"""Prospective adapter using the existing temporal model's trainable modules.

Query transforms do not commit hypothetical events or consume target attributes.
Observation retains legacy auxiliary losses with its prediction term removed.
This is a separately specified pilot, not a modification of the frozen model.
"""
from __future__ import annotations

import math

import torch
from torch import Tensor, nn
import torch.nn.functional as F

from .v33.sr_gnn_v3_3 import EverAliveStore, SRGNN_v3_3


class IndexedEverAliveStore(EverAliveStore):
    """Same max-accumulator semantics without a full N-squared copy per event."""
    @torch.no_grad()
    def update(self, src: Tensor, dst: Tensor, alive_score: Tensor):
        keys, inverse = torch.unique(self._keys(src, dst), sorted=True, return_inverse=True)
        maxima = torch.zeros(len(keys), device=self.device, dtype=self.values.dtype)
        maxima.scatter_reduce_(0, inverse, alive_score.detach().clamp(0, 1),
                               reduce="amax", include_self=True)
        registered = self.registered[keys]
        selected = keys[registered]
        self.values[selected] = torch.maximum(self.values[selected], maxima[registered])


class ProspectiveSRGNN(nn.Module):
    def __init__(self, num_nodes: int, feat_dim: int, hidden: int = 32,
                 *, decoupled: bool = False, device: str = "cpu"):
        super().__init__()
        self.decoupled = decoupled
        self.core = SRGNN_v3_3(
            num_nodes, feat_dim, hidden, device=torch.device(device),
            enable_main_predictor=False, enable_lfg=True, enable_echo=False,
            design="correct_decoupled", fsm_arch="v3", fsm_decode="hier",
            decol_hier_v2=True, causal_batch=True, hier_causal_policy=True,
            lambda_edge_trans=.5, edge_state_entropy_w=.02, edge_uniform_kl_w=.01,
            entropy_reg_weight=.01, edge_h_detach_scorepath=True,
        ).to(device)
        self.core.ever_alive = IndexedEverAliveStore(num_nodes, torch.device(device))
        # Runtime state, deliberately excluded from parameter checkpoints.
        self.last_features = torch.zeros(num_nodes, max(feat_dim, 1), device=device)
        self.watermark = -math.inf
        self.observed_events = 0

    def reset(self):
        self.core.reset()
        self.core.csn.feat_ema.zero_()
        self.last_features.zero_()
        self.watermark = -math.inf
        self.observed_events = 0

    def _check_queries(self, src: Tensor, dst: Tensor, t: Tensor):
        if src.ndim != 1 or dst.shape != src.shape or t.shape != src.shape or not src.numel():
            raise ValueError("queries must be aligned nonempty vectors")
        if src.dtype != torch.long or dst.dtype != torch.long:
            raise ValueError("endpoint identities must be integer tensors")
        if bool(((src < 0) | (dst < 0) | (src >= self.core.num_nodes)
                 | (dst >= self.core.num_nodes)).any()):
            raise ValueError("query endpoint outside node catalogue")
        if not bool(torch.isfinite(t).all()) or bool((t <= self.watermark).any()):
            raise ValueError("query time must be strictly after observed history")

    def _history_encoding(self, features: Tensor, gap: Tensor) -> Tensor:
        """ResidualCSN's transform with a read-only feature EMA, including in train mode."""
        csn = self.core.csn
        temporal = csn.time_gate(torch.log1p(gap.float()).unsqueeze(-1))
        projected = F.normalize(csn.feat_proj(features), dim=-1)
        similarity = (projected * F.normalize(csn.feat_ema.unsqueeze(0), dim=-1)).sum(
            -1, keepdim=True).clamp(-1, 1)
        novelty = 1 - (similarity + 1) / 2
        weight = csn.alpha_net(torch.cat([temporal, novelty], dim=-1))
        return features + weight * csn.feat_transform(features)

    def score_candidates(self, src: Tensor, dst: Tensor, t: Tensor) -> Tensor:
        """Pure, deterministic candidate query: no labels or current event attributes."""
        self._check_queries(src, dst, t)
        core = self.core
        gap_src = core.node_mem.delta_t(src, t)
        gap_dst = core.node_mem.delta_t(dst, t)
        state = core.edge_mem.peek_batch(src, dst)
        ever = core.ever_alive.peek(src, dst)
        past_features = (self.last_features[src] + self.last_features[dst]) / 2
        features = self._history_encoding(past_features, gap_src)
        context = core.ectg.ctx_encoder(state)
        # The deterministic message/GRU part of DRGC_v2, applied identically to
        # every candidate. No TIP sampling, event jump, EMA update or store commit.
        recurrent = core.drgc
        hs, hd = core.node_mem.get(src), core.node_mem.get(dst)
        ts, td = recurrent.time_enc(gap_src), recurrent.time_enc(gap_dst)
        ds, dd = hs * recurrent.decay_net(ts), hd * recurrent.decay_net(td)
        resonance = recurrent.tip.resonance_mask(state[:, 6]).unsqueeze(-1)
        ms = recurrent.msg_s2d(torch.cat([ds, dd, context, ts, features], dim=-1)) * resonance
        md = recurrent.msg_d2s(torch.cat([dd, ds, context, td, features], dim=-1)) * resonance
        query_h = torch.cat([recurrent.gru_src(md, hs), recurrent.gru_dst(ms, hd)], dim=-1)
        if self.decoupled:
            query_h = query_h.detach()
        current = core.state_observer(query_h, detach_h=False)
        z = (gap_src - state[:, 7]) / (state[:, 8].clamp(min=1e-6).sqrt() + 1e-6)
        z = (z * (state[:, 9] >= 2)).clamp(-5, 5)
        phi = torch.stack([state[:, 6], torch.log1p(state[:, 7].clamp(min=0)),
                           torch.log1p(state[:, 8].clamp(min=0)), state[:, 5],
                           torch.log1p(gap_src), ever, z], dim=-1).detach()
        logits = core.transition_predictor(query_h, current, pair_phi=phi)
        logits = logits + (core.lifecycle_mask.get_mask_from_state(current) + 1e-6).log()
        logits = core.lifecycle_mask.apply_ever_alive_gate(logits, ever)
        return core.existence_decoder(torch.softmax(logits, dim=-1))

    def observe_group(self, src: Tensor, dst: Tensor, t: Tensor, features: Tensor,
                      *, backward_auxiliary: bool = False) -> float:
        """Observe a complete tie group *after* every prediction has been differentiated.

        Each auxiliary backward completes before the next store update. The
        caller steps the optimizer after this method, never within a tie group.
        """
        self._check_queries(src, dst, t)
        if not bool((t == t[0]).all()):
            raise ValueError("observation requires a complete single-timestamp group")
        if features.shape != (len(src), self.core.feat_dim) or not bool(torch.isfinite(features).all()):
            raise ValueError("invalid observed event features")
        if backward_auxiliary and not self.training:
            raise ValueError("evaluation must not differentiate observation losses")
        auxiliary_sum = 0.
        for row in range(len(src)):
            r = slice(row, row + 1)
            if not self.training:
                # Match train-time *observation* statistics during replay, while
                # leaving score_candidates pure and model parameters frozen.
                with torch.no_grad():
                    observed = features[r]
                    if not self.core.feat_dim:
                        observed = torch.zeros(1, 1, device=features.device)
                    projection = F.normalize(self.core.csn.feat_proj(observed), dim=-1)
                    self.core.csn.feat_ema = self.core.csn.feat_ema * .99 + projection.mean(0) * .01
            # This auxiliary-only call has no negative target. Its placeholder
            # negative path cancels through total - pred_loss; FSM BCE is disabled
            # by enable_main_predictor=False. Never report these logits as scores.
            out = self.core(src[r], dst[r], t[r], features[r], dst[r])
            auxiliary = out["loss"] - out["pred_loss"]
            if not bool(torch.isfinite(auxiliary)):
                raise FloatingPointError("non-finite observation auxiliary loss")
            if backward_auxiliary:
                (auxiliary / len(src)).backward()
            auxiliary_sum += float(auxiliary.detach())
            with torch.no_grad():
                if self.core.feat_dim:
                    self.last_features[src[r]] = features[r]
                    self.last_features[dst[r]] = features[r]
        self.watermark = float(t[0])
        self.observed_events += len(src)
        return auxiliary_sum / len(src)
