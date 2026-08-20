"""
DyGFormer — Transformer-based temporal graph model (Yu et al., NeurIPS 2023)

Key ideas:
  - Patches interaction sequences into fixed-length segments
  - Applies Transformer encoder over patched sequences
  - Uses neighbor co-occurrence encoding

Simplified implementation focusing on core mechanism:
  patch-based temporal attention over recent interaction history.
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
from .sr_gnn import NodeMemoryStore, TimeEncoder


class PatchEncoder(nn.Module):
    """Encode a sequence of recent interactions into patch embeddings.

    REIMPL FIX (evaluation-harness: the original forward() declared a
    required `hist_time` arg that the caller (dygformer.py:114) never passed,
    raising TypeError on every run — this is why the model was excluded as
    "BROKEN" in run_baselines_benchmark.py. The patch input already carries the
    time encoding (concatenated in _encode_node), so `hist_time` is vestigial;
    it is now optional/ignored. The `in_dim` is passed explicitly so the
    co-occurrence channel can widen the projection.
    """
    def __init__(self, in_dim: int, hidden: int, patch_size: int = 4):
        super().__init__()
        self.patch_size = patch_size
        self.proj = nn.Linear(in_dim, hidden)

    def forward(self, hist_feat: Tensor, hist_time: Tensor = None) -> Tensor:
        # hist_feat: (B, seq_len, in_dim)
        B, L, D = hist_feat.shape
        # Pad to multiple of patch_size
        pad = (self.patch_size - L % self.patch_size) % self.patch_size
        if pad > 0:
            hist_feat = F.pad(hist_feat, (0, 0, 0, pad))
        # Reshape into patches and mean-pool each patch
        n_patches = hist_feat.shape[1] // self.patch_size
        patches = hist_feat.reshape(B, n_patches, self.patch_size, D).mean(dim=2)  # (B, n_patches, D)
        return self.proj(patches)  # (B, n_patches, hidden)


class DyGFormer(nn.Module):
    """
    Simplified DyGFormer: Transformer over patched interaction history.
    """
    def __init__(self, num_nodes: int, feat_dim: int, hidden: int = 128,
                 n_heads: int = 4, n_layers: int = 2, hist_len: int = 20,
                 device=torch.device("cpu")):
        super().__init__()
        self._fd = max(feat_dim, 1)
        self.hidden = hidden
        self.hist_len = hist_len
        self.device = device

        self.mem = NodeMemoryStore(num_nodes, hidden, device)
        self.time_enc = TimeEncoder(hidden)

        # History storage: last hist_len interactions per node
        self.node_hist_feat = torch.zeros(num_nodes, hist_len, self._fd, device=device)
        self.node_hist_time = torch.zeros(num_nodes, hist_len, device=device)
        self.node_hist_ptr = torch.zeros(num_nodes, dtype=torch.long, device=device)
        # Neighbor-id ring buffer (parallel to feat/time) for co-occurrence encoding.
        self.node_hist_nbr = torch.full((num_nodes, hist_len), -1,
                                        dtype=torch.long, device=device)

        # Neighbor co-occurrence encoding (DyGFormer's defining contribution):
        # for each history slot, encode how often that neighbor co-appears in the
        # partner node's history. Scalar count -> small MLP -> hidden//4 channel.
        self._cooc_dim = max(hidden // 4, 8)
        self.cooc_enc = nn.Sequential(
            nn.Linear(2, self._cooc_dim), nn.ReLU(),
            nn.Linear(self._cooc_dim, self._cooc_dim),
        )

        # Patch encoder: input = feat + time_enc + intensity(1) + cooc(self._cooc_dim)
        self.patch_enc = PatchEncoder(self._fd + hidden + 1 + self._cooc_dim,
                                      hidden, patch_size=4)

        # Transformer encoder
        enc_layer = nn.TransformerEncoderLayer(
            d_model=hidden, nhead=n_heads, dim_feedforward=hidden*2,
            dropout=0.1, batch_first=True
        )
        self.transformer = nn.TransformerEncoder(enc_layer, num_layers=n_layers)

        # Projection from transformer output to node embedding
        self.out_proj = nn.Linear(hidden, hidden)

        # Predictor
        self.pred = nn.Sequential(
            nn.Linear(hidden * 2, hidden), nn.ReLU(), nn.Linear(hidden, 1)
        )

    def reset(self):
        self.mem.reset()
        self.node_hist_feat.zero_()
        self.node_hist_time.zero_()
        self.node_hist_ptr.zero_()
        self.node_hist_nbr.fill_(-1)

    def _get_hist(self, idx: Tensor) -> Tensor:
        """Get interaction history for nodes. Returns (B, hist_len, feat_dim)."""
        return self.node_hist_feat[idx]

    def _update_hist(self, idx: Tensor, nbr: Tensor, feat: Tensor, t: Tensor):
        """Append new interaction to history buffer (ring buffer)."""
        for i in range(len(idx)):
            nid = int(idx[i])
            ptr = int(self.node_hist_ptr[nid]) % self.hist_len
            self.node_hist_feat[nid, ptr] = feat[i].detach()
            self.node_hist_time[nid, ptr] = t[i].detach()
            self.node_hist_nbr[nid, ptr] = int(nbr[i])
            self.node_hist_ptr[nid] = ptr + 1

    def _cooccurrence(self, idx_a: Tensor, idx_b: Tensor) -> Tensor:
        """Per-slot neighbor co-occurrence counts for node a's history relative
        to node b's history (DyGFormer's neighbor-cooccurrence scheme).

        Returns (B, hist_len, 2): channel 0 = count of slot-neighbor within a's
        own history, channel 1 = count of that neighbor within b's history.
        """
        nbr_a = self.node_hist_nbr[idx_a]   # (B, L) neighbor ids in a's history
        nbr_b = self.node_hist_nbr[idx_b]   # (B, L)
        # (B, L, L) equality tensors; -1 padding never matches a real id<... 0>
        valid_a = (nbr_a >= 0).unsqueeze(-1)            # (B, L, 1)
        eq_self = (nbr_a.unsqueeze(-1) == nbr_a.unsqueeze(1)) & valid_a
        eq_cross = (nbr_a.unsqueeze(-1) == nbr_b.unsqueeze(1)) & valid_a
        cnt_self = eq_self.sum(-1).float()              # (B, L)
        cnt_cross = eq_cross.sum(-1).float()            # (B, L)
        return torch.stack([cnt_self, cnt_cross], dim=-1)  # (B, L, 2)

    def _encode_node(self, idx: Tensor, t: Tensor, partner: Tensor) -> Tensor:
        """Encode node using Transformer over interaction history + co-occurrence
        relative to `partner` node's history."""
        B = idx.size(0)
        hist = self._get_hist(idx)  # (B, hist_len, feat_dim)

        # Time encoding for history
        hist_t = self.node_hist_time[idx]  # (B, hist_len)
        dt = (t.unsqueeze(-1) - hist_t).clamp(min=0)  # (B, hist_len)

        # Neighbor co-occurrence channel (vs partner history)
        cooc = self._cooccurrence(idx, partner)        # (B, L, 2)
        cooc_emb = self.cooc_enc(cooc)                  # (B, L, cooc_dim)

        # Create patch input: [feat; time_enc; intensity; cooc]
        t_enc = self.time_enc(dt.reshape(-1)).reshape(B, self.hist_len, self.hidden)
        intensity = (hist.abs().sum(-1, keepdim=True) > 0.01).float()  # active history slots
        patch_input = torch.cat([hist, t_enc, intensity, cooc_emb], dim=-1)

        # Patch and transform
        patches = self.patch_enc(patch_input)  # (B, n_patches, hidden)
        transformed = self.transformer(patches)  # (B, n_patches, hidden)

        # Pool: use mean of all patches
        emb = self.out_proj(transformed.mean(dim=1))  # (B, hidden)
        return emb

    def forward(self, src, dst, t, feat, neg_dst, **_):
        dev = src.device
        if feat.shape[-1] == 0:
            feat = torch.zeros(src.size(0), 1, device=dev)

        # Encode nodes using Transformer over history.
        # Co-occurrence is computed pairwise: src vs dst (pos), src vs neg (neg).
        src_emb = self._encode_node(src, t, dst)
        dst_emb = self._encode_node(dst, t, src)

        # Score BEFORE updating history
        src_emb_neg = self._encode_node(src, t, neg_dst)
        neg_emb = self._encode_node(neg_dst, t, src)
        pos_sc = self.pred(torch.cat([src_emb, dst_emb], -1)).squeeze(-1)
        neg_sc = self.pred(torch.cat([src_emb_neg, neg_emb], -1)).squeeze(-1)

        # Update history AFTER scoring (PRE-update leak-free, matches harness)
        self._update_hist(src, dst, feat, t)
        self._update_hist(dst, src, feat, t)

        # Update memory for compatibility
        self.mem.set(src, src_emb)
        self.mem.set(dst, dst_emb)
        self.mem.update_time(torch.cat([src, dst]), torch.cat([t, t]))

        B = src.size(0)
        loss = F.binary_cross_entropy_with_logits(
            torch.cat([pos_sc, neg_sc]),
            torch.cat([torch.ones(B, device=dev), torch.zeros(B, device=dev)])
        )
        return {"pos_score": pos_sc, "neg_score": neg_sc, "loss": loss}
