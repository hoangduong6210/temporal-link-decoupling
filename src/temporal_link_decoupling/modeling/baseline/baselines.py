"""
Baseline temporal graph models for comparison with SR-GNN.
  1. JODIE       — coupled RNN  (Kumar et al., 2019)
  2. DyRep       — temporal GNN (Trivedi et al., 2019)
  3. TGAT        — temporal attention (Xu et al., 2020)
  4. TGN         — memory + GRU (Rossi et al., 2020)
  5. GraphMixer  — MLP-based (Cong et al., 2023)
  6. Ablation variants of SR-GNN
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
from typing import Tuple, Dict, Optional
from .sr_gnn import (SRGNN, NodeMemoryStore, TimeEncoder,
                            CSN, ECTG, DRGC, NSCP,
                            IDLE, BIRTH, REINFORCE, DECAY, DEATH)


# ────────────────────────────────────────────────────────────
# Shared helpers
# ────────────────────────────────────────────────────────────

def bce_link_loss(pos: Tensor, neg: Tensor) -> Tensor:
    B, dev = pos.size(0), pos.device
    return F.binary_cross_entropy_with_logits(
        torch.cat([pos, neg]),
        torch.cat([torch.ones(B, device=dev), torch.zeros(B, device=dev)])
    )


def make_predictor(hidden: int) -> nn.Module:
    return nn.Sequential(
        nn.Linear(hidden * 2, hidden), nn.ReLU(), nn.Linear(hidden, 1)
    )


# ────────────────────────────────────────────────────────────
# 1. JODIE
# ────────────────────────────────────────────────────────────

class JODIE(nn.Module):
    def __init__(self, num_nodes: int, feat_dim: int, hidden: int = 128,
                 device=torch.device("cpu")):
        super().__init__()
        self._fd   = max(feat_dim, 1)
        self.mem   = NodeMemoryStore(num_nodes, hidden, device)
        self.te    = TimeEncoder(hidden)
        self.u_rnn = nn.RNNCell(hidden + self._fd, hidden)
        self.i_rnn = nn.RNNCell(hidden + self._fd, hidden)
        self.pred  = make_predictor(hidden)

    def reset(self): self.mem.reset()

    def forward(self, src, dst, t, feat, neg_dst, **_):
        dev = src.device
        if feat.shape[-1] == 0: feat = torch.zeros(src.size(0), 1, device=dev)
        h_s, h_d = self.mem.get(src), self.mem.get(dst)
        te = self.te(self.mem.delta_t(src, t))
        ns = self.u_rnn(torch.cat([h_d + te, feat], -1), h_s)
        nd = self.i_rnn(torch.cat([h_s + te, feat], -1), h_d)
        # Score BEFORE memory update
        neg = self.mem.get(neg_dst)
        pos_sc = self.pred(torch.cat([ns, nd], -1)).squeeze(-1)
        neg_sc = self.pred(torch.cat([ns, neg], -1)).squeeze(-1)
        # Update memory AFTER scoring
        self.mem.set(src, ns); self.mem.set(dst, nd)
        self.mem.update_time(torch.cat([src, dst]), torch.cat([t, t]))
        return {"pos_score": pos_sc, "neg_score": neg_sc,
                "loss": bce_link_loss(pos_sc, neg_sc)}


# ────────────────────────────────────────────────────────────
# 2. DyRep
# ────────────────────────────────────────────────────────────

class DyRep(nn.Module):
    def __init__(self, num_nodes: int, feat_dim: int, hidden: int = 128,
                 device=torch.device("cpu")):
        super().__init__()
        self._fd  = max(feat_dim, 1)
        self.mem  = NodeMemoryStore(num_nodes, hidden, device)
        self.te   = TimeEncoder(hidden)
        self.msg  = nn.Linear(hidden * 2 + hidden + self._fd, hidden)
        self.gru  = nn.GRUCell(hidden, hidden)
        self.pred = make_predictor(hidden)

    def reset(self): self.mem.reset()

    def forward(self, src, dst, t, feat, neg_dst, **_):
        dev = src.device
        if feat.shape[-1] == 0: feat = torch.zeros(src.size(0), 1, device=dev)
        h_s, h_d = self.mem.get(src), self.mem.get(dst)
        te = self.te(self.mem.delta_t(src, t))
        m  = F.relu(self.msg(torch.cat([h_s, h_d, te, feat], -1)))
        ns = self.gru(m, h_s); nd = self.gru(m, h_d)
        # Score BEFORE memory update
        neg = self.mem.get(neg_dst)
        pos_sc = self.pred(torch.cat([ns, nd],  -1)).squeeze(-1)
        neg_sc = self.pred(torch.cat([ns, neg], -1)).squeeze(-1)
        # Update AFTER scoring
        self.mem.set(src, ns); self.mem.set(dst, nd)
        self.mem.update_time(torch.cat([src, dst]), torch.cat([t, t]))
        return {"pos_score": pos_sc, "neg_score": neg_sc,
                "loss": bce_link_loss(pos_sc, neg_sc)}


# ────────────────────────────────────────────────────────────
# 3. TGAT
# ────────────────────────────────────────────────────────────

class TGAT(nn.Module):
    def __init__(self, num_nodes: int, feat_dim: int, hidden: int = 128,
                 device=torch.device("cpu")):
        super().__init__()
        self._fd   = max(feat_dim, 1)
        self.mem   = NodeMemoryStore(num_nodes, hidden, device)
        self.te    = TimeEncoder(hidden)
        self.q     = nn.Linear(hidden * 2, hidden)
        self.k     = nn.Linear(hidden * 2 + self._fd, hidden)
        self.v     = nn.Linear(hidden * 2 + self._fd, hidden)
        self.out   = nn.Linear(hidden, hidden)
        self.norm  = nn.LayerNorm(hidden)
        self.pred  = make_predictor(hidden)

    def reset(self): self.mem.reset()

    def forward(self, src, dst, t, feat, neg_dst, **_):
        dev = src.device
        if feat.shape[-1] == 0: feat = torch.zeros(src.size(0), 1, device=dev)
        h_s, h_d = self.mem.get(src), self.mem.get(dst)
        te = self.te(self.mem.delta_t(src, t))
        q  = self.q(torch.cat([h_s, te], -1)).unsqueeze(1)
        kv = torch.cat([h_d, te, feat], -1)
        k  = self.k(kv).unsqueeze(1); v = self.v(kv).unsqueeze(1)
        a  = torch.softmax((q * k).sum(-1, keepdim=True) / math.sqrt(h_s.size(-1)), 1)
        ns = self.norm(h_s + self.out((a * v).squeeze(1)))
        # Score BEFORE memory update
        neg = self.mem.get(neg_dst)
        pos_sc = self.pred(torch.cat([ns, h_d],  -1)).squeeze(-1)
        neg_sc = self.pred(torch.cat([ns, neg],  -1)).squeeze(-1)
        # Update AFTER scoring
        self.mem.set(src, ns)
        self.mem.update_time(torch.cat([src, dst]), torch.cat([t, t]))
        return {"pos_score": pos_sc, "neg_score": neg_sc,
                "loss": bce_link_loss(pos_sc, neg_sc)}


# ────────────────────────────────────────────────────────────
# 4. TGN
# ────────────────────────────────────────────────────────────

class TGN(nn.Module):
    def __init__(self, num_nodes: int, feat_dim: int, hidden: int = 128,
                 device=torch.device("cpu")):
        super().__init__()
        self._fd   = max(feat_dim, 1)
        self.mem   = NodeMemoryStore(num_nodes, hidden, device)
        self.te    = TimeEncoder(hidden)
        self.msg_s = nn.Linear(hidden * 2 + hidden + self._fd, hidden)
        self.msg_d = nn.Linear(hidden * 2 + hidden + self._fd, hidden)
        self.upd   = nn.GRUCell(hidden, hidden)
        self.emb   = nn.Linear(hidden * 2, hidden)
        self.pred  = make_predictor(hidden)

    def reset(self): self.mem.reset()

    def forward(self, src, dst, t, feat, neg_dst, **_):
        dev = src.device
        if feat.shape[-1] == 0: feat = torch.zeros(src.size(0), 1, device=dev)
        h_s, h_d   = self.mem.get(src), self.mem.get(dst)
        dt_s, dt_d = self.mem.delta_t(src, t), self.mem.delta_t(dst, t)
        te_s       = self.te(dt_s); te_d = self.te(dt_d)
        ms = F.relu(self.msg_s(torch.cat([h_s, h_d, te_s, feat], -1)))
        md = F.relu(self.msg_d(torch.cat([h_d, h_s, te_s, feat], -1)))
        ns = self.upd(ms, h_s); nd = self.upd(md, h_d)
        es = self.emb(torch.cat([ns, te_s], -1))
        ed = self.emb(torch.cat([nd, te_d], -1))
        # Score BEFORE memory update
        dt_n  = self.mem.delta_t(neg_dst, t)
        h_neg = self.mem.get(neg_dst)
        en    = self.emb(torch.cat([h_neg, self.te(dt_n)], -1))
        pos_sc = self.pred(torch.cat([es, ed], -1)).squeeze(-1)
        neg_sc = self.pred(torch.cat([es, en], -1)).squeeze(-1)
        # Update AFTER scoring
        self.mem.set(src, ns); self.mem.set(dst, nd)
        self.mem.update_time(torch.cat([src, dst]), torch.cat([t, t]))
        return {"pos_score": pos_sc, "neg_score": neg_sc,
                "loss": bce_link_loss(pos_sc, neg_sc)}


# ────────────────────────────────────────────────────────────
# 5. GraphMixer
# ────────────────────────────────────────────────────────────

class GraphMixer(nn.Module):
    def __init__(self, num_nodes: int, feat_dim: int, hidden: int = 128,
                 device=torch.device("cpu")):
        super().__init__()
        self._fd  = max(feat_dim, 1)
        self.mem  = NodeMemoryStore(num_nodes, hidden, device)
        self.te   = TimeEncoder(hidden)
        self.mix  = nn.Sequential(
            nn.Linear(hidden + self._fd + hidden, hidden), nn.GELU(),
            nn.Linear(hidden, hidden)
        )
        self.pred = make_predictor(hidden)

    def reset(self): self.mem.reset()

    def forward(self, src, dst, t, feat, neg_dst, **_):
        dev = src.device
        if feat.shape[-1] == 0: feat = torch.zeros(src.size(0), 1, device=dev)
        h_s, h_d = self.mem.get(src), self.mem.get(dst)
        te = self.te(self.mem.delta_t(src, t))
        ns = self.mix(torch.cat([h_s, feat, te], -1))
        nd = self.mix(torch.cat([h_d, feat, te], -1))
        # Score BEFORE memory update
        hn = self.mix(torch.cat([self.mem.get(neg_dst), feat, te], -1))
        pos_sc = self.pred(torch.cat([ns, nd], -1)).squeeze(-1)
        neg_sc = self.pred(torch.cat([ns, hn], -1)).squeeze(-1)
        # Update AFTER scoring
        self.mem.set(src, ns); self.mem.set(dst, nd)
        self.mem.update_time(torch.cat([src, dst]), torch.cat([t, t]))
        return {"pos_score": pos_sc, "neg_score": neg_sc,
                "loss": bce_link_loss(pos_sc, neg_sc)}


# ────────────────────────────────────────────────────────────
# 6. Ablation variants  (inherit SRGNN, override one module)
# ────────────────────────────────────────────────────────────

class SRGNN_noCSN(SRGNN):
    """Skip CSN — all events pass through with salience=1."""
    def forward(self, src, dst, t, feat, neg_dst, rel_type=None):
        dev = self.device; B = src.size(0)
        if feat.shape[-1] == 0: feat = torch.zeros(B, 1, device=dev)
        feat_g = feat
        sal    = torch.ones(B, device=dev)

        dt_src   = self.node_mem.delta_t(src, t)
        edge_st  = self.edge_mem.get_batch(src, dst)
        new_est, edge_ctx = self.ectg(feat_g, sal, dt_src, edge_st)
        self.edge_mem.update_batch(src, dst, new_est)

        h_s, h_d = self.node_mem.get(src), self.node_mem.get(dst)
        all_idx  = torch.unique(torch.cat([src, dst]))
        all_h    = self.node_mem.get(all_idx)
        ns, nd, ph, kl = self.drgc(h_s, h_d, feat_g, edge_ctx, dt_src, new_est[:,5], all_h)
        self.node_mem.set(all_idx, ph)
        self.node_mem.set(src, ns); self.node_mem.set(dst, nd)
        self.node_mem.update_time(torch.cat([src,dst]), torch.cat([t,t]))

        se, de = self.node_mem.get(src), self.node_mem.get(dst)
        ne     = self.node_mem.get(neg_dst)
        ps, ns2, cl, ccs = self.nscp(se, de, ne, new_est)
        pl = bce_link_loss(ps, ns2)
        return {"pos_score": ps, "neg_score": ns2,
                "loss": pl + self.lambda_tip*kl + self.lambda_causal*cl,
                "pred_loss": pl, "tip_loss": kl, "causal_loss": cl,
                "ccs": ccs.mean(), "salience": sal.mean()}


class SRGNN_noTIP(SRGNN):
    """Set TIP beta=0 — no information compression."""
    def forward(self, src, dst, t, feat, neg_dst, rel_type=None):
        old_beta = self.drgc.tip.beta
        self.drgc.tip.beta = 0.0
        out = super().forward(src, dst, t, feat, neg_dst, rel_type)
        self.drgc.tip.beta = old_beta
        return out


class SRGNN_noNSCP(SRGNN):
    """Replace NSCP with a plain MLP (no causal masking)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # override predictor — no causal logic
        self._plain_pred = nn.Linear(self.hidden * 2, 1)

    def forward(self, src, dst, t, feat, neg_dst, rel_type=None):
        dev = self.device; B = src.size(0)
        if feat.shape[-1] == 0: feat = torch.zeros(B, 1, device=dev)
        dt_src   = self.node_mem.delta_t(src, t)
        feat_g, sal = self.csn(feat, dt_src)
        edge_st  = self.edge_mem.get_batch(src, dst)
        new_est, edge_ctx = self.ectg(feat_g, sal, dt_src, edge_st)
        self.edge_mem.update_batch(src, dst, new_est)
        h_s, h_d = self.node_mem.get(src), self.node_mem.get(dst)
        all_idx  = torch.unique(torch.cat([src, dst]))
        all_h    = self.node_mem.get(all_idx)
        ns, nd, ph, kl = self.drgc(h_s, h_d, feat_g, edge_ctx, dt_src, new_est[:,5], all_h)
        self.node_mem.set(all_idx, ph)
        self.node_mem.set(src, ns); self.node_mem.set(dst, nd)
        self.node_mem.update_time(torch.cat([src,dst]), torch.cat([t,t]))
        se, de = self.node_mem.get(src), self.node_mem.get(dst)
        ne     = self.node_mem.get(neg_dst)
        ps = self._plain_pred(torch.cat([se, de], -1)).squeeze(-1)
        ns2= self._plain_pred(torch.cat([se, ne], -1)).squeeze(-1)
        pl = bce_link_loss(ps, ns2)
        return {"pos_score": ps, "neg_score": ns2,
                "loss": pl + self.lambda_tip * kl,
                "pred_loss": pl, "tip_loss": kl,
                "causal_loss": torch.tensor(0.0, device=dev),
                "ccs": torch.tensor(0.0), "salience": sal.mean()}
