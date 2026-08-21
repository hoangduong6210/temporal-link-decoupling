from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

from release_fixture import (
    RELEASE_ID,
    create_release_project,
    create_snapshot_inputs,
    commit,
    sha256,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FREEZE_SCRIPT = PROJECT_ROOT / "scripts/freeze_evidence_release.py"
SNAPSHOT_SCRIPT = PROJECT_ROOT / "scripts/build_paper_snapshot.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # build_paper_snapshot imports the sibling freeze module in direct-script mode.
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def _released_project(tmp_path: Path, *, with_figure: bool = False):
    freeze = _load(FREEZE_SCRIPT, f"freeze_for_snapshot_{id(tmp_path)}")
    root, release_plan = create_release_project(tmp_path, with_figure=with_figure)
    freeze.freeze_evidence_release(root, release_plan, activate=True)
    commit(root, "freeze evidence release")
    return root


def test_snapshot_builds_complete_occurrence_registry_and_checksums(tmp_path: Path) -> None:
    snapshot = _load(SNAPSHOT_SCRIPT, "build_snapshot_success")
    root = _released_project(tmp_path, with_figure=True)
    plan = create_snapshot_inputs(root, include_figure=True)

    manifest = snapshot.build_paper_snapshot(root, plan)

    directory = root / "paper/snapshots/LP-SNAP-TEST-001"
    records = [json.loads(line) for line in (directory / "numeric-provenance.jsonl").read_text().splitlines()]
    keys = {(item["file"], item["line"], item["literal"], item["occurrence"]) for item in records}
    assert ("main.md", 1, "0.8", 1) in keys
    assert ("main.md", 1, "2", 1) in keys
    assert ("figures/figure.png", 0, "0.8", 1) in keys
    assert (directory / "figures/figure.png.numbers.jsonl").is_file()
    assert manifest["evidence_release"] == RELEASE_ID
    checksums = {}
    for line in (directory / "checksums.sha256").read_text().splitlines():
        digest, rel = line.split(maxsplit=1)
        checksums[rel] = digest
    actual = {
        path.relative_to(directory).as_posix(): sha256(path)
        for path in directory.rglob("*")
        if path.is_file() and path.name != "checksums.sha256"
    }
    assert checksums == actual


def test_snapshot_rejects_one_missing_number_and_leaves_no_payload(tmp_path: Path) -> None:
    snapshot = _load(SNAPSHOT_SCRIPT, "build_snapshot_missing_number")
    root = _released_project(tmp_path)
    plan = create_snapshot_inputs(root, omit_structural_annotation=True)

    with pytest.raises(snapshot.common.GateError, match="unregistered paper numeric occurrence"):
        snapshot.build_paper_snapshot(root, plan)

    assert not (root / "paper/snapshots/LP-SNAP-TEST-001").exists()
    assert (root / "paper/CURRENT").read_text().strip() == "UNRELEASED"


def test_snapshot_rejects_literal_that_disagrees_with_selected_scalar(tmp_path: Path) -> None:
    snapshot = _load(SNAPSHOT_SCRIPT, "build_snapshot_value_mismatch")
    root = _released_project(tmp_path)
    plan = create_snapshot_inputs(root, empirical_literal="0.7")

    with pytest.raises(snapshot.common.GateError, match="does not match selected artifact value"):
        snapshot.build_paper_snapshot(root, plan)

    assert not (root / "paper/snapshots/LP-SNAP-TEST-001").exists()


def test_snapshot_rejects_quarantined_working_source(tmp_path: Path) -> None:
    snapshot = _load(SNAPSHOT_SCRIPT, "build_snapshot_quarantine")
    root = _released_project(tmp_path)
    plan = create_snapshot_inputs(root)
    payload = json.loads(plan.read_text())
    working = root / "paper/working/main.md"
    working.parent.mkdir(parents=True, exist_ok=True)
    working.write_text((root / "paper/candidate/main.md").read_text(), encoding="utf-8")
    payload["source_files"][0]["path"] = "paper/working/main.md"
    plan.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    commit(root, "attempt quarantined source")

    with pytest.raises(snapshot.common.GateError, match="quarantined surface"):
        snapshot.build_paper_snapshot(root, plan)

    assert not (root / "paper/snapshots/LP-SNAP-TEST-001").exists()
