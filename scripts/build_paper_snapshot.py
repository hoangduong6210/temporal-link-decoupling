#!/usr/bin/env python3
"""Build an immutable paper snapshot from one frozen evidence release.

The builder copies only explicitly allowlisted, committed manuscript sources and
checksum-locked release figures.  It does not classify numbers heuristically.
Instead, a reviewed annotation JSONL must classify every occurrence found by the
same ``NUMBER_TOKEN`` expression used by the canonical auditor.  Missing, stale,
or unsupported records stop the build before a snapshot directory or pointer is
created.

Typical usage::

    python scripts/build_paper_snapshot.py \
      --plan paper-plans/LP-SNAP-2026-001.json --activate
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Iterable, Mapping, Sequence

try:  # Works both as ``python scripts/...`` and as an imported test module.
    from scripts import freeze_evidence_release as common
    from scripts import numeric_evidence
    from scripts import public_source_identity
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import freeze_evidence_release as common  # type: ignore[no-redef]
    import numeric_evidence  # type: ignore[no-redef]
    import public_source_identity  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ID = re.compile(r"LP-SNAP-[A-Z0-9-]+")
NUMBER_TOKEN = numeric_evidence.NUMBER_TOKEN
INTERNAL_MARKER = re.compile(
    r"\b(?:claude|grok|chatgpt|codex|openai|anthropic|gemini)\b|"
    r"(?<!\\)\bPM(?:'s)?\b|reviewer\s*(?:#|Q|§)|panel asked|rebuttal|"
    r"humanization|de-AI|AI[- ]tell|flagged to PM|reported to PM",
    re.IGNORECASE,
)
ALLOWED_STRUCTURAL_EXEMPTIONS = {
    "bibliographic-locator",
    "date",
    "equation-label",
    "figure-label",
    "identifier",
    "ordered-list-label",
    "page-layout",
    "section-label",
    "software-version",
    "table-label",
}
RESERVED_SNAPSHOT_FILES = {
    "snapshot.toml",
    "results.lock.yaml",
    "numeric-provenance.jsonl",
    "checksums.sha256",
    "snapshot-plan.json",
}
BANNED_SOURCE_ROOTS = (
    Path("paper/working"),
    Path("paper/figs"),
    Path("figures/generated"),
    Path("results/audit"),
    Path("results/historical"),
)


def _safe_target(raw: Any, label: str) -> str:
    if not isinstance(raw, str) or not raw:
        raise common.GateError(f"{label} target must be a non-empty string")
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts or path.as_posix().startswith("/"):
        raise common.GateError(f"{label} target must be snapshot-relative: {raw}")
    normalized = path.as_posix()
    if normalized in RESERVED_SNAPSHOT_FILES or not path.name:
        raise common.GateError(f"{label} target is reserved or invalid: {raw}")
    return normalized


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _source_entry(
    root: Path,
    value: Any,
    *,
    label: str,
    banned: bool,
) -> dict[str, Any]:
    entry = common._require_mapping(value, label)
    common._required(entry, ("path", "target"), label)
    rel, path = common._safe_file(root, entry["path"], label)
    if banned and any(Path(rel).is_relative_to(prefix) for prefix in BANNED_SOURCE_ROOTS):
        raise common.GateError(f"{label} imports from a quarantined surface: {rel}")
    return {"path": rel, "source": path, "target": _safe_target(entry["target"], label)}


def _project_pointer(root: Path, key: str) -> str:
    project = common._load_toml(root / "PROJECT.toml")
    pointers = common._require_mapping(project.get("pointers"), "PROJECT.toml pointers")
    value = pointers.get(key)
    if not isinstance(value, str) or not value:
        raise common.GateError(f"PROJECT.toml has no {key} pointer")
    return value


def _verify_frozen_release(root: Path, release_id: Any) -> dict[str, Any]:
    if not isinstance(release_id, str) or common.RELEASE_ID.fullmatch(release_id) is None:
        raise common.GateError("evidence_release must match LP-REL-[A-Z0-9-]+")
    if (root / "results/CURRENT").read_text(encoding="utf-8").strip() != release_id:
        raise common.GateError("evidence release is not results/CURRENT")
    if _project_pointer(root, "evidence_release") != release_id:
        raise common.GateError("PROJECT.toml evidence pointer disagrees with results/CURRENT")
    reproducibility = common._load_toml(root / "REPRODUCIBILITY.toml")
    if reproducibility.get("status") not in {"EVIDENCE_FROZEN", "REPRODUCIBLE"}:
        raise common.GateError(
            "REPRODUCIBILITY.toml has not reached evidence-frozen state"
        )
    if reproducibility.get("evidence_release") != release_id:
        raise common.GateError("REPRODUCIBILITY.toml does not bind the evidence release")
    release = (root / "results/frozen" / release_id).resolve()
    frozen_root = (root / "results/frozen").resolve()
    if not _is_under(release, frozen_root) or not release.is_dir() or release.is_symlink():
        raise common.GateError(f"frozen evidence release is missing: {release_id}")
    common._verify_release_directory(release)
    manifest = common._require_mapping(
        common._load_json(release / "release.json"), "frozen release manifest"
    )
    if manifest.get("state") != "FROZEN" or manifest.get("release_id") != release_id:
        raise common.GateError("frozen release manifest identity/state mismatch")
    return manifest


def _git_blob(root: Path, commit: str, path: Path) -> bytes:
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
        return public_source_identity.git_blob(root, commit, rel)
    except (ValueError, public_source_identity.SourceIdentityError) as exc:
        raise common.GateError(f"source is not present at {commit}: {path}: {exc}") from exc


def _verify_source_at_commit(root: Path, commit: str, path: Path) -> None:
    if _git_blob(root, commit, path) != path.read_bytes():
        raise common.GateError(f"source bytes differ from declared commit: {path.relative_to(root)}")


def _verify_wiki_commit(root: Path, wiki_commit: str) -> None:
    if not public_source_identity.tree_matches_head(root, wiki_commit, "wiki"):
        raise common.GateError("current canonical wiki differs from declared wiki_commit")


def _verify_build_job(root: Path, job_id: Any, source_commit: str) -> dict[str, Any]:
    if not isinstance(job_id, str) or common.JOB_ID.fullmatch(job_id) is None:
        raise common.GateError("paper_build_job must match LP-JOB-[A-Z0-9-]+")
    rel = f"evidence/jobs/{job_id}.toml"
    _, _, record = common._registered_job(root, rel)
    common._required(
        record,
        ("job_id", "source_commit", "source_state", "command", "exit_code", "outcome"),
        f"paper build job {job_id}",
    )
    if record["job_id"] != job_id:
        raise common.GateError(f"paper build job record identity mismatch: {job_id}")
    if record["source_commit"] != source_commit or record["source_state"] != "CLEAN":
        raise common.GateError(f"paper build job does not bind the clean source commit: {job_id}")
    if record["exit_code"] != 0 or record["outcome"] != "COMPLETED":
        raise common.GateError(f"paper build job did not complete: {job_id}")
    if not isinstance(record["command"], str) or not record["command"].strip():
        raise common.GateError(f"paper build job command is absent: {job_id}")
    return record


def _verify_rendered_outputs(
    root: Path,
    rendered: Sequence[Mapping[str, Any]],
    build_record: Mapping[str, Any],
) -> None:
    declared: set[tuple[str, str]] = set()
    pointer = build_record.get("result_pointer")
    digest = build_record.get("result_sha256")
    if isinstance(pointer, str) and isinstance(digest, str):
        declared.add((pointer, digest))
    additional = build_record.get("additional_artifacts", [])
    if not isinstance(additional, list):
        raise common.GateError("paper build job additional_artifacts must be an array")
    for index, raw in enumerate(additional):
        item = common._require_mapping(raw, f"paper build additional_artifacts[{index}]")
        if isinstance(item.get("path"), str) and isinstance(item.get("sha256"), str):
            declared.add((item["path"], item["sha256"]))
    for item in rendered:
        pair = (str(item["path"]), common._sha256(Path(item["source"])))
        if pair not in declared:
            raise common.GateError(
                f"paper build job does not checksum-bind rendered output: {item['path']}"
            )


def _numeric_occurrences(path: Path, target: str) -> list[tuple[str, int, str, int]]:
    occurrences: list[tuple[str, int, str, int]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise common.GateError(f"paper source is not UTF-8 text: {path}: {exc}") from exc
    for lineno, line in enumerate(lines, 1):
        if INTERNAL_MARKER.search(line):
            raise common.GateError(f"internal/AI workflow marker in paper source: {target}:{lineno}")
        try:
            numeric_evidence.reject_ambiguous_numeric_text(line, f"{target}:{lineno}")
        except numeric_evidence.NumericEvidenceError as exc:
            raise common.GateError(str(exc)) from exc
        seen: dict[str, int] = {}
        for match in NUMBER_TOKEN.finditer(line):
            literal = match.group(0)
            seen[literal] = seen.get(literal, 0) + 1
            occurrences.append((target, lineno, literal, seen[literal]))
    return occurrences


def _load_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(
                line,
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(f"non-finite constant {value}")
                ),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise common.GateError(f"invalid {label} JSONL at line {lineno}: {exc}") from exc
        records.append(common._require_mapping(item, f"{label}:{lineno}"))
    return records


def _record_key(item: Mapping[str, Any], label: str) -> tuple[str, int, str, int]:
    common._required(item, ("file", "line", "literal", "occurrence", "kind"), label)
    if not isinstance(item["file"], str) or not isinstance(item["literal"], str):
        raise common.GateError(f"{label} file/literal must be strings")
    if not isinstance(item["line"], int) or item["line"] < 0:
        raise common.GateError(f"{label} line must be a nonnegative integer")
    if not isinstance(item["occurrence"], int) or item["occurrence"] < 1:
        raise common.GateError(f"{label} occurrence must be a positive integer")
    return (item["file"], item["line"], item["literal"], item["occurrence"])


def _release_jobs(
    root: Path, release_dir: Path, release_manifest: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    jobs: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(common._require_list(release_manifest.get("jobs"), "release jobs")):
        item = common._require_mapping(raw, f"release job[{index}]")
        common._required(
            item,
            ("job_id", "record", "supported_evidence_ids", "supported_scientific_claim_ids"),
            f"release job[{index}]",
        )
        job_id = item["job_id"]
        if not isinstance(job_id, str) or common.JOB_ID.fullmatch(job_id) is None or job_id in jobs:
            raise common.GateError(f"invalid/duplicate job in evidence release: {job_id}")
        frozen_record = (release_dir / str(item["record"])).resolve()
        if not _is_under(frozen_record, release_dir) or not frozen_record.is_file():
            raise common.GateError(f"frozen job record is missing: {job_id}")
        _, current_record_path, current_record = common._registered_job(
            root, f"evidence/jobs/{job_id}.toml"
        )
        if common._sha256(frozen_record) != common._sha256(current_record_path):
            raise common.GateError(f"current/frozen scientific job records differ: {job_id}")
        if current_record.get("scientific") is not True:
            raise common.GateError(f"release contains a non-scientific job: {job_id}")
        jobs[job_id] = {
            "manifest": item,
            "record": current_record,
        }
    if not jobs:
        raise common.GateError("evidence release contains no scientific jobs")
    return jobs


def _claim_section(text: str, claim_id: str) -> str:
    match = re.search(rf"^### {re.escape(claim_id)}\s*$", text, re.MULTILINE)
    if match is None:
        raise common.GateError(f"numeric record references unknown claim: {claim_id}")
    next_match = re.search(r"^### LP-C-[A-Z0-9-]+\s*$", text[match.end():], re.MULTILINE)
    end = match.end() + next_match.start() if next_match else len(text)
    return text[match.start():end]


def _validate_numeric_record(
    item: dict[str, Any],
    *,
    key: tuple[str, int, str, int],
    release_dir: Path,
    release_checksums: Mapping[str, str],
    release_manifest: Mapping[str, Any],
    release_jobs: Mapping[str, Mapping[str, Any]],
    claims_text: str,
    evidence_text: str,
    figure: bool = False,
) -> dict[str, str]:
    kind = item.get("kind")
    if kind in {"empirical", "protocol", "derived"}:
        common._required(
            item,
            ("claim_id", "evidence_id", "job_id", "artifact_path", "artifact_sha256", "artifact_selector"),
            f"numeric record {key}",
        )
        claim_id = item["claim_id"]
        evidence_id = item["evidence_id"]
        job_id = item["job_id"]
        if not isinstance(claim_id, str) or common.CLAIM_ID.fullmatch(claim_id) is None:
            raise common.GateError(f"invalid claim ID in numeric record: {key}")
        if not isinstance(evidence_id, str) or common.EVIDENCE_ID.fullmatch(evidence_id) is None:
            raise common.GateError(f"invalid evidence ID in numeric record: {key}")
        if not isinstance(job_id, str) or common.JOB_ID.fullmatch(job_id) is None:
            raise common.GateError(f"invalid job ID in numeric record: {key}")
        if claim_id not in set(release_manifest.get("claim_ids", [])):
            raise common.GateError(f"numeric claim is absent from evidence release: {claim_id}")
        if evidence_id not in set(release_manifest.get("evidence_ids", [])):
            raise common.GateError(f"numeric evidence is absent from evidence release: {evidence_id}")
        job = release_jobs.get(job_id)
        if job is None:
            raise common.GateError(f"numeric job is absent from evidence release: {job_id}")
        manifest_job = common._require_mapping(job["manifest"], f"release job {job_id}")
        record = common._require_mapping(job["record"], f"job record {job_id}")
        if evidence_id not in set(manifest_job["supported_evidence_ids"]):
            raise common.GateError(f"job does not support numeric evidence: {key}")
        if claim_id not in set(manifest_job["supported_scientific_claim_ids"]):
            raise common.GateError(f"job does not support numeric claim: {key}")
        if evidence_id not in set(record.get("supported_evidence_ids", [])) or claim_id not in set(
            record.get("supported_scientific_claim_ids", [])
        ):
            raise common.GateError(f"registered job support differs from release: {key}")
        section = _claim_section(claims_text, claim_id)
        if "**Paper eligibility:** true" not in section or "**Lifecycle status:** BLOCKED" in section:
            raise common.GateError(f"numeric claim is not paper-eligible: {claim_id}")
        if f"## {evidence_id}" not in evidence_text:
            raise common.GateError(f"numeric record references unknown evidence: {evidence_id}")
        artifact_path = item["artifact_path"]
        if not isinstance(artifact_path, str) or artifact_path not in release_checksums:
            raise common.GateError(f"numeric artifact is absent from frozen release: {key}")
        artifact = (release_dir / artifact_path).resolve()
        if not _is_under(artifact, release_dir) or not artifact.is_file():
            raise common.GateError(f"numeric artifact path escapes/missing: {key}")
        if item["artifact_sha256"] != release_checksums[artifact_path] or common._sha256(artifact) != item["artifact_sha256"]:
            raise common.GateError(f"numeric artifact checksum mismatch: {key}")
        if not isinstance(item["artifact_selector"], str) or not item["artifact_selector"].strip():
            raise common.GateError(f"numeric artifact selector is absent: {key}")
        owned_paths = {str(manifest_job["result"])}
        owned_paths.update(
            str(entry.get("path"))
            for entry in common._require_list(
                release_manifest.get("artifacts", []), "release artifacts"
            )
            if isinstance(entry, dict) and entry.get("job_id") == job_id
        )
        if artifact_path not in owned_paths:
            raise common.GateError(f"numeric artifact is not owned by its declared job: {key}")
        if any(field in item for field in numeric_evidence.COMPUTED_FIELDS):
            raise common.GateError(f"numeric annotation contains builder-owned fields: {key}")
        try:
            verified = numeric_evidence.verify_numeric_assertion(
                artifact=artifact,
                selector=item["artifact_selector"],
                literal=str(item["literal"]),
                assertion=item.get("value_assertion"),
            )
        except numeric_evidence.NumericEvidenceError as exc:
            raise common.GateError(f"numeric value assertion failed {key}: {exc}") from exc
    elif kind == "structural":
        if item.get("exemption") not in ALLOWED_STRUCTURAL_EXEMPTIONS:
            raise common.GateError(f"invalid structural exemption: {key}")
        forbidden = {
            "claim_id", "evidence_id", "job_id", "artifact_path",
            "artifact_sha256", "artifact_selector", "value_assertion",
        }
        if forbidden.intersection(item):
            raise common.GateError(f"structural numeric record carries scientific provenance: {key}")
        verified = {}
    else:
        raise common.GateError(f"invalid numeric kind {kind!r}: {key}")
    if figure:
        if item.get("figure_sidecar") is not True:
            raise common.GateError(f"figure record lacks figure_sidecar=true: {key}")
        plot_job = item.get("plot_job_id")
        if not isinstance(plot_job, str) or plot_job not in release_jobs:
            raise common.GateError(f"figure record lacks a frozen plot job: {key}")
        if kind != "structural" and item.get("job_id") != plot_job:
            raise common.GateError(f"figure plot_job_id/job_id mismatch: {key}")
    return verified


def _write_jsonl(path: Path, records: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for item in records:
            stream.write(json.dumps(item, sort_keys=True, allow_nan=False, separators=(",", ":")))
            stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _toml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _write_snapshot_toml(path: Path, manifest: Mapping[str, Any]) -> None:
    scalar_keys = (
        "state", "snapshot_id", "venue", "submission_state", "source_commit",
        "wiki_commit", "evidence_release", "paper_build_job", "results_lock",
        "numeric_registry", "checksum_manifest",
    )
    lines = ["schema_version = 1"]
    lines.extend(f"{key} = {_toml_quote(str(manifest[key]))}" for key in scalar_keys)
    if manifest.get("supersedes") is not None:
        lines.append(f"supersedes = {_toml_quote(str(manifest['supersedes']))}")
    for key in ("source_files", "rendered_files", "figure_files"):
        rendered = ", ".join(_toml_quote(str(item)) for item in manifest[key])
        lines.append(f"{key} = [{rendered}]")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_results_lock(
    path: Path,
    *,
    snapshot_id: str,
    evidence_release: str,
    release_dir: Path,
    source_commit: str,
    wiki_commit: str,
    paper_build_job: str,
) -> None:
    values = {
        "schema_version": "1",
        "snapshot_id": snapshot_id,
        "evidence_release": evidence_release,
        "evidence_release_manifest_sha256": common._sha256(release_dir / "release.json"),
        "evidence_release_checksums_sha256": common._sha256(release_dir / "checksums.sha256"),
        "source_commit": source_commit,
        "wiki_commit": wiki_commit,
        "paper_build_job": paper_build_job,
    }
    path.write_text(
        "".join(f'{key}: "{value}"\n' for key, value in values.items()),
        encoding="utf-8",
    )


def _activate_snapshot(
    root: Path, snapshot_id: str, supersedes: str | None
) -> None:
    current_path = root / "paper/CURRENT"
    project_path = root / "PROJECT.toml"
    reproducibility_path = root / "REPRODUCIBILITY.toml"
    originals = {
        current_path: current_path.read_text(encoding="utf-8"),
        project_path: project_path.read_text(encoding="utf-8"),
        reproducibility_path: reproducibility_path.read_text(encoding="utf-8"),
    }
    current = originals[current_path].strip()
    if current != "UNRELEASED" and supersedes != current:
        raise common.GateError(
            f"activation would replace {current}; plan.supersedes must name that snapshot"
        )
    updated = {
        current_path: f"{snapshot_id}\n",
        project_path: common._replace_toml_pointer(
            originals[project_path], "paper_snapshot", snapshot_id
        ),
        reproducibility_path: common._replace_toml_pointer(
            originals[reproducibility_path], "paper_snapshot", snapshot_id
        ),
    }
    written: list[Path] = []
    try:
        for path, text in updated.items():
            common._atomic_text(path, text)
            written.append(path)
    except Exception:
        for path in reversed(written):
            common._atomic_text(path, originals[path])
        raise


def build_paper_snapshot(
    root: Path,
    plan_path: Path,
    *,
    activate: bool = False,
) -> dict[str, Any]:
    """Validate and atomically build one immutable conference-paper snapshot."""

    root = root.resolve()
    plan_path = plan_path.resolve()
    if not plan_path.is_relative_to(root):
        raise common.GateError("snapshot plan must be inside the project root")
    common._verify_clean_worktree(root)
    plan = common._require_mapping(common._load_json(plan_path), "snapshot plan")
    common._required(
        plan,
        (
            "schema_version", "snapshot_id", "venue", "submission_state", "source_commit",
            "wiki_commit", "evidence_release", "paper_build_job", "source_files",
            "rendered_files", "figure_files", "numeric_annotations",
        ),
        "snapshot plan",
    )
    if plan["schema_version"] != 1:
        raise common.GateError("unsupported snapshot-plan schema_version")
    snapshot_id = plan["snapshot_id"]
    if not isinstance(snapshot_id, str) or SNAPSHOT_ID.fullmatch(snapshot_id) is None:
        raise common.GateError("snapshot_id must match LP-SNAP-[A-Z0-9-]+")
    if not isinstance(plan["venue"], str) or not plan["venue"].strip():
        raise common.GateError("snapshot venue is absent")
    if not isinstance(plan["submission_state"], str) or not plan["submission_state"].strip():
        raise common.GateError("snapshot submission_state is absent")
    source_commit = common._verify_commit(root, plan["source_commit"], "snapshot source_commit")
    wiki_commit = common._verify_commit(root, plan["wiki_commit"], "snapshot wiki_commit")
    _verify_wiki_commit(root, wiki_commit)
    release_manifest = _verify_frozen_release(root, plan["evidence_release"])
    release_dir = (root / "results/frozen" / str(plan["evidence_release"])).resolve()
    release_checksums = common._checksum_registry(release_dir / "checksums.sha256")
    release_jobs = _release_jobs(root, release_dir, release_manifest)
    build_record = _verify_build_job(root, plan["paper_build_job"], source_commit)

    source_values = common._require_list(plan["source_files"], "source_files")
    rendered_values = common._require_list(plan["rendered_files"], "rendered_files")
    figure_values = common._require_list(plan["figure_files"], "figure_files")
    if not source_values or not rendered_values:
        raise common.GateError("snapshot requires at least one source and one rendered export")
    sources = [
        _source_entry(root, value, label=f"source_files[{index}]", banned=True)
        for index, value in enumerate(source_values)
    ]
    rendered = [
        _source_entry(root, value, label=f"rendered_files[{index}]", banned=True)
        for index, value in enumerate(rendered_values)
    ]
    _verify_rendered_outputs(root, rendered, build_record)
    figures: list[dict[str, Any]] = []
    for index, value in enumerate(figure_values):
        item = _source_entry(root, value, label=f"figure_files[{index}]", banned=True)
        raw = common._require_mapping(value, f"figure_files[{index}]")
        common._required(raw, ("numbers",), f"figure_files[{index}]")
        numbers_rel, numbers_path = common._safe_file(
            root, raw["numbers"], f"figure_files[{index}].numbers"
        )
        if not _is_under(item["source"], release_dir) or not _is_under(numbers_path, release_dir):
            raise common.GateError("figures and figure sidecars must come from the frozen evidence release")
        item["numbers"] = numbers_rel
        item["numbers_source"] = numbers_path
        item["numbers_target"] = f"{item['target']}.numbers.jsonl"
        figures.append(item)
    targets = [item["target"] for item in (*sources, *rendered, *figures)]
    targets.extend(item["numbers_target"] for item in figures)
    if len(targets) != len(set(targets)):
        raise common.GateError("snapshot target paths collide")
    for source in sources:
        if source["source"].suffix.lower() not in {".bib", ".md", ".tex", ".txt"}:
            raise common.GateError(f"paper source is not auditable text: {source['path']}")
        _verify_source_at_commit(root, source_commit, source["source"])

    annotations_rel, annotations_path = common._safe_file(
        root, plan["numeric_annotations"], "numeric annotations"
    )
    if any(Path(annotations_rel).is_relative_to(prefix) for prefix in BANNED_SOURCE_ROOTS):
        raise common.GateError("numeric annotations come from a quarantined surface")
    auditable_texts = [
        item
        for item in (*sources, *rendered)
        if item["source"].suffix.lower() in {".bib", ".md", ".tex", ".txt", ".html"}
    ]
    expected = {
        key
        for source in auditable_texts
        for key in _numeric_occurrences(source["source"], source["target"])
    }
    annotation_records = _load_jsonl(annotations_path, "numeric annotations")
    registry: dict[tuple[str, int, str, int], dict[str, Any]] = {}
    claims_text = (root / "wiki/claims/Current-Claim-Language.md").read_text(encoding="utf-8")
    evidence_text = (root / "wiki/evidence/Evidence-Ledger.md").read_text(encoding="utf-8")
    for index, item in enumerate(annotation_records):
        key = _record_key(item, f"numeric annotation[{index}]")
        if key in registry:
            raise common.GateError(f"duplicate numeric annotation: {key}")
        if item.get("figure_sidecar") is True:
            raise common.GateError("source numeric annotations may not masquerade as figure sidecars")
        verified = _validate_numeric_record(
            item,
            key=key,
            release_dir=release_dir,
            release_checksums=release_checksums,
            release_manifest=release_manifest,
            release_jobs=release_jobs,
            claims_text=claims_text,
            evidence_text=evidence_text,
        )
        item.update(verified)
        registry[key] = item
    missing = sorted(expected - set(registry))
    stale = sorted(set(registry) - expected)
    if missing:
        raise common.GateError(f"unregistered paper numeric occurrence: {missing[0]}")
    if stale:
        raise common.GateError(f"stale paper numeric annotation: {stale[0]}")

    figure_sidecars: dict[str, list[dict[str, Any]]] = {}
    for figure in figures:
        records = _load_jsonl(figure["numbers_source"], f"figure sidecar {figure['target']}")
        if not records:
            raise common.GateError(f"figure sidecar is empty: {figure['numbers']}")
        for index, item in enumerate(records):
            key = _record_key(item, f"figure sidecar {figure['target']}[{index}]")
            if key[0] != figure["target"] or key[1] != 0:
                raise common.GateError(
                    f"figure sidecar must use file={figure['target']!r}, line=0: {key}"
                )
            if key in registry:
                raise common.GateError(f"duplicate global numeric occurrence: {key}")
            verified = _validate_numeric_record(
                item,
                key=key,
                release_dir=release_dir,
                release_checksums=release_checksums,
                release_manifest=release_manifest,
                release_jobs=release_jobs,
                claims_text=claims_text,
                evidence_text=evidence_text,
                figure=True,
            )
            item.update(verified)
            registry[key] = item
        figure_sidecars[figure["numbers_target"]] = records

    target = root / "paper/snapshots" / snapshot_id
    if target.exists():
        raise common.GateError(f"immutable paper snapshot already exists: {target.relative_to(root)}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{snapshot_id}.staging-", dir=target.parent))
    try:
        for item in (*sources, *rendered, *figures):
            destination = staging / item["target"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item["source"], destination)
        for sidecar_target, records in figure_sidecars.items():
            destination = staging / sidecar_target
            destination.parent.mkdir(parents=True, exist_ok=True)
            _write_jsonl(destination, records)
        shutil.copy2(plan_path, staging / "snapshot-plan.json")
        ordered_registry = [registry[key] for key in sorted(registry)]
        _write_jsonl(staging / "numeric-provenance.jsonl", ordered_registry)
        snapshot_manifest = {
            "schema_version": 1,
            "state": "FROZEN",
            "snapshot_id": snapshot_id,
            "venue": plan["venue"],
            "submission_state": plan["submission_state"],
            "source_commit": source_commit,
            "wiki_commit": wiki_commit,
            "evidence_release": plan["evidence_release"],
            "paper_build_job": plan["paper_build_job"],
            "supersedes": plan.get("supersedes"),
            "results_lock": "results.lock.yaml",
            "numeric_registry": "numeric-provenance.jsonl",
            "checksum_manifest": "checksums.sha256",
            "source_files": [item["target"] for item in sources],
            "rendered_files": [item["target"] for item in rendered],
            "figure_files": [item["target"] for item in figures],
        }
        _write_snapshot_toml(staging / "snapshot.toml", snapshot_manifest)
        _write_results_lock(
            staging / "results.lock.yaml",
            snapshot_id=snapshot_id,
            evidence_release=str(plan["evidence_release"]),
            release_dir=release_dir,
            source_commit=source_commit,
            wiki_commit=wiki_commit,
            paper_build_job=str(plan["paper_build_job"]),
        )
        common._write_checksums(staging)
        common._verify_release_directory(staging)
        os.replace(staging, target)
        for path in target.rglob("*"):
            if path.is_file():
                path.chmod(path.stat().st_mode & ~0o222)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    if activate:
        try:
            _activate_snapshot(root, snapshot_id, plan.get("supersedes"))
        except Exception:
            for path in target.rglob("*"):
                if path.is_file():
                    path.chmod(path.stat().st_mode | 0o200)
            shutil.rmtree(target)
            raise
    return snapshot_manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a checksum-closed immutable conference-paper snapshot.",
        epilog=(
            "PLAN CONTRACT: JSON schema_version=1 with snapshot_id, venue, "
            "submission_state, source_commit, wiki_commit, evidence_release, "
            "paper_build_job, source_files/rendered_files [{path,target}], optional "
            "figure_files [{path,target,numbers}], and numeric_annotations JSONL. "
            "Every source NUMBER_TOKEN must have one exact annotation."
        ),
    )
    parser.add_argument("--plan", required=True, type=Path, help="reviewed snapshot-plan JSON")
    parser.add_argument("--project-root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument(
        "--activate",
        action="store_true",
        help="after building, advance paper/CURRENT and matching TOML pointers",
    )
    args = parser.parse_args(argv)
    try:
        manifest = build_paper_snapshot(
            args.project_root, args.plan, activate=args.activate
        )
    except common.GateError as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2))
        return 2
    except Exception as exc:
        print(json.dumps({"status": "TOOL_ERROR", "error": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 3
    print(json.dumps({
        "status": "FROZEN",
        "snapshot_id": manifest["snapshot_id"],
        "evidence_release": manifest["evidence_release"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
