"""
EdgeBank — memorization-floor baseline for dynamic link prediction.

Poursafaei, Huang, Pelrine, Rabbany, "Towards Better Evaluation for Dynamic
Link Prediction", NeurIPS 2022 Datasets & Benchmarks.

EdgeBank is a NON-PARAMETRIC, NO-TRAIN heuristic: it predicts a positive whenever
the queried (u, v) pair has been observed in a "memory bank" of past edges. It is
the standard lower-bound / sanity floor for temporal-graph link prediction: a
transductive model that cannot beat EdgeBank is just memorizing, and EdgeBank is
expected to be NEAR-CHANCE on the inductive split (unseen nodes were, by
definition, never banked) — that ~0.5 inductive AP is the POINT of the floor,
not a bug.

Two standard variants (both implemented here, selected at construction):
  - EdgeBank-inf  ("unlimited"): the bank remembers every edge ever observed.
  - EdgeBank-tw   ("time-window"): the bank only remembers edges whose last
    occurrence falls within a recent time window [t - W, t]; older memories
    expire. W is set per-query to a fraction of the observed time span (the
    paper's "fixed time window" = average span of train edges); here we use the
    'fixed' rule: W = window_frac * (t_max_seen - t_min_seen).

HARNESS INTEGRATION (evaluation-harness, B-protocol parity)
--------------------------------------------------
This module conforms to the exact same forward() contract as the other
experiments/models baselines so it runs through the UNCHANGED train.py /
run_baselines_benchmark.py pipeline (identical chronological 70/15/15 split,
identical fair inductive negative pool seen->seen / ind->ind, identical
sklearn AP/AUC). Consequences of fitting the no-train heuristic into a trainer:

  * One dummy nn.Parameter exists ONLY so torch.optim.Adam(model.parameters())
    does not error and so load_state_dict(best_state) is a no-op restore. It is
    detached from the score; gradients do not affect predictions. EdgeBank does
    not learn.
  * The bank is filled in forward() PRE-update: a query is scored against the
    bank state BEFORE the current positive edge is inserted, so a test edge can
    never see itself (no temporal leak — same discipline the harness uses for
    every streaming baseline).
  * train.py calls reset() at the start of every epoch and, before the test
    pass, replays train+val to rebuild the bank, then evaluates test. That
    rebuild-then-query is exactly the EdgeBank protocol (bank = all edges
    strictly before the query). Re-running epochs does not "train" anything; it
    only re-streams identical data, so the floor is deterministic given the
    split.

Scores are membership-based: 1.0 if (u,v) in bank else 0.0. AP/AUC are
rank-based, so binary scores are valid; ties are broken by sklearn's averaging.
A tiny score on the negative is added from the dummy param's zero contribution
only to keep autograd happy; it does not change ranking.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor


class EdgeBank(nn.Module):
    def __init__(self, num_nodes: int, feat_dim: int, hidden: int = 128,
                 variant: str = "inf", window_frac: float = 0.15,
                 device=torch.device("cpu")):
        super().__init__()
        assert variant in ("inf", "tw"), f"EdgeBank variant must be inf|tw, got {variant}"
        self.variant = variant
        self.window_frac = float(window_frac)
        self.num_nodes = num_nodes
        self.device = device
        # Dummy param: keeps Adam + load_state_dict happy. Detached from scoring.
        self._dummy = nn.Parameter(torch.zeros(1))
        # Bank: key = (u,v) undirected pair id -> last-seen timestamp (float).
        # Python dict on host; non-parametric, not part of state_dict.
        self._bank = {}
        self._t_min = float("inf")
        self._t_max = float("-inf")

    def reset(self):
        self._bank = {}
        self._t_min = float("inf")
        self._t_max = float("-inf")

    @staticmethod
    def _keys(u_arr, v_arr):
        """Vectorized undirected-pair keys (EdgeBank treats edges as undirected).
        int64 hash a*K+b with a<=b; K large enough that no pair collides for the
        node-id ranges in these datasets (<1e5 nodes)."""
        u = np.asarray(u_arr, dtype=np.int64)
        v = np.asarray(v_arr, dtype=np.int64)
        a = np.minimum(u, v)
        b = np.maximum(u, v)
        return a * np.int64(100_000_007) + b

    def _query(self, u_arr, v_arr, t_now: float) -> Tensor:
        """Vectorized membership: returns 1.0 where pair is in the bank (and,
        for tw, last-seen within the recent window)."""
        keys = self._keys(u_arr, v_arr)
        n = len(keys)
        out = np.zeros(n, dtype=np.float32)
        if not self._bank:
            return torch.from_numpy(out).to(self.device)
        if self.variant == "tw" and self._t_max > self._t_min:
            window = self.window_frac * (self._t_max - self._t_min)
            lo = t_now - window
        else:
            lo = None  # inf variant: any past occurrence counts
        bank = self._bank
        for i in range(n):  # dict lookups only (no numpy per-row), fast in CPython
            last = bank.get(keys[i])
            if last is not None and (lo is None or last >= lo):
                out[i] = 1.0
        return torch.from_numpy(out).to(self.device)

    def _insert(self, u_arr, v_arr, t_arr):
        """Vectorized bank update: dedup to last-seen-ts per key in this batch,
        then merge into the host dict (one dict write per unique key)."""
        keys = self._keys(u_arr, v_arr)
        t = np.asarray(t_arr, dtype=np.float64)
        if len(t):
            tmn = float(t.min()); tmx = float(t.max())
            if tmn < self._t_min: self._t_min = tmn
            if tmx > self._t_max: self._t_max = tmx
        # Reduce to max-ts per unique key within the batch (chronological batch
        # => last occurrence wins anyway; max is order-independent + correct).
        order = np.argsort(t, kind="stable")
        k_sorted = keys[order]; t_sorted = t[order]
        bank = self._bank
        for k, ti in zip(k_sorted.tolist(), t_sorted.tolist()):
            prev = bank.get(k)
            if prev is None or ti > prev:
                bank[k] = ti

    def forward(self, src, dst, t, feat, neg_dst, **_):
        dev = src.device
        src_np = src.detach().cpu().numpy()
        dst_np = dst.detach().cpu().numpy()
        neg_np = neg_dst.detach().cpu().numpy()
        t_np = t.detach().cpu().numpy()
        t_now = float(t_np.max()) if len(t_np) else self._t_max

        # SCORE BEFORE INSERT (no leak): query bank as of strictly-prior state.
        pos_sc = self._query(src_np, dst_np, t_now).to(dev)
        neg_sc = self._query(src_np, neg_np, t_now).to(dev)

        # Attach dummy param's zero so autograd has a graph; does not alter ranks.
        zero = self._dummy.sum() * 0.0
        pos_sc = pos_sc + zero
        neg_sc = neg_sc + zero

        # INSERT current positives into bank AFTER scoring.
        self._insert(src_np, dst_np, t_np)

        B = src.size(0)
        loss = F.binary_cross_entropy_with_logits(
            torch.cat([pos_sc, neg_sc]),
            torch.cat([torch.ones(B, device=dev), torch.zeros(B, device=dev)])
        )
        return {"pos_score": pos_sc, "neg_score": neg_sc, "loss": loss}


class EdgeBankInf(EdgeBank):
    def __init__(self, num_nodes, feat_dim, hidden=128, device=torch.device("cpu")):
        super().__init__(num_nodes, feat_dim, hidden, variant="inf", device=device)


class EdgeBankTW(EdgeBank):
    def __init__(self, num_nodes, feat_dim, hidden=128, window_frac=0.15,
                 device=torch.device("cpu")):
        super().__init__(num_nodes, feat_dim, hidden, variant="tw",
                         window_frac=window_frac, device=device)
