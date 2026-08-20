"""Load only corpus identities admitted by the tracked resource manifest.

Acquisition and preprocessing are explicit staging operations. Training never
downloads, rebuilds, or silently accepts different bytes when a corpus is
missing.
"""
import hashlib
import os
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(
    os.environ.get("LINK_PREDICTION_DATA_DIR", PROJECT_ROOT / "resources" / "corpora")
).resolve()

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _current_manifest_entries() -> dict[str, dict[str, str]]:
    """Return current dataset entries from the tracked TOML manifest subset."""
    manifest = (PROJECT_ROOT / "resources/manifest.toml").read_text(encoding="utf-8")
    entries: dict[str, dict[str, str]] = {}
    for block in manifest.split("[[dataset]]")[1:]:
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if "=" not in line:
                continue
            key, value = (part.strip() for part in line.split("=", 1))
            if value.startswith('"') and value.endswith('"'):
                fields[key] = value[1:-1]
        state = fields.get("state", "")
        rel = Path(fields.get("path", ""))
        if state.startswith("CURRENT") and rel.parent == Path("corpora"):
            entries[rel.stem] = fields
    return entries


def download_dataset(name: str):
    """Compatibility entry point that now performs a fail-closed local load."""
    return load_dataset(name)


def preprocess_dataset(name: str, raw_path: str):
    """Reject implicit preprocessing on the scientific execution path."""
    raise RuntimeError(
        "Dataset preprocessing is a reviewed staging operation. Use the explicit "
        "builder workflow, verify the raw digest, then update resources/manifest.toml."
    )


def load_dataset(name: str):
    """Load and verify one current preprocessed dataset identity."""
    normalized = name.lower()
    entries = _current_manifest_entries()
    if normalized not in entries:
        raise ValueError(
            f"Dataset {name!r} is not a current identity in resources/manifest.toml; "
            f"choose from {sorted(entries)}."
        )
    entry = entries[normalized]
    path = DATA_DIR / f"{normalized}.npz"
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing {path}. Training does not download or build data implicitly; "
            "follow resources/README.md."
        )
    actual = _sha256(path)
    if actual != entry["sha256"]:
        raise ValueError(
            f"Checksum mismatch for {path}: expected {entry['sha256']}, got {actual}."
        )
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
    for name in ["wikipedia"]:
        data = download_dataset(name)
        splits = get_data_splits(data)
        print(f"  Train: {len(splits['train']['sources'])} edges")
        print(f"  Val:   {len(splits['val']['sources'])} edges")
        print(f"  Test:  {len(splits['test']['sources'])} edges")
