from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_artifact_helpers():
    path = ROOT / "experiments/dataset_builders/_artifacts.py"
    spec = importlib.util.spec_from_file_location("dataset_artifacts", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_source_registry_is_fetch_only_and_fully_pinned() -> None:
    registry = json.loads((ROOT / "resources/source_registry.json").read_text())
    rights = registry["rights_policy"]
    assert rights["upstream_license_grant_identified"] is False
    assert rights["redistribution_by_this_project"] is False
    assert rights["owner_license_review_required_for_redistribution"] is True

    datasets = registry["datasets"]
    assert set(datasets) == {"wikipedia", "mooc", "coedit"}
    for name in ("wikipedia", "mooc"):
        record = datasets[name]
        assert record["url"].startswith("https://snap.stanford.edu/jodie/")
        assert re.fullmatch(r"[0-9a-f]{64}", record["raw_sha256"])
        assert re.fullmatch(r"[0-9a-f]{64}", record["processed_sha256"])
        assert record["raw_bytes"] > 0
    assert re.fullmatch(r"[0-9a-f]{64}", datasets["coedit"]["processed_sha256"])


def test_current_manifest_matches_reproducible_registry() -> None:
    registry = json.loads((ROOT / "resources/source_registry.json").read_text())
    manifest = (ROOT / "resources/manifest.toml").read_text()
    expected = {
        record["dataset_id"]: record["processed_sha256"]
        for record in registry["datasets"].values()
    }
    blocks = {
        match.group(1): block
        for block in manifest.split("[[dataset]]")[1:]
        if (match := re.search(r'^\s*id = "([^"]+)"', block))
    }
    for dataset_id, digest in expected.items():
        block = blocks[dataset_id]
        assert f'sha256 = "{digest}"' in block
        corpus_name = dataset_id.split("-")[2].lower()
        corpus = ROOT / "resources/corpora" / f"{corpus_name}.npz"
        if corpus.exists():
            assert _sha256(corpus) == digest


def test_npz_writer_is_byte_deterministic(tmp_path: Path) -> None:
    helpers = _load_artifact_helpers()
    arrays = {
        "sources": np.array([2, 1], dtype=np.int64),
        "features": np.array([[1.5], [2.5]], dtype=np.float32),
    }
    first = tmp_path / "first.npz"
    second = tmp_path / "second.npz"
    helpers.save_npz_deterministic(first, arrays)
    helpers.save_npz_deterministic(second, arrays)
    assert first.read_bytes() == second.read_bytes()
    with np.load(first, allow_pickle=False) as restored:
        assert np.array_equal(restored["sources"], arrays["sources"])
        assert np.array_equal(restored["features"], arrays["features"])
