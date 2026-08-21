from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
PACKAGE = "temporal_link_decoupling"
SIBLING_PACKAGE = "lifecycle_readout"
PREFIX = "LP"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _front_matter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"missing front matter: {path}"
    end = text.find("\n---\n", 4)
    assert end > 0, f"unterminated front matter: {path}"
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def _manifest_entries() -> list[dict[str, str]]:
    text = (ROOT / "resources/manifest.toml").read_text(encoding="utf-8")
    entries = []
    for block in text.split("[[dataset]]")[1:]:
        entry = dict(re.findall(r'^(\w+)\s*=\s*"([^"]+)"', block, re.MULTILINE))
        entries.append(entry)
    return entries


def test_required_repository_contract() -> None:
    required = [
        "README.md", "LICENSE", "LICENSE-SCOPE.md", "THIRD_PARTY_NOTICES.md",
        "PROJECT.toml", "pyproject.toml", "CITATION.cff",
        "REPRODUCIBILITY.toml",
        "results/CURRENT", "paper/CURRENT", "resources/manifest.toml",
        "wiki/README.md", "wiki/INDEX.md", "wiki/START-HERE.md",
        "wiki/LIMITATIONS.md", "wiki/REPRODUCIBILITY.md",
        "wiki/status/Project-Status.md",
        "wiki/claims/Current-Claim-Language.md",
        "wiki/evidence/Evidence-Ledger.md",
        "wiki/governance/License-and-Assets.md",
        "wiki/governance/Numeric-Evidence-and-Publication-Hygiene.md",
        "evidence/jobs/LP-JOB-LOCAL-20260820-001.toml",
        "evidence/jobs/SCIENTIFIC_JOB_CONTRACT.md",
        "evidence/jobs/checksums.sha256",
        "paper/SNAPSHOT_TEMPLATE.toml", "paper/snapshots/README.md",
        "scripts/audit_scientific_provenance.py",
        "scripts/reconcile_scientific_matrix.py",
        "scripts/freeze_evidence_release.py",
        "scripts/build_paper_snapshot.py",
        "scripts/public_source_identity.py",
        "scripts/verify_public_history.py",
        "evidence/export/COMMIT-EQUIVALENCE.json",
        "evidence/export/PUBLIC-HISTORY-POLICY.toml",
        "slurm/scientific_matrix.sbatch",
        "slurm/reconcile_scientific_matrix.sbatch",
    ]
    assert not [path for path in required if not (ROOT / path).is_file()]
    project = (ROOT / "PROJECT.toml").read_text(encoding="utf-8")
    evidence_release = re.search(r'^evidence_release = "([^"]+)"$', project, re.MULTILINE)
    paper_snapshot = re.search(r'^paper_snapshot = "([^"]+)"$', project, re.MULTILINE)
    assert evidence_release and paper_snapshot
    assert (ROOT / "results/CURRENT").read_text().strip() == evidence_release.group(1)
    assert (ROOT / "paper/CURRENT").read_text().strip() == paper_snapshot.group(1)

    for script in (ROOT / "slurm").glob("*.sbatch"):
        text = script.read_text(encoding="utf-8")
        assert "SLURM_SUBMIT_DIR" in text
        assert 'dirname "${BASH_SOURCE[0]}"' not in text


def test_wiki_front_matter_index_and_links() -> None:
    pages = sorted(WIKI.rglob("*.md"))
    index = (WIKI / "INDEX.md").read_text(encoding="utf-8")
    for page in pages:
        fields = _front_matter(page)
        assert fields.get("title")
        assert fields.get("status")
        assert fields.get("paper_source") in {"true", "false"}
        date_fields = [key for key in ("date", "last_updated") if key in fields]
        assert len(date_fields) == 1
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", fields[date_fields[0]])
        rel = page.relative_to(WIKI).as_posix()
        assert f"({rel})" in index, f"wiki page absent from INDEX: {rel}"

        text = page.read_text(encoding="utf-8")
        for target in re.findall(r"!?\[[^]]*\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            clean = target.split("#", 1)[0]
            resolved = (page.parent / clean).resolve()
            assert resolved.is_relative_to(ROOT)
            assert resolved.exists(), f"broken link {target} in {page}"


def test_wiki_identifier_and_governance_contracts() -> None:
    index = (WIKI / "INDEX.md").read_text(encoding="utf-8")
    identity_sources = [
        *WIKI.rglob("*.md"),
        ROOT / "protocols/link_prediction_v1.toml",
        ROOT / "resources/manifest.toml",
    ]
    identity_text = "\n".join(path.read_text(encoding="utf-8") for path in identity_sources)
    ids = set(re.findall(r"\b(?:LP-(?:RQ|D|P|E|C|H)-[A-Z0-9-]+|DEC-\d{4})\b", identity_text))
    assert ids
    assert not [identifier for identifier in sorted(ids) if f"`{identifier}`" not in index]
    paper_current = (ROOT / "paper/CURRENT").read_text(encoding="utf-8").strip()
    if paper_current == "UNRELEASED":
        assert "None. `paper/CURRENT`" in index
    else:
        assert f"`{paper_current}`" in index

    claims = (WIKI / "claims/Current-Claim-Language.md").read_text(encoding="utf-8")
    for field in (
        "Exact permitted statement", "Lifecycle status", "Scope and population",
        "Dataset and fidelity", "Metric and uncertainty unit", "Evidence IDs",
        "Execution job",
        "Required qualifiers", "Known limitations", "Paper eligibility",
        "Last review date",
    ):
        assert claims.count(f"**{field}:**") == 3
    assert "## Validated artifacts that are not admitted claims" in claims
    assert "## Blocked or proposed claims" in claims
    assert "## Rejected positive claims" in claims

    evidence = (WIKI / "evidence/Evidence-Ledger.md").read_text(encoding="utf-8")
    for field in (
        "Scientific purpose", "Lifecycle", "Source commit",
        "Protocol, configuration, and data hashes", "Execution identity",
        "Artifact path or release URI", "Artifact checksum", "Coverage and failures",
        "Acceptance-gate outcome", "Supported claim IDs", "Rejected claim IDs",
        "Scientific-use boundary",
    ):
        assert evidence.count(f"**{field}:**") == 7

    decision = (WIKI / "decisions/0001-separate-link-prediction-and-lifecycle-readout.md").read_text()
    for heading in (
        "# DEC-0001", "## Context", "## Options considered", "## Decision",
        "## Scientific consequences", "## Evidence and affected IDs",
        "## Supersedes / superseded by",
    ):
        assert heading in decision


def test_public_export_excludes_internal_artifacts() -> None:
    excluded = [
        "AGENTS.md", "docs/MIGRATION.md", "evidence/audits", "figures",
        "paper/figs", "paper/working", "results/audit", "results/historical",
        "resources/corpora/pre_idfix",
        "paper/snapshots/LP-SNAP-2026-CONFERENCE-001",
        "paper/snapshots/LP-SNAP-2026-CONFERENCE-002",
    ]
    assert not [path for path in excluded if (ROOT / path).exists()]
    reachable = subprocess.run(
        ["git", "rev-list", "--objects", "HEAD"], cwd=ROOT,
        text=True, capture_output=True, check=True,
    ).stdout.splitlines()
    reachable_paths = [line.split(" ", 1)[1] for line in reachable if " " in line]
    assert not [path for path in excluded if any(item.startswith(path) for item in reachable_paths)]
    snapshot_root_files = {
        path.name for path in (ROOT / "paper/snapshots").iterdir() if path.is_file()
    }
    assert snapshot_root_files == {"README.md"}


def test_public_history_allows_only_the_named_overleaf_zip() -> None:
    verifier = (ROOT / "scripts/verify_public_history.py").read_text(encoding="utf-8")
    assert "candidate/link-prediction-overleaf\\.zip" in verifier
    assert "link-prediction-overleaf\\.zip" in verifier
    assert 'BANNED_SUFFIX = {".docx", ".zip", ".pyc", ".log", ".out"}' in verifier
    assert "ALLOWED_OVERLEAF_ZIP.fullmatch(path)" in verifier


def test_license_metadata_and_asset_boundaries() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert license_text.startswith("BSD 3-Clause License\n")
    assert "Temporal Link Prediction by Decoupling contributors" in license_text
    assert "Neither the name of the copyright holder" in license_text
    assert '\"AS IS\"' in license_text

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    project = (ROOT / "PROJECT.toml").read_text(encoding="utf-8")
    reproducibility = (ROOT / "REPRODUCIBILITY.toml").read_text(encoding="utf-8")
    assert 'license = "BSD-3-Clause"' in pyproject
    assert "license: BSD-3-Clause" in citation
    assert 'software_license = "BSD-3-Clause"' in project
    assert 'public_source_release_state = "BSD_3_CLAUSE_LICENSED_SOURCE"' in reproducibility

    scope = (ROOT / "LICENSE-SCOPE.md").read_text(encoding="utf-8")
    notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    governance = (WIKI / "governance/License-and-Assets.md").read_text(encoding="utf-8")
    for text in (scope, notices, governance):
        assert "dataset" in text.lower()
        assert "third-party" in text.lower()
    assert "manuscript source" in scope
    assert "submission bundles" in scope

    registry = json.loads((ROOT / "resources/source_registry.json").read_text())
    rights = registry["rights_policy"]
    assert rights["upstream_license_grant_identified"] is False
    assert rights["redistribution_by_this_project"] is False

    policy = (ROOT / "evidence/export/PUBLIC-HISTORY-POLICY.toml").read_text()
    assert "license_added = false" in policy
    mapping = json.loads(
        (ROOT / "evidence/export/COMMIT-EQUIVALENCE.json").read_text()
    )
    assert mapping["allowed_public_overlays"] == [
        "wiki/INDEX.md",
        "wiki/governance/License-and-Assets.md",
    ]


def test_license_identifier_is_structural_but_scientific_numbers_remain_visible() -> None:
    spec = importlib.util.spec_from_file_location(
        "audit_scientific_provenance",
        ROOT / "scripts/audit_scientific_provenance.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    mask = module._mask_structural_wiki_tokens
    assert "3" not in mask("Software license: BSD-3-Clause")
    assert "81%" in mask("BSD-3-Clause does not evidence a value of 81%")


def test_audit_toml_loader_preserves_build_artifact_array_tables() -> None:
    spec = importlib.util.spec_from_file_location(
        "audit_scientific_provenance_array_tables",
        ROOT / "scripts/audit_scientific_provenance.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    record = module._load_toml(
        ROOT / "evidence/jobs/LP-JOB-LOCAL-20260821-PAPER-BUILD-005.toml"
    )
    artifacts = record["additional_artifacts"]
    assert isinstance(artifacts, list)
    assert {item["role"] for item in artifacts} == {
        "self-contained-overleaf-package",
        "monochrome-vector-result-figure",
        "monochrome-vector-protocol-figure",
        "lppl-overleaf-class",
    }


def test_every_public_evidence_job_reference_resolves() -> None:
    evidence = (WIKI / "evidence/Evidence-Ledger.md").read_text(encoding="utf-8")
    registry = (ROOT / "evidence/jobs/checksums.sha256").read_text(encoding="utf-8")
    for job_id in set(re.findall(r"\bLP-JOB-[A-Z0-9-]+\b", evidence)):
        rel = f"evidence/jobs/{job_id}.toml"
        record = ROOT / rel
        assert record.is_file(), f"evidence ledger references missing job: {job_id}"
        assert rel in registry, f"evidence ledger job is not checksum-registered: {job_id}"


def test_claim_evidence_namespace_resolves() -> None:
    claims = (WIKI / "claims/Current-Claim-Language.md").read_text()
    evidence = (WIKI / "evidence/Evidence-Ledger.md").read_text()
    assert not re.search(r"\bLCR-[A-Z]", claims + evidence)
    for evidence_id in set(re.findall(rf"{PREFIX}-E-[A-Z0-9-]+", claims)):
        assert evidence_id in evidence


def test_source_boundary_syntax_and_imports() -> None:
    for path in ROOT.rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    src_text = "\n".join(
        path.read_text(encoding="utf-8") for path in (ROOT / "src").rglob("*.py")
    )
    assert SIBLING_PACKAGE not in src_text
    assert "sys.path.insert" not in src_text
    assert "sys.path.append" not in src_text
    for path in ROOT.rglob("*"):
        if path.is_symlink():
            assert path.resolve().is_relative_to(ROOT)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    code = (
        f"import {PACKAGE}, {PACKAGE}.datasets, {PACKAGE}.training; "
        f"from {PACKAGE}.modeling.v33 import sr_gnn_v3_3; "
        f"from {PACKAGE}.modeling.baseline import baselines; "
        f"print({PACKAGE}.__file__)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd="/tmp", env=env,
        text=True, capture_output=True, check=True,
    )
    assert Path(result.stdout.strip()).resolve().is_relative_to(ROOT)


def test_json_and_artifact_hygiene() -> None:
    for path in ROOT.rglob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    forbidden = {"__pycache__", ".claude", ".pytest_cache"}
    bad_suffixes = {".pyc", ".aux", ".out", ".log"}
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "__pycache__/" in ignore and "*.py[cod]" in ignore and ".pytest_cache/" in ignore
    assert "results/frozen/*" not in ignore
    assert "paper/snapshots/*" not in ignore
    for path in ROOT.rglob("*"):
        # Python/pytest create caches while this suite is running. Their exclusion
        # is a VCS contract; filesystem presence during a test is not a violation.
        if (
            forbidden.intersection(path.parts)
            or path.suffix in {".pyc"}
            or path.is_relative_to(ROOT / "results/audit")
        ):
            continue
        assert path.suffix not in bad_suffixes


def test_public_files_contain_no_private_paths() -> None:
    excluded = [
        ROOT / "results/historical",
        ROOT / "results/audit",
        ROOT / "paper/working",
    ]
    suffixes = {".py", ".sh", ".sbatch", ".md", ".toml", ".yaml", ".yml", ".json"}
    pattern = re.compile(r"/(?:users|home|private|scratch)/")
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if any(path.is_relative_to(base) for base in excluded):
            continue
        assert not pattern.search(path.read_text(encoding="utf-8", errors="ignore")), path


def test_runtime_and_public_checksum_manifests() -> None:
    for manifest_path in [
        ROOT / "configs/shared-runtime.sha256",
        ROOT / "resources/checksums.sha256",
        ROOT / "evidence/jobs/checksums.sha256",
    ]:
        for line in manifest_path.read_text().splitlines():
            expected, rel = line.split(maxsplit=1)
            artifact = ROOT / rel
            if not artifact.exists() and artifact.is_relative_to(ROOT / "resources/corpora"):
                continue
            assert artifact.exists()
            assert _sha256(artifact) == expected


def test_numeric_evidence_jobs_and_publication_boundary() -> None:
    claims = (WIKI / "claims/Current-Claim-Language.md").read_text(encoding="utf-8")
    assert claims.count("**Execution job:**") == 3

    job_ids = set(re.findall(r"\bLP-JOB-[A-Z0-9-]+\b", claims))
    assert job_ids
    checksums = (ROOT / "evidence/jobs/checksums.sha256").read_text(encoding="utf-8")
    for job_id in job_ids:
        record = ROOT / "evidence" / "jobs" / f"{job_id}.toml"
        assert record.is_file(), job_id
        text = record.read_text(encoding="utf-8")
        assert f'job_id = "{job_id}"' in text
        assert "source_state" in text and "command" in text and "exit_code" in text
        assert re.search(r"^scientific = (?:true|false)$", text, re.MULTILINE)
        if "scientific = true" in text:
            assert 'execution_kind = "scheduler"' in text
            assert "supported_scientific_claim_ids" in text
            assert "final_accounting_sha256" in text
        assert record.relative_to(ROOT).as_posix() in checksums

    quantitative = re.compile(
        r"(?<![A-Za-z0-9_-])(?:\d+\.\d+|\d+(?:\.\d+)?\s*(?:%|pp)|±\s*\d)"
    )
    violations = []
    for page in WIKI.rglob("*.md"):
        if page == WIKI / "claims/Current-Claim-Language.md":
            continue
        for lineno, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
            prose = re.sub(r"`[^`]+`", "", line)
            if quantitative.search(prose):
                violations.append(f"{page.relative_to(ROOT)}:{lineno}:{line}")
    assert not violations

    policy = (ROOT / "evidence/export/PUBLIC-HISTORY-POLICY.toml").read_text(encoding="utf-8")
    for banned in ("AGENTS.md", "paper/working/", "results/historical/",
                   "paper/figs/", "figures/", "evidence/audits/"):
        assert banned in policy


def test_active_surface_has_no_ai_or_internal_orphan_markers() -> None:
    patterns = re.compile(
        r"(?i)claude|grok|chatgpt|codex|openai|anthropic|gemini|"
        r"PM directive|TESTBENCH|team report|NHIỆM VỤ|flagged to PM|"
        r"reported to PM|human directive|AI[- ]tell|humanization|de-AI|"
        r"\bPM(?:'s)?\b|reviewer\s*(?:#|Q|§)|panel asked|rebuttal|"
        r"job\s*[#:=_-]?\s*\d{5,}"
    )
    violations = []
    for base in (ROOT / "src", ROOT / "experiments", ROOT / "wiki"):
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".md", ".toml", ".json"}:
                for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if patterns.search(line):
                        violations.append(f"{path.relative_to(ROOT)}:{lineno}:{line}")
    assert not violations


def test_provenance_auditor_and_release_readiness_semantics() -> None:
    command = [sys.executable, "scripts/audit_scientific_provenance.py"]
    canonical = subprocess.run(
        [*command, "--check-canonical"], cwd=ROOT,
        text=True, capture_output=True, check=False,
    )
    assert canonical.returncode == 0, canonical.stdout + canonical.stderr
    report = json.loads(canonical.stdout)
    assert report["canonical_status"] == "PASS"
    paper_current = (ROOT / "paper/CURRENT").read_text(encoding="utf-8").strip()
    expected_snapshot_state = "NOT_PRESENT" if paper_current == "UNRELEASED" else "AUDITED"
    assert report["paper_snapshot"]["state"] == expected_snapshot_state
    reproducible = (
        'status = "REPRODUCIBLE"'
        in (ROOT / "REPRODUCIBILITY.toml").read_text(encoding="utf-8")
    )
    assert report["release_readiness"] == ("READY" if reproducible else "BLOCKED")
    assert report["active_internal_markers"] == []
    assert report["wiki"]["unclassified_numeric_tokens_outside_claim_registry"] == []
    assert report["wiki"]["unclassified_number_words_outside_claim_registry"] == []
    assert report["quarantine_diagnostics"]["historical_json_files"] == 0
    assert report["quarantine_diagnostics"][
        "historical_json_with_normalized_execution_identity"
    ] == 0
    assert report["quarantine_diagnostics"][
        "legacy_binary_has_visible_quarantine_banner"
    ] == {}

    release = subprocess.run(
        [*command, "--require-release"], cwd=ROOT,
        text=True, capture_output=True, check=False,
    )
    assert release.returncode == (0 if reproducible else 2)


def test_reproducibility_manifest_is_honest_and_hash_closed() -> None:
    text = (ROOT / "REPRODUCIBILITY.toml").read_text(encoding="utf-8")
    assert re.search(r'^status = "(?:EVIDENCE_FROZEN|REPRODUCIBLE)"$', text, re.MULTILINE)
    assert 'source_state = "CLEAN_SCIENTIFIC_EXECUTION"' in text
    assert re.search(r'^source_commit = "[0-9a-f]{40}"$', text, re.MULTILINE)
    assert (
        'clean_clone_corpus_state = '
        '"VERIFIED_NETWORK_ACQUISITION_AND_DETERMINISTIC_REBUILD"'
    ) in text
    assert 'task_seed_attempt_failure_coverage = "COMPLETE_EXACT_PROTOCOL_MATRIX"' in text
    assert 'aggregation_reconstruction = "VERIFIED_FROM_SELECTED_PER_SEED_ROWS_WITH_SAMPLE_STD"' in text
    for hash_key, path_key in (
        ("protocol_sha256", "protocol_path"),
        ("runtime_manifest_sha256", "runtime_manifest"),
        ("data_manifest_sha256", "data_manifest"),
        ("data_checksums_sha256", "data_checksums"),
    ):
        expected = re.search(rf'^{hash_key} = "([0-9a-f]{{64}})"$', text, re.MULTILINE)
        rel = re.search(rf'^{path_key} = "([^"]+)"$', text, re.MULTILINE)
        assert expected and rel
        assert _sha256(ROOT / rel.group(1)) == expected.group(1)


def test_dataset_loading_is_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_path = ROOT / "src/temporal_link_decoupling/datasets.py"
    spec = importlib.util.spec_from_file_location("lp_datasets_under_test", source_path)
    assert spec and spec.loader
    datasets = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(datasets)

    monkeypatch.setattr(datasets, "DATA_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="does not download or build"):
        datasets.load_dataset("wikipedia")

    np.savez(
        tmp_path / "wikipedia.npz",
        sources=np.array([0]), destinations=np.array([1]), timestamps=np.array([0.0]),
        labels=np.array([1]), features=np.zeros((1, 1)), num_nodes=np.array([2]),
        num_edges=np.array([1]), feat_dim=np.array([1]),
    )
    with pytest.raises(ValueError, match="Checksum mismatch"):
        datasets.load_dataset("wikipedia")
    with pytest.raises(RuntimeError, match="reviewed staging operation"):
        datasets.preprocess_dataset("wikipedia", "unreviewed.csv")

    source = source_path.read_text()
    assert "urlretrieve" not in source
    assert "allow_pickle=False" in source


def test_dataset_manifest_schema_and_idfix_contract() -> None:
    entries = _manifest_entries()
    assert len({entry["id"] for entry in entries}) == len(entries)
    by_id = {entry["id"]: entry for entry in entries}
    data_root = Path(os.environ.get(
        "LINK_PREDICTION_DATA_DIR", ROOT / "resources" / "corpora"
    ))
    current_entries = [
        entry for entry in entries if entry.get("state", "").startswith("CURRENT")
    ]
    paths = [
        data_root / Path(entry["path"]).relative_to("corpora")
        for entry in current_entries
    ]
    checksum_entries = {}
    for line in (ROOT / "resources/checksums.sha256").read_text().splitlines():
        expected, rel = line.split(maxsplit=1)
        checksum_entries[rel] = expected
    for entry in entries:
        assert checksum_entries[f'resources/{entry["path"]}'] == entry["sha256"]
    if not any(path.exists() for path in paths) and "LINK_PREDICTION_DATA_DIR" not in os.environ:
        import pytest
        pytest.skip("optional local corpora are absent; identities remain in manifest.toml")
    assert all(path.exists() for path in paths), "configured corpus set is incomplete"
    for entry in current_entries:
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
        path = data_root / Path(entry["path"]).relative_to("corpora")
        assert path.is_file()
        assert _sha256(path) == entry["sha256"]
        with np.load(path, allow_pickle=False) as data:
            required = {"sources", "destinations", "timestamps", "labels", "features",
                        "num_nodes", "num_edges", "feat_dim"}
            assert required.issubset(data.files)
            n = int(data["num_edges"][0]); nodes = int(data["num_nodes"][0])
            feat_dim = int(data["feat_dim"][0])
            assert all(len(data[key]) == n for key in ("sources", "destinations", "timestamps", "labels"))
            assert data["features"].shape == (n, feat_dim)
            assert data["sources"].min() >= 0 and data["destinations"].min() >= 0
            assert data["sources"].max() < nodes and data["destinations"].max() < nodes
            assert np.all(np.diff(data["timestamps"]) >= 0)
            if "WIKIPEDIA" in entry["id"] or "MOOC" in entry["id"]:
                assert entry["topology"] == "disjoint-bipartite"
                assert np.intersect1d(data["sources"], data["destinations"]).size == 0
            if entry["id"] == "LP-D-COEDIT-002":
                assert entry["topology"] == "homogeneous-shared-node-space"
                assert np.intersect1d(data["sources"], data["destinations"]).size > 0

    assert by_id["LP-D-WIKIPEDIA-002"]["sha256"] != by_id["LP-D-WIKIPEDIA-001"]["sha256"]
    assert by_id["LP-D-MOOC-002"]["sha256"] != by_id["LP-D-MOOC-001"]["sha256"]
