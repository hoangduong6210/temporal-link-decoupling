"""
Build a NON-BIPARTITE temporal graph from Wikipedia data.

Wikipedia original: user → page (bipartite)
Co-edit graph: user ↔ user (non-bipartite)
  Edge (u1, u2, t) exists when u1 and u2 edit the SAME page within
  a time window, creating a co-editing relationship.

This is a standard construction used in collaboration network analysis.
"""

import argparse
import json
import numpy as np
from collections import defaultdict
from pathlib import Path

from _artifacts import save_npz_deterministic, sha256_file

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STAGING_DIR = PROJECT_ROOT / "resources" / "staging"
SOURCE_REGISTRY = PROJECT_ROOT / "resources" / "source_registry.json"


def build_coedit_graph(
    window_minutes: int = 60,
    max_events: int = 80000,
    input_dir: Path = STAGING_DIR,
    output_dir: Path = STAGING_DIR,
) -> Path:
    """
    Build user-user co-editing temporal graph from Wikipedia.

    For each page, find pairs of users who edit within `window_minutes`
    of each other. Each such pair creates a co-edit event.
    """
    # Load Wikipedia
    wiki = np.load(input_dir / "wikipedia.npz", allow_pickle=False)
    src = wiki['sources']       # users
    dst = wiki['destinations']  # pages
    timestamps = wiki['timestamps']
    features = wiki['features']
    num_orig = int(wiki['num_nodes'][0])

    print(f"Wikipedia: {len(src)} events, {num_orig} nodes")

    # Group edits by page
    page_edits = defaultdict(list)  # page_id → [(user, time, feat_idx)]
    for i in range(len(src)):
        page_edits[int(dst[i])].append((int(src[i]), float(timestamps[i]), i))

    # Build co-edit events
    window = window_minutes * 60  # convert to seconds (timestamps are in seconds)
    co_sources, co_dests, co_times, co_feats = [], [], [], []

    # Collect all unique users that appear as src
    all_users = sorted(set(src.tolist()))
    user_remap = {u: i for i, u in enumerate(all_users)}
    num_users = len(all_users)

    print(f"Unique users: {num_users}")
    print(f"Building co-edit graph (window={window_minutes}min)...")

    event_count = 0
    for page_id, edits in page_edits.items():
        edits.sort(key=lambda x: x[1])  # sort by time
        for i in range(len(edits)):
            for j in range(i + 1, len(edits)):
                u1, t1, fi = edits[i]
                u2, t2, fj = edits[j]
                if u1 == u2:
                    continue
                if t2 - t1 > window:
                    break  # sorted, no need to check further

                # Co-edit event: average features of the two edits
                co_sources.append(user_remap[u1])
                co_dests.append(user_remap[u2])
                co_times.append((t1 + t2) / 2.0)
                avg_feat = (features[fi] + features[fj]) / 2.0
                co_feats.append(avg_feat)

                event_count += 1
                if event_count >= max_events:
                    break
            if event_count >= max_events:
                break
        if event_count >= max_events:
            break

    co_sources = np.array(co_sources, dtype=np.int64)
    co_dests = np.array(co_dests, dtype=np.int64)
    co_times = np.array(co_times, dtype=np.float64)
    co_feats = np.array(co_feats, dtype=np.float32)

    # Normalize timestamps
    co_times = co_times - co_times.min()

    # Sort by time
    sort_idx = np.argsort(co_times, kind="stable")
    co_sources = co_sources[sort_idx]
    co_dests = co_dests[sort_idx]
    co_times = co_times[sort_idx]
    co_feats = co_feats[sort_idx]

    feat_dim = co_feats.shape[1]

    print(f"Co-edit graph: {len(co_sources)} events, {num_users} users, feat_dim={feat_dim}")

    # Verify non-bipartite: check if same nodes appear as both src and dst
    src_set = set(co_sources.tolist())
    dst_set = set(co_dests.tolist())
    overlap = src_set & dst_set
    print(f"  Src nodes: {len(src_set)}, Dst nodes: {len(dst_set)}, Overlap: {len(overlap)}")
    print(f"  Non-bipartite: {'YES' if len(overlap) > len(src_set) * 0.5 else 'WEAK'}")

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "coedit.npz"
    save_npz_deterministic(out_path, {
        "sources": co_sources,
        "destinations": co_dests,
        "timestamps": co_times,
        "labels": np.zeros(len(co_sources), dtype=np.int64),
        "features": co_feats,
        "num_nodes": np.array([num_users], dtype=np.int64),
        "num_edges": np.array([len(co_sources)], dtype=np.int64),
        "feat_dim": np.array([feat_dim], dtype=np.int64),
    })

    registry = json.loads(SOURCE_REGISTRY.read_text(encoding="utf-8"))
    expected = str(registry["datasets"]["coedit"]["processed_sha256"]).lower()
    actual = sha256_file(out_path)
    if expected and not expected.startswith("pending-") and actual != expected:
        raise ValueError(
            f"coedit: processed checksum mismatch: expected {expected}, got {actual}"
        )

    print(f"[saved] {out_path}")
    return out_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=STAGING_DIR)
    parser.add_argument("--output-dir", type=Path, default=STAGING_DIR)
    args = parser.parse_args()
    build_coedit_graph(input_dir=args.input_dir, output_dir=args.output_dir)
