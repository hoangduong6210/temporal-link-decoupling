"""
One-shot migration: apply the disjoint bipartite id remap (the download.py fix)
to the EXISTING wikipedia.npz / mooc.npz, preserving the edge stream exactly.

Why not just re-run download.py from the raw CSV?
  The wikipedia.npz on disk was built from a TRUNCATED wikipedia.csv download
  (157,469 edges; the full SNAP file has 157,474 rows). Re-preprocessing from a
  fresh CSV would silently change the edge stream -- and therefore every result
  already produced, plus CoEdit. This migration changes ONLY the id namespace.

Validity: it was verified that the old node_map was the IDENTITY for both
datasets (users occupy 0..num_users-1, items occupy 0..num_items-1 which is a
subset of the user range, union == user range). Hence the stored `sources` are
raw user ids and the stored `destinations` are raw item ids, and applying
    destinations += num_users
reproduces exactly what the fixed preprocess_dataset() emits.
"""
import os
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKUP = PROJECT_ROOT / "resources" / "corpora" / "pre_idfix"
OUTPUT_DIR = PROJECT_ROOT / "resources" / "staging"


def migrate(name):
    old = np.load(BACKUP / f"{name}.npz", allow_pickle=False)
    src, dst = old["sources"], old["destinations"]

    uu, ui = np.unique(src), np.unique(dst)
    num_users, num_items = len(uu), len(ui)

    # Precondition: identity node_map (users contiguous from 0, items a 0-based
    # contiguous block inside it). If this fails, the derivation is invalid.
    assert np.array_equal(uu, np.arange(num_users)), f"{name}: users not 0..N-1"
    assert np.array_equal(ui, np.arange(num_items)), f"{name}: items not 0..M-1"

    new_src = src.copy()
    new_dst = dst + num_users
    num_nodes = num_users + num_items

    assert len(np.intersect1d(np.unique(new_src), np.unique(new_dst))) == 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"{name}.npz"
    np.savez(out,
             sources=new_src,
             destinations=new_dst,
             timestamps=old["timestamps"],
             labels=old["labels"],
             features=old["features"],
             num_nodes=np.array([num_nodes]),
             num_edges=np.array([len(new_src)]),
             feat_dim=np.array([old["features"].shape[1]]))
    print(f"[fixed] {name}: {num_users} users + {num_items} items = {num_nodes} nodes, "
          f"{len(new_src)} edges, feat_dim={old['features'].shape[1]}")


if __name__ == "__main__":
    for n in ["wikipedia", "mooc"]:
        migrate(n)
