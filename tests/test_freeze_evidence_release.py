from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from release_fixture import RELEASE_ID, create_release_project, sha256


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts/freeze_evidence_release.py"


def _module():
    spec = importlib.util.spec_from_file_location("freeze_evidence_release_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_freeze_creates_checksum_closed_non_overwritable_release(tmp_path: Path) -> None:
    freeze = _module()
    root, plan = create_release_project(tmp_path)

    manifest = freeze.freeze_evidence_release(root, plan)

    release = root / f"results/frozen/{RELEASE_ID}"
    assert manifest["state"] == "FROZEN"
    assert manifest["jobs"][0]["coverage"]["task_count"] == 1
    checksums = {}
    for line in (release / "checksums.sha256").read_text().splitlines():
        digest, rel = line.split(maxsplit=1)
        checksums[rel] = digest
    actual = {
        path.relative_to(release).as_posix(): sha256(path)
        for path in release.rglob("*")
        if path.is_file() and path.name != "checksums.sha256"
    }
    assert checksums == actual
    assert (release / "release.json").stat().st_mode & 0o222 == 0
    with pytest.raises(freeze.GateError):
        freeze.freeze_evidence_release(root, plan)


def test_freeze_rejects_incomplete_final_attempt_without_output(tmp_path: Path) -> None:
    freeze = _module()
    root, plan = create_release_project(tmp_path, incomplete_attempt=True)

    with pytest.raises(freeze.GateError, match="no successful final attempt"):
        freeze.freeze_evidence_release(root, plan)

    assert not (root / f"results/frozen/{RELEASE_ID}").exists()
    assert (root / "results/CURRENT").read_text().strip() == "UNRELEASED"


def test_freeze_recomputes_and_rejects_false_aggregate(tmp_path: Path) -> None:
    freeze = _module()
    root, plan = create_release_project(tmp_path, aggregate_mismatch=True)

    with pytest.raises(freeze.GateError, match="mean reconstruction mismatch"):
        freeze.freeze_evidence_release(root, plan)

    assert not (root / f"results/frozen/{RELEASE_ID}").exists()


def test_cli_blocks_current_repository_without_mutating_pointers() -> None:
    freeze = _module()
    current_before = (PROJECT_ROOT / "results/CURRENT").read_text()
    # A minimal intentionally incomplete plan reaches the clean-tree gate first
    # in this migration worktree; either condition must fail before any output.
    with pytest.raises(freeze.GateError):
        freeze.freeze_evidence_release(PROJECT_ROOT, PROJECT_ROOT / "PROJECT.toml")
    assert (PROJECT_ROOT / "results/CURRENT").read_text() == current_before
