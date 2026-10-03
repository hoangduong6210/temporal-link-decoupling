"""Protocol wrapper around the pinned, externally fetched original TGN modules.

Upstream: twitter-research/tgn, Apache-2.0. No upstream source is vendored here.
The wrapper separates pure candidate queries from real-event observation.
"""
from __future__ import annotations

import importlib
import importlib.machinery
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[3]


def checked_upstream():
    registry = json.loads((ROOT / "configs/tgn-upstream.json").read_text())
    value = os.environ.get("LP_TGN_SOURCE")
    if not value:
        raise RuntimeError("LP_TGN_SOURCE must name the pinned external TGN checkout")
    source = Path(value).resolve()
    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()
    if git("rev-parse", "HEAD") != registry["commit"] or git("status", "--porcelain"):
        raise RuntimeError("external TGN checkout does not match its clean pinned source")
    for name in ["model", "modules", "utils"]:
        existing = sys.modules.get(name)
        if existing:
            # Upstream uses namespace packages without __init__.py in some
            # directories; those have __file__=None and a package search path.
            locations = ([existing.__file__] if getattr(existing, "__file__", None)
                         else list(getattr(existing, "__path__", [])))
            if not locations or any(not Path(location).resolve().is_relative_to(source) for location in locations):
                raise RuntimeError("TGN import namespace already belongs to another package")
        else:
            # Register only upstream's explicit package namespaces, without
            # changing the process-wide module search path.
            spec = importlib.machinery.PathFinder.find_spec(name, [str(source)])
            if spec is None:
                raise RuntimeError("registered TGN package namespace is missing")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            if spec.loader is not None:
                spec.loader.exec_module(module)
    return importlib.import_module("model.tgn").TGN, importlib.import_module("utils.utils").get_neighbor_finder


class UpstreamTGN(nn.Module):
    """Original attention/memory/readout modules with an explicit score/observe API.

    Dimensions, neighborhood count and dropout are pilot settings, not a claim
    to reproduce the published benchmark configuration or original evaluator.
    """
    def __init__(self, data, hidden=32, *, neighbors=10):
        super().__init__()
        TGN, get_neighbor_finder = checked_upstream()
        self.data = data
        self.neighbors = neighbors
        self.num_nodes = int(data["num_nodes"])
        # Zero is upstream's padding identity; project corpus identities start at zero.
        edges = np.arange(1, len(data["sources"]) + 1)
        graph = SimpleNamespace(sources=data["sources"] + 1, destinations=data["destinations"] + 1,
                                timestamps=data["timestamps"], edge_idxs=edges)
        finder = get_neighbor_finder(graph, uniform=False, max_node_idx=self.num_nodes)
        node_features = np.zeros((self.num_nodes + 1, hidden), dtype=np.float32)
        edge_features = np.concatenate([np.zeros((1, data["feat_dim"]), dtype=np.float32), data["features"]])
        self.core = TGN(finder, node_features, edge_features, torch.device("cpu"),
                        n_layers=1, n_heads=2, dropout=0., use_memory=True,
                        memory_update_at_start=True, memory_dimension=hidden,
                        message_dimension=hidden, embedding_module_type="graph_attention",
                        message_function="identity", aggregator_type="last",
                        memory_updater_type="gru", n_neighbors=neighbors)
        self.reset()

    def reset(self):
        self.core.memory.__init_memory__()
        self.observed_events = 0
        self.watermark = -math.inf

    def _arrays(self, src, dst, t):
        if src.ndim != 1 or dst.shape != src.shape or t.shape != src.shape or not len(src):
            raise ValueError("queries must be aligned nonempty vectors")
        if src.dtype != torch.long or dst.dtype != torch.long:
            raise ValueError("query endpoints must be integer tensors")
        if bool(((src < 0) | (dst < 0) | (src >= self.num_nodes) | (dst >= self.num_nodes)).any()):
            raise ValueError("query endpoint outside node catalogue")
        if not bool(torch.isfinite(t).all()) or bool((t <= self.watermark).any()):
            raise ValueError("query must follow observed history")
        if self.observed_events < len(self.data["timestamps"]) and bool((t > self.data["timestamps"][self.observed_events]).any()):
            raise ValueError("chronological replay must observe earlier events before querying")
        return src.cpu().numpy() + 1, dst.cpu().numpy() + 1, t.cpu().numpy()

    def score_candidates(self, src, dst, t):
        source, destination, timestamp = self._arrays(src, dst, t)
        # Visiting only existing message keys avoids defaultdict insertion during
        # a query. This computes pending updates without committing memory.
        memory, _ = self.core.get_updated_memory(list(self.core.memory.messages), self.core.memory.messages)
        nodes = np.concatenate([source, destination])
        times = np.concatenate([timestamp, timestamp])
        embeddings = self.core.embedding_module.compute_embedding(
            memory=memory, source_nodes=nodes, timestamps=times,
            n_layers=self.core.n_layers, n_neighbors=self.neighbors)
        count = len(source)
        return self.core.affinity_score(embeddings[:count], embeddings[count:]).reshape(-1)

    @torch.no_grad()
    def observe_group(self, src, dst, t, features, *, backward_auxiliary=False):
        source, destination, timestamp = self._arrays(src, dst, t)
        if not bool((t == t[0]).all()):
            raise ValueError("observation requires a complete timestamp group")
        start, stop = self.observed_events, self.observed_events + len(src)
        expected = self.data
        if stop < len(expected["timestamps"]) and expected["timestamps"][stop] == float(t[0]):
            raise ValueError("observation cannot split a timestamp group")
        if (not np.array_equal(source - 1, expected["sources"][start:stop]) or
                not np.array_equal(destination - 1, expected["destinations"][start:stop]) or
                not np.array_equal(timestamp, expected["timestamps"][start:stop]) or
                not np.array_equal(features.cpu().numpy(), expected["features"][start:stop])):
            raise ValueError("observation must replay the exact chronological event stream")
        # Upstream last-message aggregation keeps a stable final message within
        # timestamp ties. All queries precede this call; no optimizer step occurs here.
        self.core.compute_temporal_embeddings(source, destination, destination, timestamp,
                                               np.arange(start + 1, stop + 1), self.neighbors)
        self.core.memory.detach_memory()
        self.observed_events = stop
        self.watermark = float(t[0])
        return 0.  # Original TGN has no SR-GNN auxiliary objective.
