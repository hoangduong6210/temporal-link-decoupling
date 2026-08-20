"""
SR-GNN v3 — REACT (Resonance Echo with Adaptive Computation Tree)

Builds on v2 with 5 contributions:
  1. Multi-signal Edge State (12-dim): recurrence (EWMA-decay), Hawkes λ(t),
     Welford online μ_dt/σ_dt → z-score-based state targets.
  2. Echo Memory with time-decay (anti-staleness): per-node Krylov echo,
     decayed by exp(-λ_echo · dt) before propagation.
  3. Adaptive Router: edges in DECAY/DEATH skip echo update (~70% skip).
  4. Periodic Hopfield Pass: post-batch (anti-leakage) attention sweep on
     active set — long-range resonance at O(N_active² / M) amortized cost.
  5. Joint Profile (pair affinity): rate_uv vs rate_u·rate_v (PMI-like) drives
     resonance coefficient R_uv.

Causality invariants (DO NOT VIOLATE):
  I1. Score BEFORE memory update          (legacy rule)
  I2. Decay echo BEFORE propagate         (anti-staleness)
  I3. Hopfield AFTER backward             (anti-leakage)
  I4. last_t synced with echo on update
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
from typing import Optional, Dict, Tuple

from .sr_gnn import (
    IDLE, BIRTH, REINFORCE, DECAY, DEATH,
    VALID_TRANSITIONS,
    TimeEncoder,
    NodeMemoryStore,
)
from .sr_gnn_v2 import ResidualCSN, TIP_v2


# ════════════════════════════════════════════════════════════════
# Multi-signal Edge State Store (12-dim)
# Layout: [state_logits(5) | recur(1) | hawkes_λ(1) | mean_dt(1) | std_dt(1) | n_obs(1) | vol(1) | life(1)]
# ════════════════════════════════════════════════════════════════

EDGE_STATE_DIM = 12
IDX_RECUR     = 5
IDX_HAWKES    = 6
IDX_MEAN_DT   = 7
IDX_STD_DT    = 8
IDX_NOBS      = 9
IDX_VOL       = 10
IDX_LIFE      = 11


class EdgeStateStoreV3:
    """Vectorized 12-dim edge state. Pool grows on-demand, all batch ops on GPU.

    Internal layout:
      _table : Tensor[max_edges, 12]   — dense state pool
      _last_t: Tensor[max_edges]       — last seen timestamp
      _key_to_idx: Dict[int, int]      — (u*N+v) → row idx (CPU dict)
    """
    INIT_POOL = 200_000

    def __init__(self, num_nodes: int, device: torch.device,
                 ewma_alpha: float = 0.3,
                 hawkes_mu: float = 0.05,
                 hawkes_alpha: float = 1.0,
                 hawkes_beta: float = 0.1,
                 ewma_decay: float = 0.05):
        self.N = num_nodes
        self.device = device
        self.ewma_alpha = ewma_alpha
        self.hawkes_mu = hawkes_mu
        self.hawkes_alpha = hawkes_alpha
        self.hawkes_beta = hawkes_beta
        self.ewma_decay = ewma_decay
        self._key_to_idx: Dict[int, int] = {}
        # Allocate "row 0" as the init template so unseen edges read default state.
        self._table = torch.zeros(self.INIT_POOL, EDGE_STATE_DIM, device=device)
        self._table[:, IDLE] = 1.0
        self._table[:, IDX_STD_DT] = 1.0
        self._last_t = torch.zeros(self.INIT_POOL, device=device)
        self._next_idx = 1   # row 0 reserved as default

    def _alloc(self, keys_cpu, t_cpu):
        """Allocate rows for unseen pair-keys. Returns idx list (Python list)
        and a list of (idx, t) pairs that need fresh last_t initialization."""
        idxs = [0] * len(keys_cpu)
        new_idxs = []
        new_ts = []
        ki = self._key_to_idx
        n = self._next_idx
        for i in range(len(keys_cpu)):
            k = keys_cpu[i]
            j = ki.get(k)
            if j is None:
                j = n
                ki[k] = n
                n += 1
                new_idxs.append(j)
                new_ts.append(t_cpu[i])
            idxs[i] = j
        self._next_idx = n
        return idxs, new_idxs, new_ts

    def get_batch(self, src: Tensor, dst: Tensor, t: Tensor) -> Tuple[Tensor, Tensor, Tensor]:
        # Compute keys vectorized, then move to CPU once
        keys = (src.long() * self.N + dst.long()).cpu().numpy().tolist()
        t_cpu = t.cpu().numpy().tolist()
        idxs, new_idxs, new_ts = self._alloc(keys, t_cpu)
        idx = torch.tensor(idxs, dtype=torch.long, device=self.device)
        # Bulk-init last_t for new rows (single index_put)
        if new_idxs:
            ni = torch.tensor(new_idxs, dtype=torch.long, device=self.device)
            nt = torch.tensor(new_ts, dtype=torch.float, device=self.device)
            self._last_t[ni] = nt
        states = self._table[idx]
        last_t = self._last_t[idx]
        return states, last_t, idx

    def update_batch(self, idx: Tensor, t: Tensor, new_states: Tensor):
        # idx: (B,) row indices returned by get_batch
        self._table[idx] = new_states.detach()
        self._last_t[idx] = t.float().detach()

    def reset(self):
        self._key_to_idx.clear()
        self._table.zero_()
        self._table[:, IDLE] = 1.0
        self._table[:, IDX_STD_DT] = 1.0
        self._last_t.zero_()
        self._next_idx = 1


# ════════════════════════════════════════════════════════════════
# Joint Profile Store (per-pair PMI-like affinity)
# ════════════════════════════════════════════════════════════════

class JointProfileStore:
    """Vectorized rate tracking: per-node rate_u + per-pair rate_uv (dense pool)."""
    INIT_POOL = 200_000

    def __init__(self, num_nodes: int, device: torch.device,
                 alpha: float = 0.05, decay: float = 0.001):
        self.N = num_nodes
        self.device = device
        self.alpha = alpha
        self.decay = decay
        self.rate_u = torch.zeros(num_nodes, device=device)
        self.last_u = torch.zeros(num_nodes, device=device)
        self._key_to_idx: Dict[int, int] = {}
        self._rate_uv = torch.zeros(self.INIT_POOL, device=device)
        self._last_uv = torch.zeros(self.INIT_POOL, device=device)
        self._next_idx = 1   # row 0 = default (rate=0)

    def _alloc(self, keys_cpu, t_cpu):
        idxs = [0] * len(keys_cpu)
        new_idxs = []
        new_ts = []
        ki = self._key_to_idx
        n = self._next_idx
        for i in range(len(keys_cpu)):
            k = keys_cpu[i]
            j = ki.get(k)
            if j is None:
                j = n
                ki[k] = n
                n += 1
                new_idxs.append(j)
                new_ts.append(t_cpu[i])
            idxs[i] = j
        self._next_idx = n
        return idxs, new_idxs, new_ts

    def affinity(self, src: Tensor, dst: Tensor, t: Tensor) -> Tuple[Tensor, Tensor]:
        """Return (B,) affinity ∈ [0, 10] and (B,) row indices."""
        keys = (src.long() * self.N + dst.long()).cpu().numpy().tolist()
        t_cpu = t.cpu().numpy().tolist()
        idxs, new_idxs, new_ts = self._alloc(keys, t_cpu)
        idx = torch.tensor(idxs, dtype=torch.long, device=self.device)
        if new_idxs:
            ni = torch.tensor(new_idxs, dtype=torch.long, device=self.device)
            nt = torch.tensor(new_ts, dtype=torch.float, device=self.device)
            self._last_uv[ni] = nt
        ru = self.rate_u[src]
        rv = self.rate_u[dst]
        rates_uv = self._rate_uv[idx]
        denom = torch.sqrt(ru * rv + 1e-6)
        return (rates_uv / (denom + 1e-6)).clamp(0, 10), idx

    def update(self, src: Tensor, dst: Tensor, t: Tensor, idx: Tensor):
        """Vectorized update of rate_u (per-node) and rate_uv (per-edge row)."""
        # Per-node update — gather both src and dst as a single batch
        nodes = torch.cat([src, dst])
        times = torch.cat([t, t])
        last_n = self.last_u[nodes]
        dt_n = (times - last_n).clamp(min=0.0)
        new_rate_n = (1 - self.alpha) * self.rate_u[nodes] * torch.exp(-self.decay * dt_n) + self.alpha
        self.rate_u[nodes] = new_rate_n
        self.last_u[nodes] = times

        # Per-pair update on row indices
        last_p = self._last_uv[idx]
        dt_p = (t - last_p).clamp(min=0.0)
        new_rate_p = (1 - self.alpha) * self._rate_uv[idx] * torch.exp(-self.decay * dt_p) + self.alpha
        self._rate_uv[idx] = new_rate_p
        self._last_uv[idx] = t.float()

    def reset(self):
        self.rate_u.zero_()
        self.last_u.zero_()
        self._key_to_idx.clear()
        self._rate_uv.zero_()
        self._last_uv.zero_()
        self._next_idx = 1


# ════════════════════════════════════════════════════════════════
# Echo Memory with Time-Decay
# ════════════════════════════════════════════════════════════════

class EchoMemory(nn.Module):
    """Per-node accumulated resonance echo (∞-hop equivalent via Krylov recursion).

    Invariants:
      - decay() applied BEFORE any propagation (anti-staleness)
      - update() called AFTER prediction (anti-leakage)
      - hopfield_pass() called AFTER backward()

    IMPORTANT: echo & last_t are stored as PLAIN ATTRIBUTES, not buffers.
    Reasoning: train.py saves model.state_dict() at best val, then load_state_dict
    before test eval. If echo is a buffer, it gets saved/restored, which leaks
    training-time accumulated state into test predictions. Plain attribute keeps
    echo on device but excludes it from state_dict.
    """
    def __init__(self, num_nodes: int, hidden: int,
                 tau: float = 0.9, lambda_echo: float = 0.01,
                 device: torch.device = torch.device("cpu")):
        super().__init__()
        self.tau = tau
        self.lambda_echo = lambda_echo
        self.device = device
        # Plain tensors (not buffers) — excluded from state_dict
        self.echo   = torch.zeros(num_nodes, hidden, device=device)
        self.last_t = torch.zeros(num_nodes, device=device)

    @torch.no_grad()
    def decay_get(self, idx: Tensor, t_now: Tensor) -> Tensor:
        """Return decayed echo for indices `idx` at time `t_now`."""
        dt = (t_now - self.last_t[idx]).clamp(min=0.0)
        factor = torch.exp(-self.lambda_echo * dt).unsqueeze(-1)
        return self.echo[idx] * factor

    @torch.no_grad()
    def update(self, u: Tensor, v: Tensor, R_uv: Tensor,
               h_u: Tensor, h_v: Tensor, t_now: Tensor,
               bidirectional: bool = True):
        """Update echo[u] using h_v + decayed echo[v]. If bidirectional,
        also update echo[v] using h_u + decayed echo[u] (symmetric).

        Caller must NOT pre-compute decay; this method does it once."""
        echo_u_decayed = self.decay_get(u, t_now)
        echo_v_decayed = self.decay_get(v, t_now)
        R = R_uv.unsqueeze(-1)

        delta_u = R * (h_v + echo_v_decayed)
        new_echo_u = self.tau * echo_u_decayed + (1 - self.tau) * delta_u
        self.echo[u] = new_echo_u.detach()
        self.last_t[u] = t_now

        if bidirectional:
            delta_v = R * (h_u + echo_u_decayed)   # symmetric: use ORIGINAL decayed echo_u
            new_echo_v = self.tau * echo_v_decayed + (1 - self.tau) * delta_v
            self.echo[v] = new_echo_v.detach()
            self.last_t[v] = t_now
        # If not bidirectional, intentionally DO NOT stamp last_t[v] — v's echo
        # content unchanged, so decay should continue from its true last update.

    @torch.no_grad()
    def hopfield_pass(self, active_idx: Tensor, beta: float = 1.0):
        """Continuous Hopfield single-pass on active set.
        MUST be called AFTER loss.backward() and optimizer.step()."""
        if active_idx.numel() < 2:
            return
        H = self.echo[active_idx]                            # (n, d)
        # Numerical stability: normalize
        H_norm = F.normalize(H, dim=-1)
        attn = torch.softmax(beta * H_norm @ H_norm.T, dim=-1)
        H_new = attn @ H
        self.echo[active_idx] = 0.5 * H + 0.5 * H_new

    def reset(self):
        self.echo.zero_()
        self.last_t.zero_()


# ════════════════════════════════════════════════════════════════
# ECTG v3 — Multi-signal heuristic targets
# ════════════════════════════════════════════════════════════════

class ECTGv3(nn.Module):
    """Edge-state transition net using z-score + Hawkes λ heuristic targets."""
    def __init__(self, feat_dim: int, hidden: int):
        super().__init__()
        in_dim = feat_dim + 1 + 5 + 4  # feat | log_dt | cur_dist | (recur, hawkes_λ, z, log_nobs)
        self.trans_net = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.ReLU(),
            nn.Linear(hidden, 5)
        )
        self.ctx_encoder = nn.Linear(EDGE_STATE_DIM, hidden)

    def update_signals(self, edge_states: Tensor, last_t: Tensor,
                       t: Tensor, store: EdgeStateStoreV3) -> Tensor:
        """Update recurrence, Hawkes λ, Welford μ/σ, n_obs given new event at t."""
        dt = (t - last_t).clamp(min=0.0)
        # Welford online (for n>0)
        n_old = edge_states[:, IDX_NOBS]
        mean_old = edge_states[:, IDX_MEAN_DT]
        var_old = edge_states[:, IDX_STD_DT].pow(2)
        n_new = n_old + 1
        delta = dt - mean_old
        mean_new = mean_old + delta / n_new.clamp(min=1)
        # M2 = var_old * n_old (running sum of squares)
        m2_old = var_old * n_old
        m2_new = m2_old + delta * (dt - mean_new)
        var_new = m2_new / n_new.clamp(min=1)
        std_new = torch.sqrt(var_new.clamp(min=1e-4))

        # First observation: dt is `t - last_t[init=0]` = absolute timestamp.
        # Using it as mean would corrupt z-score for all future events.
        # Solution: skip Welford for first event — keep default mean=0, std=1.
        first_mask = (n_old < 0.5).float()
        std_new = first_mask * 1.0 + (1 - first_mask) * std_new
        mean_new = first_mask * 0.0 + (1 - first_mask) * mean_new
        # Also fix dt itself for first-event downstream usage: treat as 0 (no gap to compare)
        # This matters for z-score in heuristic_target.

        # Recurrence (EWMA with time-decay)
        recur_old = edge_states[:, IDX_RECUR]
        decay_factor = torch.exp(-store.ewma_decay * dt)
        recur_new = (1 - store.ewma_alpha) * recur_old * decay_factor + store.ewma_alpha

        # Hawkes λ(t)  recursive update:
        #   λ_new = α + (λ_old - μ) * exp(-β * dt) + μ
        haw_old = edge_states[:, IDX_HAWKES]
        haw_new = store.hawkes_alpha + (haw_old - store.hawkes_mu) * torch.exp(-store.hawkes_beta * dt) + store.hawkes_mu
        haw_new = haw_new.clamp(min=0.0, max=20.0)

        # Volatility / lifecycle (kept simple)
        vol_new = edge_states[:, IDX_VOL] * 0.95 + 0.05
        life_new = edge_states[:, IDX_LIFE] + torch.log1p(dt) * 0.01

        out = edge_states.clone()
        out[:, IDX_RECUR] = recur_new
        out[:, IDX_HAWKES] = haw_new
        out[:, IDX_MEAN_DT] = mean_new
        out[:, IDX_STD_DT] = std_new
        out[:, IDX_NOBS] = n_new
        out[:, IDX_VOL] = vol_new
        out[:, IDX_LIFE] = life_new
        return out

    def heuristic_target(self, edge_states: Tensor, dt: Tensor) -> Tensor:
        """Soft state target from multi-signal cues."""
        recur = edge_states[:, IDX_RECUR]
        haw   = edge_states[:, IDX_HAWKES]
        mean_dt = edge_states[:, IDX_MEAN_DT]
        std_dt  = edge_states[:, IDX_STD_DT].clamp(min=1e-2)
        n_obs   = edge_states[:, IDX_NOBS]

        is_first  = (n_obs < 1.5).float()
        # For first events, force z=0 (no late/dead signal) to avoid using absolute timestamp
        z = torch.where(is_first.bool(), torch.zeros_like(dt), (dt - mean_dt) / std_dt)

        is_active = torch.sigmoid(haw - 1.0)
        is_late   = torch.sigmoid(z - 1.5)
        is_dead   = torch.sigmoid(z - 3.0)

        targets = torch.stack([
            (1.0 - is_active - is_first).clamp(min=0),       # IDLE
            is_first * 2.0,                                   # BIRTH
            is_active * (1 - is_late),                        # REINFORCE
            is_late * (1 - is_dead),                          # DECAY
            is_dead,                                          # DEATH
        ], dim=-1)
        # Mask invalid transitions
        cur_idx = edge_states[:, :5].argmax(-1)
        mask = VALID_TRANSITIONS[cur_idx.cpu()].to(edge_states.device)
        masked = targets.masked_fill(~mask, -1e9)
        return torch.softmax(masked, dim=-1).detach()

    def forward(self, feat: Tensor, salience: Tensor,
                delta_t: Tensor, edge_states: Tensor
                ) -> Tuple[Tensor, Tensor, Tensor, Tensor]:
        """Returns: new_states, edge_ctx, student_logits, heuristic_target."""
        cur_dist = torch.softmax(edge_states[:, :5], dim=-1)
        log_dt = torch.log1p(delta_t.float()).unsqueeze(-1)

        recur = edge_states[:, IDX_RECUR:IDX_RECUR+1]
        haw   = edge_states[:, IDX_HAWKES:IDX_HAWKES+1]
        mean_dt = edge_states[:, IDX_MEAN_DT:IDX_MEAN_DT+1]
        std_dt  = edge_states[:, IDX_STD_DT:IDX_STD_DT+1].clamp(min=1e-2)
        n_obs = edge_states[:, IDX_NOBS:IDX_NOBS+1]
        log_nobs = torch.log1p(n_obs)
        # Mask z=0 for first events to avoid absolute-timestamp leak
        is_first = (n_obs < 1.5).float()
        z = (1 - is_first) * (delta_t.unsqueeze(-1) - mean_dt) / std_dt

        trans_in = torch.cat([feat, log_dt, cur_dist,
                              recur, haw, z, log_nobs], dim=-1)
        student_logits = self.trans_net(trans_in)

        # Causal mask
        cur_idx = cur_dist.argmax(-1)
        mask = VALID_TRANSITIONS[cur_idx.cpu()].to(feat.device)
        masked_logits = student_logits.masked_fill(~mask, -1e9)
        new_dist = torch.softmax(masked_logits, dim=-1)

        # Build new state vector (overwrite the first 5 dims)
        new_states = edge_states.clone()
        new_states[:, :5] = new_dist

        # Edge ctx for downstream
        edge_ctx = self.ctx_encoder(new_states)

        # Heuristic target (using updated signal-bearing dims, but state idx from old)
        target = self.heuristic_target(edge_states, delta_t)

        return new_states, edge_ctx, student_logits, target


# ════════════════════════════════════════════════════════════════
# DRGC v3 — Resonance-weighted bidirectional with echo augmentation
# ════════════════════════════════════════════════════════════════

class DRGCv3(nn.Module):
    def __init__(self, feat_dim: int, hidden: int, beta_tip: float = 0.001):
        super().__init__()
        self.hidden = hidden
        self.time_enc = TimeEncoder(hidden)

        msg_in = hidden * 2 + hidden + hidden + feat_dim
        self.msg_s2d = nn.Sequential(
            nn.Linear(msg_in, hidden), nn.ReLU(), nn.Linear(hidden, hidden))
        self.msg_d2s = nn.Sequential(
            nn.Linear(msg_in, hidden), nn.ReLU(), nn.Linear(hidden, hidden))
        self.gru_src = nn.GRUCell(hidden, hidden)
        self.gru_dst = nn.GRUCell(hidden, hidden)
        self.decay_net = nn.Sequential(
            nn.Linear(hidden, hidden // 2), nn.ReLU(),
            nn.Linear(hidden // 2, hidden), nn.Sigmoid())
        # Resonance coefficient network: [affinity, cos_sim, intensity, log_nobs] → [0,1]
        # Initialize bias to make R_uv ≈ 0.9 at start (don't suppress messages early)
        self.res_net = nn.Sequential(
            nn.Linear(4, hidden // 4), nn.ReLU(),
            nn.Linear(hidden // 4, 1), nn.Sigmoid())
        with torch.no_grad():
            self.res_net[-2].bias.fill_(2.0)   # sigmoid(2.0) ≈ 0.88
        self.tip = TIP_v2(hidden, beta_tip)

    def compute_resonance(self, h_src: Tensor, h_dst: Tensor,
                          affinity: Tensor, intensity: Tensor,
                          n_obs: Tensor) -> Tensor:
        cos_sim = F.cosine_similarity(h_src, h_dst, dim=-1).unsqueeze(-1)
        feat = torch.cat([
            affinity.unsqueeze(-1),
            cos_sim,
            intensity.unsqueeze(-1),
            torch.log1p(n_obs).unsqueeze(-1)
        ], dim=-1)
        return self.res_net(feat).squeeze(-1)        # (B,) ∈ [0,1]

    def forward(self, h_src: Tensor, h_dst: Tensor,
                feat: Tensor, edge_ctx: Tensor,
                dt_src: Tensor, dt_dst: Tensor,
                R_uv: Tensor,
                compress_nodes: Tensor, compress_staleness: Optional[Tensor]
                ) -> Tuple[Tensor, Tensor, Tensor, Tensor]:
        t_enc_s = self.time_enc(dt_src)
        t_enc_d = self.time_enc(dt_dst)
        decay_s = self.decay_net(t_enc_s)
        decay_d = self.decay_net(t_enc_d)
        h_src_d = h_src * decay_s
        h_dst_d = h_dst * decay_d

        r_mask = R_uv.unsqueeze(-1)

        msg_s = self.msg_s2d(torch.cat([h_src_d, h_dst_d, edge_ctx, t_enc_s, feat], -1))
        msg_d = self.msg_d2s(torch.cat([h_dst_d, h_src_d, edge_ctx, t_enc_d, feat], -1))
        msg_s = msg_s * r_mask
        msg_d = msg_d * r_mask

        new_h_src = self.gru_src(msg_d, h_src)
        new_h_dst = self.gru_dst(msg_s, h_dst)

        parsed_h, kl = self.tip(compress_nodes, compress_staleness)
        return new_h_src, new_h_dst, parsed_h, kl


# ════════════════════════════════════════════════════════════════
# NSCP v3 — uses 12-dim edge state
# ════════════════════════════════════════════════════════════════

class NSCPv3(nn.Module):
    def __init__(self, hidden: int):
        super().__init__()
        self.state_embed = nn.Sequential(
            nn.Linear(EDGE_STATE_DIM, hidden // 2), nn.ReLU(),
            nn.Linear(hidden // 2, hidden // 4))
        pred_in = hidden * 2 + hidden // 4
        self.predictor = nn.Sequential(
            nn.Linear(pred_in, hidden), nn.ReLU(),
            nn.Dropout(0.1), nn.Linear(hidden, 1))

    def forward(self, src_emb: Tensor, dst_emb: Tensor,
                neg_dst_emb: Tensor, edge_state: Tensor,
                state_logits: Tensor):
        st_emb = self.state_embed(edge_state)
        pos_in = torch.cat([src_emb, dst_emb, st_emb], -1)
        neg_in = torch.cat([src_emb, neg_dst_emb, st_emb], -1)
        pos_score = self.predictor(pos_in).squeeze(-1)
        neg_score = self.predictor(neg_in).squeeze(-1)

        decay_death = edge_state[:, DECAY] + edge_state[:, DEATH]
        reinforce = edge_state[:, REINFORCE]
        causal_loss = (
            (decay_death * F.relu(pos_score)).mean()
            + (reinforce * F.relu(-pos_score)).mean() * 0.5
        )
        state_target = edge_state[:, :5].detach()
        state_loss = F.kl_div(
            F.log_softmax(state_logits, -1), state_target, reduction='batchmean'
        ) * 0.1
        total_causal = causal_loss + state_loss
        ccs = 1.0 - (decay_death * torch.sigmoid(pos_score).detach()).clamp(0, 1)
        return pos_score, neg_score, total_causal, ccs


# ════════════════════════════════════════════════════════════════
# Full SR-GNN v3
# ════════════════════════════════════════════════════════════════

class SRGNN_v3(nn.Module):
    def __init__(self, num_nodes: int, feat_dim: int, hidden: int = 128,
                 tip_beta: float = 0.001,
                 lambda_tip: float = 0.01, lambda_causal: float = 0.1,
                 lambda_trans: float = 0.05, lambda_distill: float = 0.2,
                 tau_echo: float = 0.95, lambda_echo: float = 0.01,
                 hopfield_period: int = 50, hopfield_beta: float = 1.0,
                 use_echo: bool = True, use_hopfield: bool = True,
                 use_router: bool = True, use_joint: bool = True,
                 use_bidirectional_echo: bool = True,
                 num_echo_scales: int = 1,
                 device: torch.device = torch.device("cpu")):
        super().__init__()
        self.num_nodes = num_nodes
        self.feat_dim = feat_dim
        self.hidden = hidden
        self.lambda_tip = lambda_tip
        self.lambda_causal = lambda_causal
        self.lambda_trans = lambda_trans
        self.lambda_distill = lambda_distill
        self.hopfield_period = hopfield_period
        self.hopfield_beta = hopfield_beta
        self.use_echo = use_echo
        self.use_hopfield = use_hopfield
        self.use_router = use_router
        self.use_joint = use_joint
        self.use_bidirectional_echo = use_bidirectional_echo
        self.num_echo_scales = num_echo_scales
        self.device = device
        self._feat_in = max(feat_dim, 1)

        self.csn  = ResidualCSN(self._feat_in, hidden)
        self.ectg = ECTGv3(self._feat_in, hidden)
        self.drgc = DRGCv3(self._feat_in, hidden, tip_beta)
        self.nscp = NSCPv3(hidden)

        # Echo gate: learnable scalar to control how much echo contributes
        # Start small (0.1) so model learns from local memory first, then ramps up echo
        self.echo_gate = nn.Parameter(torch.tensor(0.1))
        self.echo_norm = nn.LayerNorm(hidden)

        self.node_mem = NodeMemoryStore(num_nodes, hidden, device)
        self.edge_mem = EdgeStateStoreV3(num_nodes, device)
        self.joint    = JointProfileStore(num_nodes, device)

        # Multi-scale Echo Bank: K parallel echo memories with different decay rates
        # Scale 0 (short): λ × 5  — recent context
        # Scale 1 (med):   λ × 1  — current best (lambda_echo)
        # Scale 2 (long):  λ / 5  — long-term routine
        if num_echo_scales == 1:
            self.echoes = nn.ModuleList([
                EchoMemory(num_nodes, hidden, tau_echo, lambda_echo, device).to(device)
            ])
            self.scale_mix = None
        else:
            scale_multipliers = [5.0, 1.0, 0.2][:num_echo_scales]
            self.echoes = nn.ModuleList([
                EchoMemory(num_nodes, hidden, tau_echo, lambda_echo * m, device).to(device)
                for m in scale_multipliers
            ])
            # Learnable mix weights across scales (softmax)
            self.scale_mix = nn.Parameter(torch.zeros(num_echo_scales))
        # Backward-compat alias for legacy code paths
        self.echo = self.echoes[0]

        self.state_oracle = nn.Sequential(
            nn.Linear(hidden * 2, hidden), nn.ReLU(),
            nn.Linear(hidden, 5)
        ).to(device)

        # routing/hopfield bookkeeping
        self._batch_count = 0
        self._recent_active = []                # rolling list of recent active idx
        self._routing_skip_total = 0
        self._routing_total = 0

    def reset(self):
        self.node_mem.reset()
        self.edge_mem.reset()
        self.joint.reset()
        for e in self.echoes:
            e.reset()
        self._batch_count = 0
        self._recent_active = []
        self._routing_skip_total = 0
        self._routing_total = 0

    def _multi_scale_echo_get(self, idx: Tensor, t: Tensor) -> Tensor:
        """Aggregated decayed echo over K scales, mixed by learnable softmax weights."""
        if self.num_echo_scales == 1:
            return self.echoes[0].decay_get(idx, t)
        w = torch.softmax(self.scale_mix, dim=0)         # (K,)
        outs = [e.decay_get(idx, t) for e in self.echoes]  # K × (B, d)
        stacked = torch.stack(outs, dim=0)                # (K, B, d)
        return (w.view(-1, 1, 1) * stacked).sum(dim=0)    # (B, d)

    def post_step(self):
        """Called after loss.backward() + optimizer.step() to run Hopfield pass."""
        self._batch_count += 1
        if not (self.use_echo and self.use_hopfield):
            self._recent_active = []
            return
        if self._batch_count % self.hopfield_period == 0 and self._recent_active:
            active = torch.unique(torch.cat(self._recent_active))
            if active.numel() >= 2:
                self.echo.hopfield_pass(active, beta=self.hopfield_beta)
            self._recent_active = []

    def forward(self, src: Tensor, dst: Tensor, t: Tensor,
                feat: Tensor, neg_dst: Tensor,
                rel_type: Optional[Tensor] = None) -> Dict[str, Tensor]:
        device = self.device
        B = src.size(0)

        if feat.shape[-1] == 0:
            feat = torch.zeros(B, 1, device=device)
        elif feat.shape[-1] < self._feat_in:
            feat = F.pad(feat, (0, self._feat_in - feat.shape[-1]))

        # ── L1: ResidualCSN ──
        dt_src = self.node_mem.delta_t(src, t)
        feat_g, sal = self.csn(feat, dt_src)

        # ── L2: ECTG v3 ──
        edge_st_old, last_t_e, edge_idx = self.edge_mem.get_batch(src, dst, t)
        dt_e = (t - last_t_e).clamp(min=0.0)
        # First update signal-bearing dims based on new event (recur, hawkes, μ, σ, n_obs)
        edge_st_signals = self.ectg.update_signals(edge_st_old, last_t_e, t, self.edge_mem)
        # Then run transition net using updated signals
        new_edge_st, edge_ctx, student_logits, heuristic_target = self.ectg(
            feat_g, sal, dt_e, edge_st_signals)

        # ── Joint profile: compute affinity from STORE STATE BEFORE update ──
        if self.use_joint:
            affinity, joint_idx = self.joint.affinity(src, dst, t)
        else:
            affinity = torch.ones(B, device=device)
            joint_idx = None
        intensity = new_edge_st[:, IDX_HAWKES]
        n_obs = new_edge_st[:, IDX_NOBS]

        # ── L3: DRGC v3 ──
        h_src = self.node_mem.get(src)
        h_dst = self.node_mem.get(dst)
        dt_dst = self.node_mem.delta_t(dst, t)

        # Augment with decayed echo (anti-staleness, anti-leakage: echo from BEFORE this batch)
        # Echo is normalized + gated to prevent magnitude explosion
        if self.use_echo:
            echo_src = self._multi_scale_echo_get(src, t)
            echo_dst = self._multi_scale_echo_get(dst, t)
            gate = torch.sigmoid(self.echo_gate)               # ∈ (0, 1), starts ~0.52
            h_src_full = h_src + gate * self.echo_norm(echo_src)
            h_dst_full = h_dst + gate * self.echo_norm(echo_dst)
        else:
            gate = torch.tensor(0.0, device=device)
            h_src_full = h_src
            h_dst_full = h_dst

        # Resonance coefficient — use RAW h (not echo-augmented) to avoid
        # self-reinforcing community drift.
        R_uv = self.drgc.compute_resonance(h_src, h_dst, affinity, intensity, n_obs)

        all_idx = torch.unique(torch.cat([src, dst]))
        all_h = self.node_mem.get(all_idx)
        all_staleness = (t.max().float() - self.node_mem.last_t[all_idx]).clamp(0)

        new_h_src, new_h_dst, parsed_h, kl = self.drgc(
            h_src_full, h_dst_full, feat_g, edge_ctx,
            dt_src, dt_dst, R_uv, all_h, all_staleness
        )

        teacher_logits = self.state_oracle(torch.cat([new_h_src, new_h_dst], dim=-1))

        # ── L4: NSCP v3 (score BEFORE memory update — Invariant I1) ──
        neg_emb = self.node_mem.get(neg_dst)
        # Augment neg with its own echo (same gate to ensure parity with pos)
        if self.use_echo:
            neg_echo = self._multi_scale_echo_get(neg_dst, t)
            neg_emb_full = neg_emb + gate * self.echo_norm(neg_echo)
        else:
            neg_emb_full = neg_emb
        pos_sc, neg_sc, c_loss, ccs = self.nscp(
            new_h_src, new_h_dst, neg_emb_full, new_edge_st, teacher_logits)

        # ════════════ POST-PREDICTION STATE UPDATES ════════════
        # Edge state store
        self.edge_mem.update_batch(edge_idx, t, new_edge_st)
        # Joint profile
        if self.use_joint and joint_idx is not None:
            self.joint.update(src, dst, t, joint_idx)
        # Adaptive router: only update echo for active edges (IDLE/BIRTH/REINFORCE)
        if self.use_router:
            active_score = new_edge_st[:, IDLE] + new_edge_st[:, BIRTH] + new_edge_st[:, REINFORCE]
            active_mask = active_score > 0.5
        else:
            active_mask = torch.ones(B, dtype=torch.bool, device=device)
        self._routing_total += B
        self._routing_skip_total += int((~active_mask).sum().item())
        if self.use_echo and active_mask.any():
            with torch.no_grad():
                u_act = src[active_mask]
                v_act = dst[active_mask]
                R_act = R_uv[active_mask].detach()
                h_u_act = new_h_src[active_mask].detach()
                h_v_act = new_h_dst[active_mask].detach()
                t_act = t[active_mask]
                # Update ALL scales (each has different decay rate, same content)
                for e in self.echoes:
                    e.update(u_act, v_act, R_act, h_u_act, h_v_act, t_act,
                             bidirectional=self.use_bidirectional_echo)
        # Track active indices for periodic Hopfield
        self._recent_active.append(all_idx.detach())

        # Node memory (last)
        self.node_mem.set(all_idx, parsed_h)
        self.node_mem.set(src, new_h_src)
        self.node_mem.set(dst, new_h_dst)
        self.node_mem.update_time(torch.cat([src, dst]), torch.cat([t, t]))

        # ── Loss ──
        pred_loss = F.binary_cross_entropy_with_logits(
            torch.cat([pos_sc, neg_sc]),
            torch.cat([torch.ones(B, device=device), torch.zeros(B, device=device)])
        )
        s_teacher = F.softmax(teacher_logits, dim=-1).detach()
        log_s_student = F.log_softmax(student_logits, dim=-1)
        loss_heur = F.kl_div(log_s_student, heuristic_target, reduction='batchmean')
        loss_pred_kl = F.kl_div(log_s_student, s_teacher, reduction='batchmean')
        trans_loss = (1 - self.lambda_distill) * loss_heur + self.lambda_distill * loss_pred_kl

        total = (pred_loss
                 + self.lambda_tip * kl
                 + self.lambda_causal * c_loss
                 + self.lambda_trans * trans_loss)

        return {
            "pos_score": pos_sc, "neg_score": neg_sc,
            "loss": total, "pred_loss": pred_loss,
            "tip_loss": kl, "causal_loss": c_loss,
            "trans_loss": trans_loss,
            "ccs": ccs.mean(), "salience": sal.mean(),
            "R_uv_mean": R_uv.mean().detach(),
            "active_ratio": float(active_mask.float().mean().item()),
        }
