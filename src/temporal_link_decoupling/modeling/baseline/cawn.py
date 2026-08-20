"""
CAWN — Causal Anonymous Walk (Wang et al., ICLR 2021)

Key ideas:
  - Extracts causal anonymous walks from temporal neighborhood
  - Uses RNN to encode walk sequences
  - Anonymous: node identities replaced by temporal ordering

Simplified implementation: temporal walk encoding with anonymized node features.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
from .sr_gnn import NodeMemoryStore, TimeEncoder


class CAWN(nn.Module):
    """
    Simplified CAWN: temporal walk encoding with anonymized features.
    Uses node memory + temporal encoding as proxy for full walk extraction.
    """
    def __init__(self, num_nodes: int, feat_dim: int, hidden: int = 128,
                 walk_len: int = 3, n_walks: int = 5,
                 device=torch.device("cpu")):
        super().__init__()
        self._fd = max(feat_dim, 1)
        self.hidden = hidden
        self.device = device

        self.mem = NodeMemoryStore(num_nodes, hidden, device)
        self.time_enc = TimeEncoder(hidden)

        # Walk encoder: processes anonymized walk features via GRU
        self.walk_gru = nn.GRU(hidden + self._fd, hidden, batch_first=True)

        # Combine walk embeddings
        self.walk_agg = nn.Sequential(
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden)
        )

        # Interaction encoder: current event features
        self.event_enc = nn.Sequential(
            nn.Linear(hidden * 2 + hidden + self._fd, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden)
        )

        # Memory updater
        self.gru_update = nn.GRUCell(hidden, hidden)

        # Predictor
        self.pred = nn.Sequential(
            nn.Linear(hidden * 2, hidden), nn.ReLU(), nn.Linear(hidden, 1)
        )

    def reset(self):
        self.mem.reset()

    def _encode_walk(self, node_idx: Tensor, t: Tensor, feat: Tensor) -> Tensor:
        """Encode temporal walk from node's perspective using memory + time."""
        B = node_idx.size(0)
        h = self.mem.get(node_idx)  # (B, hidden)
        dt = self.mem.delta_t(node_idx, t)
        t_enc = self.time_enc(dt)  # (B, hidden)

        # Simulate walk: use node memory as proxy for walk encoding
        # In full CAWN, this would extract actual walks from temporal graph
        walk_input = torch.cat([t_enc, feat], dim=-1).unsqueeze(1)  # (B, 1, hidden+fd)
        walk_out, _ = self.walk_gru(walk_input, h.unsqueeze(0))  # (B, 1, hidden)
        walk_emb = self.walk_agg(walk_out.squeeze(1))  # (B, hidden)

        return walk_emb

    def forward(self, src, dst, t, feat, neg_dst, **_):
        dev = src.device
        if feat.shape[-1] == 0:
            feat = torch.zeros(src.size(0), 1, device=dev)

        # Get current memories
        h_s, h_d = self.mem.get(src), self.mem.get(dst)
        dt = self.mem.delta_t(src, t)
        t_enc = self.time_enc(dt)

        # Encode walks
        walk_s = self._encode_walk(src, t, feat)
        walk_d = self._encode_walk(dst, t, feat)

        # Event encoding
        event_feat = torch.cat([walk_s, walk_d, t_enc, feat], dim=-1)
        new_emb = self.event_enc(event_feat)

        # Update memories
        new_s = self.gru_update(new_emb, h_s)
        new_d = self.gru_update(new_emb, h_d)

        # Score BEFORE memory update
        neg_emb = self.mem.get(neg_dst)
        walk_neg = self._encode_walk(neg_dst, t, feat)
        neg_event = self.event_enc(torch.cat([walk_s, walk_neg, t_enc, feat], dim=-1))
        neg_final = self.gru_update(neg_event, self.mem.get(neg_dst))

        pos_sc = self.pred(torch.cat([new_s, new_d], -1)).squeeze(-1)
        neg_sc = self.pred(torch.cat([new_s, neg_final], -1)).squeeze(-1)

        # Update AFTER scoring
        self.mem.set(src, new_s)
        self.mem.set(dst, new_d)
        self.mem.update_time(torch.cat([src, dst]), torch.cat([t, t]))

        B = src.size(0)
        loss = F.binary_cross_entropy_with_logits(
            torch.cat([pos_sc, neg_sc]),
            torch.cat([torch.ones(B, device=dev), torch.zeros(B, device=dev)])
        )
        return {"pos_score": pos_sc, "neg_score": neg_sc, "loss": loss}
