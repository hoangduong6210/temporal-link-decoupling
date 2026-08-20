"""
Download and preprocess temporal graph datasets.
Datasets: Wikipedia, Reddit, MOOC (from Jodie / TGB benchmarks)
Format: each row = (source, destination, timestamp, edge_idx, [features])
"""
import argparse
import json
import numpy as np
import pandas as pd
import urllib.request
from pathlib import Path

from _artifacts import save_npz_deterministic, sha256_file

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "resources" / "staging"
SOURCE_REGISTRY = PROJECT_ROOT / "resources" / "source_registry.json"


def _registry() -> dict[str, object]:
    return json.loads(SOURCE_REGISTRY.read_text(encoding="utf-8"))


def _source_record(name: str) -> dict[str, object]:
    datasets = _registry().get("datasets", {})
    if not isinstance(datasets, dict) or name not in datasets:
        raise ValueError(f"Dataset is not in the reviewed source registry: {name}")
    record = datasets[name]
    if not isinstance(record, dict) or record.get("kind") != "upstream_csv":
        raise ValueError(f"Dataset is not an upstream CSV source: {name}")
    return record


def download_dataset(name: str, data_dir: Path = DATA_DIR):
    """Acquire and preprocess one checksum-pinned upstream CSV explicitly."""
    name = name.lower()
    data_dir.mkdir(parents=True, exist_ok=True)
    record = _source_record(name)
    raw_path = data_dir / f"{name}.csv"
    processed_path = data_dir / f"{name}.npz"
    expected_raw = str(record["raw_sha256"]).lower()
    expected_processed = str(record.get("processed_sha256", "")).lower()

    if not raw_path.exists():
        temporary = raw_path.with_suffix(raw_path.suffix + ".part")
        print(f"[↓] Downloading {name} from {record['url']}...")
        try:
            with urllib.request.urlopen(str(record["url"]), timeout=60) as response, temporary.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            if sha256_file(temporary) != expected_raw:
                raise ValueError(f"{name}: downloaded raw checksum mismatch")
            temporary.replace(raw_path)
        finally:
            temporary.unlink(missing_ok=True)

    actual_raw = sha256_file(raw_path)
    expected_bytes = int(record["raw_bytes"])
    if raw_path.stat().st_size != expected_bytes:
        raise ValueError(
            f"{name}: raw byte length mismatch: expected {expected_bytes}, "
            f"got {raw_path.stat().st_size}"
        )
    if actual_raw != expected_raw:
        raise ValueError(
            f"{name}: raw checksum mismatch: expected {expected_raw}, got {actual_raw}"
        )

    preprocess_dataset(name, raw_path, data_dir)
    actual_processed = sha256_file(processed_path)
    if (
        expected_processed
        and not expected_processed.startswith("pending-")
        and actual_processed != expected_processed
    ):
        raise ValueError(
            f"{name}: processed checksum mismatch: expected "
            f"{expected_processed}, got {actual_processed}"
        )
    return load_dataset(name, data_dir)


def preprocess_dataset(name: str, raw_path: Path, data_dir: Path = DATA_DIR):
    """Parse Jodie CSV format into structured arrays."""
    print(f"[⚙] Preprocessing {name}...")

    df = pd.read_csv(raw_path, skiprows=1, header=None)

    # Jodie format: user_id, item_id, timestamp, state_label, comma-separated features
    sources = df.iloc[:, 0].values.astype(np.int64)
    destinations = df.iloc[:, 1].values.astype(np.int64)
    timestamps = df.iloc[:, 2].values.astype(np.float64)
    labels = df.iloc[:, 3].values.astype(np.int64)

    # Features: remaining columns
    features = np.nan_to_num(
        df.iloc[:, 4:].values.astype(np.float32),
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    # Re-index nodes into a DISJOINT bipartite id space.
    #
    # The Jodie CSV format is BIPARTITE: `user_id` and `item_id` are two
    # INDEPENDENT id namespaces, each numbered from 0. Concatenating them and
    # taking np.unique() merges the two namespaces, so user k and item k are
    # assigned the SAME node id -- they then share a row in every node-indexed
    # store (node memory, echo memory, ...). Instead, give users the low block
    # and offset the items above them:
    #     users -> [0, num_users)
    #     items -> [num_users, num_users + num_items)
    unique_users = np.unique(sources)
    unique_items = np.unique(destinations)
    num_users = len(unique_users)
    num_items = len(unique_items)

    user_map = {old: new for new, old in enumerate(unique_users)}
    item_map = {old: num_users + new for new, old in enumerate(unique_items)}

    sources = np.array([user_map[s] for s in sources], dtype=np.int64)
    destinations = np.array([item_map[d] for d in destinations], dtype=np.int64)

    # Normalize timestamps to start from 0
    timestamps = timestamps - timestamps.min()

    # Sort by time. kind="stable" so that events sharing a timestamp keep their
    # original CSV order -- the default (quicksort) permutes ties differently
    # between runs, which makes the resulting .npz non-reproducible.
    sort_idx = np.argsort(timestamps, kind="stable")
    sources = sources[sort_idx]
    destinations = destinations[sort_idx]
    timestamps = timestamps[sort_idx]
    labels = labels[sort_idx]
    features = features[sort_idx]

    # TRUE total node count: users and items are disjoint, so they add.
    num_nodes = num_users + num_items
    num_edges = len(sources)
    feat_dim = features.shape[1]

    # Integrity: the two namespaces must not overlap after the remap.
    assert len(np.intersect1d(np.unique(sources), np.unique(destinations))) == 0, \
        "user/item id namespaces overlap after remap"

    processed_path = data_dir / f"{name}.npz"
    save_npz_deterministic(processed_path, {
        "sources": sources,
        "destinations": destinations,
        "timestamps": timestamps,
        "labels": labels,
        "features": features,
        "num_nodes": np.array([num_nodes], dtype=np.int64),
        "num_edges": np.array([num_edges], dtype=np.int64),
        "feat_dim": np.array([feat_dim], dtype=np.int64),
    })

    print(f"[✓] {name}: {num_nodes} nodes ({num_users} users + {num_items} items), "
          f"{num_edges} edges, feat_dim={feat_dim}")
    return load_dataset(name, data_dir)


def load_dataset(name: str, data_dir: Path = DATA_DIR):
    """Load preprocessed dataset."""
    if name == "coedit" and not (data_dir / "coedit.npz").exists():
        raise FileNotFoundError("Run build_coedit.py to create the staged CoEdit corpus.")
    path = data_dir / f"{name}.npz"
    data = np.load(path, allow_pickle=False)
    # Sanitize features: the Jodie wikipedia.csv has a truncated final row whose
    # trailing feature fields are NaN (edge 157468, cols 149-171). Identity on
    # mooc/coedit (0 NaN/inf), so this does not perturb their numerics.
    features = np.nan_to_num(data["features"].astype(np.float32),
                             nan=0.0, posinf=0.0, neginf=0.0)
    return {
        "sources": data["sources"],
        "destinations": data["destinations"],
        "timestamps": data["timestamps"],
        "labels": data["labels"],
        "features": features,
        "num_nodes": int(data["num_nodes"][0]),
        "num_edges": int(data["num_edges"][0]),
        "feat_dim": int(data["feat_dim"][0]),
    }


def get_data_splits(data, train_ratio=0.70, val_ratio=0.15):
    """Chronological train/val/test split."""
    n = data["num_edges"]
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    splits = {}
    for split_name, start, end in [("train", 0, train_end),
                                    ("val", train_end, val_end),
                                    ("test", val_end, n)]:
        splits[split_name] = {
            "sources": data["sources"][start:end],
            "destinations": data["destinations"][start:end],
            "timestamps": data["timestamps"][start:end],
            "labels": data["labels"][start:end],
            "features": data["features"][start:end],
        }

    return splits


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datasets", nargs="+", choices=("wikipedia", "mooc"))
    parser.add_argument("--output-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()
    for name in args.datasets:
        data = download_dataset(name, args.output_dir)
        splits = get_data_splits(data)
        print(f"  Train: {len(splits['train']['sources'])} edges")
        print(f"  Val:   {len(splits['val']['sources'])} edges")
        print(f"  Test:  {len(splits['test']['sources'])} edges")
