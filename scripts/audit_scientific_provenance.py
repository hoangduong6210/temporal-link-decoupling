#!/usr/bin/env python3
"""Audit canonical numeric provenance and release-pointer consistency.

Canonical consistency can pass while the project is explicitly unreleased.
Release readiness remains blocked until immutable evidence and paper snapshots
exist and satisfy the contracts documented under ``wiki/`` and ``paper/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

try:  # Python 3.11+
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - exercised on the cluster's Python 3.9
    tomllib = None


ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
UNRELEASED = "UNRELEASED"

CLAIM_ID = re.compile(r"\bLP-C-[A-Z0-9-]+\b")
EVIDENCE_ID = re.compile(r"\bLP-E-[A-Z0-9-]+\b")
JOB_ID = re.compile(r"\bLP-JOB-[A-Z0-9-]+\b")
SCIENTIFIC_LITERAL = re.compile(
    r"(?<![A-Za-z0-9_])(?:[+-]?\d+\.\d+(?:[eE][+-]?\d+)?|"
    r"[+-]?\d+(?:\.\d+)?\s*(?:%|pp)\b|"
    r"(?:±|\\pm)\s*\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|"
    r"\d+(?:\.\d+)?\s*(?::|/)\s*\d+(?:\.\d+)?)"
)
NUMBER_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_])[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?(?:\s*(?:%|pp))?"
    r"(?![A-Za-z0-9_])"
)
NUMBER_WORD = re.compile(
    r"\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|hundred|thousand|million|billion)\b",
    re.IGNORECASE,
)
STRUCTURAL_IDENTIFIER = re.compile(
    r"\b(?:LP-(?:RQ|D|P|E|C|H|JOB)-[A-Z0-9-]+|DEC-\d+|SHA-\d+)\b"
)
INTERNAL_MARKER = re.compile(
    r"\b(?:claude|grok|chatgpt|codex|openai|anthropic|gemini)\b|"
    r"\bPM(?:'s)?\b|reviewer\s*(?:#|Q|§)|panel asked|rebuttal|"
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
SNAPSHOT_REQUIRED = {
    "snapshot.toml",
    "results.lock.yaml",
    "numeric-provenance.jsonl",
    "checksums.sha256",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_toml(path: Path) -> dict[str, object]:
    if tomllib is not None:
        with path.open("rb") as stream:
            return tomllib.load(stream)

    # Dependency-free parser for the deliberately small manifest subset used by
    # this audit. Scientific release validation must not disappear merely
    # because the host Python predates stdlib TOML support.
    root: dict[str, object] = {}
    current = root
    logical_lines: list[str] = []
    pending = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        pending = f"{pending} {line}".strip()
        if pending.count("[") > pending.count("]"):
            continue
        logical_lines.append(pending)
        pending = ""
    if pending:
        raise ValueError(f"unterminated TOML value in {path}")

    for line in logical_lines:
        if line.startswith("[") and line.endswith("]"):
            table = line[1:-1].strip()
            current = root
            for component in table.split("."):
                child = current.setdefault(component, {})
                if not isinstance(child, dict):
                    raise ValueError(f"invalid TOML table in {path}: {table}")
                current = child
            continue
        key, raw_value = (part.strip() for part in line.split("=", 1))
        if raw_value.startswith('"'):
            value: object = json.loads(raw_value)
        elif raw_value.startswith("["):
            value = json.loads(re.sub(r",\s*]$", "]", raw_value))
        elif raw_value in {"true", "false"}:
            value = raw_value == "true"
        else:
            value = int(raw_value)
        current[key] = value
    return root


def _checksums(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(maxsplit=1)
        entries[rel] = digest
    return entries


def _yaml_scalar_map(path: Path) -> dict[str, str]:
    """Parse the flat, string-valued results lock without a YAML dependency."""
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            raise ValueError(f"invalid results lock line in {path}: {raw}")
        key, value = (part.strip() for part in line.split(":", 1))
        values[key] = value.strip('"\'')
    return values


def _job_record(job_id: str, issues: list[str]) -> dict[str, object] | None:
    path = ROOT / "evidence" / "jobs" / f"{job_id}.toml"
    if not path.is_file():
        issues.append(f"missing job record: {job_id}")
        return None
    registered = _checksums(ROOT / "evidence/jobs/checksums.sha256")
    rel = path.relative_to(ROOT).as_posix()
    if registered.get(rel) != _sha256(path):
        issues.append(f"job checksum mismatch or missing registration: {job_id}")
    record = _load_toml(path)
    if record.get("job_id") != job_id:
        issues.append(f"job record identity mismatch: {job_id}")
    return record


def _claim_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^### (LP-C-[A-Z0-9-]+)\s*$", text, re.MULTILINE))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[match.start():end]
    return sections


def _mask_structural_wiki_tokens(line: str) -> str:
    """Mask governance locators while leaving disguised scientific values visible."""
    masked = re.sub(r"\d{4}-\d{2}-\d{2}", "", line)
    masked = STRUCTURAL_IDENTIFIER.sub("", masked)
    masked = re.sub(r"\bv?\d+(?:\.\d+)+\b", "", masked, flags=re.IGNORECASE)
    masked = re.sub(r"^\s*\d+[.)]\s+", "", masked)
    masked = re.sub(r"\]\([^)]+\)", "]()", masked)
    masked = re.sub(r"\[[^]]*,\s*\d{4}\]", "", masked)

    def replace_code(match: re.Match[str]) -> str:
        content = match.group(1)
        is_locator = (
            bool(STRUCTURAL_IDENTIFIER.fullmatch(content))
            or "/" in content
            or bool(re.fullmatch(r"v?\d+(?:\.\d+)+", content, re.IGNORECASE))
            or bool(re.search(r"\.(?:json|md|npz|py|sha256|toml|yaml|yml)$", content))
        )
        return "" if is_locator else content

    return re.sub(r"`([^`]*)`", replace_code, masked)


def _audit_wiki(issues: list[str]) -> dict[str, object]:
    claims_path = WIKI / "claims/Current-Claim-Language.md"
    claims_text = claims_path.read_text(encoding="utf-8")
    evidence_text = (WIKI / "evidence/Evidence-Ledger.md").read_text(encoding="utf-8")
    sections = _claim_sections(claims_text)
    resolved_jobs: set[str] = set()

    for claim_id, section in sections.items():
        evidence = set(EVIDENCE_ID.findall(section))
        jobs = set(JOB_ID.findall(section))
        blocked = "**Lifecycle status:** BLOCKED" in section
        if not evidence:
            issues.append(f"claim has no evidence ID: {claim_id}")
        for evidence_id in evidence:
            if f"## {evidence_id}" not in evidence_text:
                issues.append(f"claim references unknown evidence: {claim_id} -> {evidence_id}")
        if blocked:
            if SCIENTIFIC_LITERAL.search(section):
                issues.append(f"blocked claim restates a scientific numeric literal: {claim_id}")
            if "**Execution job:** NONE" not in section and not jobs:
                issues.append(f"blocked claim has ambiguous execution state: {claim_id}")
            continue
        if not jobs:
            issues.append(f"validated/admitted claim has no execution job: {claim_id}")
        for job_id in jobs:
            record = _job_record(job_id, issues)
            resolved_jobs.add(job_id)
            if record is None:
                continue
            supported = set(record.get("supported_evidence_ids", []))
            if not evidence.issubset(supported):
                issues.append(f"job does not support claim evidence: {claim_id} -> {job_id}")
            scientific_claims = set(record.get("supported_scientific_claim_ids", []))
            if "**Paper eligibility:** true" in section and claim_id not in scientific_claims:
                issues.append(f"paper-eligible claim is not supported by scientific job: {claim_id}")

    scalar_locations: list[str] = []
    number_word_locations: list[str] = []
    structural_numeric_occurrences = 0
    claim_numeric_occurrences = 0
    for path in sorted(WIKI.rglob("*.md")):
        in_front_matter = False
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if lineno == 1 and line == "---":
                in_front_matter = True
                continue
            if in_front_matter:
                if line == "---":
                    in_front_matter = False
                continue
            if path == claims_path and any(line in section.splitlines() for section in sections.values()):
                claim_numeric_occurrences += len(NUMBER_TOKEN.findall(line))
                claim_numeric_occurrences += len(NUMBER_WORD.findall(line))
                continue
            masked = _mask_structural_wiki_tokens(line)
            structural_numeric_occurrences += len(NUMBER_TOKEN.findall(line)) - len(NUMBER_TOKEN.findall(masked))
            if NUMBER_TOKEN.search(masked):
                scalar_locations.append(f"{path.relative_to(ROOT)}:{lineno}")
            if NUMBER_WORD.search(masked):
                number_word_locations.append(f"{path.relative_to(ROOT)}:{lineno}")
    if scalar_locations:
        issues.extend(f"unclassified numeric token outside claim registry: {item}" for item in scalar_locations)
    if number_word_locations:
        issues.extend(f"unclassified number word outside claim registry: {item}" for item in number_word_locations)

    zero_claims = [
        claim_id for claim_id, section in sections.items()
        if re.search(r"\b(?:equals?|=)\s+zero\b", section, re.IGNORECASE)
    ]
    return {
        "claim_count": len(sections),
        "resolved_job_ids": sorted(resolved_jobs),
        "unclassified_numeric_tokens_outside_claim_registry": scalar_locations,
        "unclassified_number_words_outside_claim_registry": number_word_locations,
        "structural_numeric_occurrences": structural_numeric_occurrences,
        "claim_numeric_occurrences": claim_numeric_occurrences,
        "number_word_claims_with_section_level_provenance": zero_claims,
    }


def _numeric_occurrences(path: Path) -> list[tuple[int, str, int]]:
    occurrences: list[tuple[int, str, int]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        seen: dict[str, int] = {}
        for match in NUMBER_TOKEN.finditer(line):
            literal = match.group(0)
            seen[literal] = seen.get(literal, 0) + 1
            occurrences.append((lineno, literal, seen[literal]))
    return occurrences


def _audit_snapshot(snapshot_id: str, evidence_release: str, issues: list[str]) -> dict[str, object]:
    snapshot = ROOT / "paper/snapshots" / snapshot_id
    if not snapshot.is_dir():
        issues.append(f"current paper snapshot directory is missing: {snapshot_id}")
        return {"snapshot_id": snapshot_id, "state": "INVALID"}
    missing = sorted(name for name in SNAPSHOT_REQUIRED if not (snapshot / name).is_file())
    if missing:
        issues.append(f"snapshot missing required files: {snapshot_id}: {', '.join(missing)}")
        return {"snapshot_id": snapshot_id, "state": "INVALID", "missing": missing}

    manifest = _load_toml(snapshot / "snapshot.toml")
    lock = _yaml_scalar_map(snapshot / "results.lock.yaml")
    if manifest.get("snapshot_id") != snapshot_id:
        issues.append("snapshot manifest identity does not match paper/CURRENT")
    if manifest.get("evidence_release") != evidence_release:
        issues.append("snapshot evidence release does not match PROJECT.toml")
    if lock.get("evidence_release") != evidence_release:
        issues.append("results lock does not match current evidence release")
    for key in ("source_commit", "wiki_commit"):
        if not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get(key, ""))):
            issues.append(f"snapshot lacks a clean 40-hex {key}")

    checksums = _checksums(snapshot / "checksums.sha256")
    declared = [
        *manifest.get("source_files", []),
        *manifest.get("rendered_files", []),
        *manifest.get("figure_files", []),
        "snapshot.toml", "results.lock.yaml", "numeric-provenance.jsonl",
    ]
    for rel in declared:
        artifact = (snapshot / str(rel)).resolve()
        if not artifact.is_relative_to(snapshot.resolve()):
            issues.append(f"snapshot path escapes root: {rel}")
            continue
        if not artifact.is_file():
            issues.append(f"snapshot artifact is missing: {rel}")
        elif checksums.get(str(rel)) != _sha256(artifact):
            issues.append(f"snapshot artifact checksum mismatch: {rel}")

    claims_text = (WIKI / "claims/Current-Claim-Language.md").read_text(encoding="utf-8")
    evidence_text = (WIKI / "evidence/Evidence-Ledger.md").read_text(encoding="utf-8")

    def validate_numeric_record(item: dict[str, object], key: tuple[str, int, str, int]) -> None:
        kind = item.get("kind")
        if kind in {"empirical", "protocol", "derived"}:
            for required in ("claim_id", "evidence_id", "job_id", "artifact_sha256", "artifact_selector"):
                if not item.get(required):
                    issues.append(f"numeric record lacks {required}: {key}")
            claim_id = str(item.get("claim_id", ""))
            evidence_id = str(item.get("evidence_id", ""))
            job_id = str(item.get("job_id", ""))
            if f"### {claim_id}" not in claims_text:
                issues.append(f"numeric record references unknown claim: {key}")
            if f"## {evidence_id}" not in evidence_text:
                issues.append(f"numeric record references unknown evidence: {key}")
            if not re.fullmatch(r"[0-9a-f]{64}", str(item.get("artifact_sha256", ""))):
                issues.append(f"numeric record has invalid artifact checksum: {key}")
            if job_id:
                record = _job_record(job_id, issues)
                if record is not None:
                    if record.get("scientific") is not True:
                        issues.append(f"numeric record uses a non-scientific job: {key}")
                    if not re.fullmatch(r"[0-9a-f]{40}", str(record.get("source_commit", ""))):
                        issues.append(f"scientific job lacks a clean source commit: {job_id}")
                    if evidence_id not in set(record.get("supported_evidence_ids", [])):
                        issues.append(f"scientific job does not support numeric evidence: {key}")
                    if claim_id not in set(record.get("supported_scientific_claim_ids", [])):
                        issues.append(f"scientific job does not support numeric claim: {key}")
        elif kind == "structural":
            if item.get("exemption") not in ALLOWED_STRUCTURAL_EXEMPTIONS:
                issues.append(f"numeric record has invalid structural exemption: {key}")
        else:
            issues.append(f"numeric record has invalid kind: {key}")

    registry: dict[tuple[str, int, str, int], dict[str, object]] = {}
    registry_path = snapshot / "numeric-provenance.jsonl"
    for lineno, line in enumerate(registry_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            key = (item["file"], int(item["line"]), item["literal"], int(item["occurrence"]))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            issues.append(f"invalid numeric registry record at line {lineno}: {exc}")
            continue
        if key in registry:
            issues.append(f"duplicate numeric registry record: {key}")
        registry[key] = item
        validate_numeric_record(item, key)

    expected: set[tuple[str, int, str, int]] = set()
    for rel in manifest.get("source_files", []):
        source = snapshot / str(rel)
        if source.suffix.lower() not in {".bib", ".md", ".tex", ".txt"} or not source.is_file():
            continue
        for line, literal, occurrence in _numeric_occurrences(source):
            expected.add((str(rel), line, literal, occurrence))
        for lineno, text_line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            if INTERNAL_MARKER.search(text_line):
                issues.append(f"internal/AI workflow marker in snapshot: {rel}:{lineno}")
    for key in sorted(expected - registry.keys()):
        issues.append(f"unregistered snapshot numeric occurrence: {key}")
    for key in sorted(registry.keys() - expected):
        if not registry[key].get("figure_sidecar", False):
            issues.append(f"stale numeric registry occurrence: {key}")

    for rel in manifest.get("figure_files", []):
        sidecar = snapshot / f"{rel}.numbers.jsonl"
        if not sidecar.is_file():
            issues.append(f"numeric figure lacks sidecar inventory: {rel}")
        elif checksums.get(f"{rel}.numbers.jsonl") != _sha256(sidecar):
            issues.append(f"figure numeric sidecar checksum mismatch: {rel}")
        else:
            for lineno, line in enumerate(sidecar.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                    key = (
                        str(item["file"]), int(item.get("line", 0)),
                        str(item["literal"]), int(item["occurrence"]),
                    )
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                    issues.append(f"invalid figure sidecar record {rel}:{lineno}: {exc}")
                    continue
                validate_numeric_record(item, key)
                if registry.get(key) != item:
                    issues.append(f"figure sidecar record is absent or stale in global registry: {key}")

    return {
        "snapshot_id": snapshot_id,
        "state": "AUDITED",
        "numeric_occurrences": len(expected),
        "numeric_registry_records": len(registry),
    }


def _quarantine_diagnostics() -> dict[str, object]:
    historical_json = sorted((ROOT / "results/historical").rglob("*.json"))
    normalized = 0
    for path in historical_json:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        serialized = json.dumps(payload)
        if re.search(r'"(?:job_id|run_id|source_commit)"\s*:', serialized):
            normalized += 1

    banner = "QUARANTINED LEGACY WORKING"
    binary_banner: dict[str, bool] = {}
    docx = ROOT / "paper/working/RSGNN_core_IEEE.docx"
    if docx.is_file():
        with zipfile.ZipFile(docx) as archive:
            document = archive.read("word/document.xml").decode("utf-8", errors="ignore")
        binary_banner[docx.relative_to(ROOT).as_posix()] = banner in document
    archive_path = ROOT / "paper/working/RSGNN_core_Overleaf.zip"
    if archive_path.is_file():
        with zipfile.ZipFile(archive_path) as archive:
            tex = "\n".join(
                archive.read(name).decode("utf-8", errors="ignore")
                for name in archive.namelist() if name.endswith((".tex", ".md"))
            )
        binary_banner[archive_path.relative_to(ROOT).as_posix()] = banner in tex

    duplicate_figures = 0
    for path in (ROOT / "paper/figs").glob("*.png"):
        twin = ROOT / "paper/working/overleaf/figs" / path.name
        if twin.is_file() and _sha256(path) == _sha256(twin):
            duplicate_figures += 1
    return {
        "historical_json_files": len(historical_json),
        "historical_json_with_normalized_execution_identity": normalized,
        "legacy_binary_has_visible_quarantine_banner": binary_banner,
        "top_level_paper_figures_matching_quarantined_working_copies": duplicate_figures,
    }


def audit() -> dict[str, object]:
    issues: list[str] = []
    project = _load_toml(ROOT / "PROJECT.toml")
    pointers = project.get("pointers", {})
    evidence_release = str(pointers.get("evidence_release", ""))
    paper_snapshot = str(pointers.get("paper_snapshot", ""))
    result_pointer = (ROOT / "results/CURRENT").read_text(encoding="utf-8").strip()
    paper_pointer = (ROOT / "paper/CURRENT").read_text(encoding="utf-8").strip()
    if result_pointer != evidence_release:
        issues.append("results/CURRENT disagrees with PROJECT.toml")
    if paper_pointer != paper_snapshot:
        issues.append("paper/CURRENT disagrees with PROJECT.toml")

    wiki = _audit_wiki(issues)
    if paper_snapshot == UNRELEASED:
        payload = [
            path.relative_to(ROOT / "paper/snapshots").as_posix()
            for path in (ROOT / "paper/snapshots").rglob("*")
            if path.is_file() and path.name not in {".gitkeep", "README.md"}
        ]
        if payload:
            issues.append(f"orphan paper snapshot payload while UNRELEASED: {payload}")
        snapshot: dict[str, object] = {"state": "NOT_PRESENT", "pointer": UNRELEASED}
    else:
        snapshot = _audit_snapshot(paper_snapshot, evidence_release, issues)

    reproducibility = _load_toml(ROOT / "REPRODUCIBILITY.toml")
    if reproducibility.get("evidence_release") != evidence_release:
        issues.append("REPRODUCIBILITY.toml evidence pointer mismatch")
    if reproducibility.get("paper_snapshot") != paper_snapshot:
        issues.append("REPRODUCIBILITY.toml paper pointer mismatch")
    for key, path_key in (
        ("protocol_sha256", "protocol_path"),
        ("runtime_manifest_sha256", "runtime_manifest"),
        ("data_manifest_sha256", "data_manifest"),
        ("data_checksums_sha256", "data_checksums"),
    ):
        path = ROOT / str(reproducibility[path_key])
        if reproducibility.get(key) != _sha256(path):
            issues.append(f"stale reproducibility hash: {key}")

    active_internal: list[str] = []
    for base_name in ("src", "experiments"):
        for path in sorted((ROOT / base_name).rglob("*.py")):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if INTERNAL_MARKER.search(line):
                    active_internal.append(f"{path.relative_to(ROOT)}:{lineno}")
    if active_internal:
        issues.extend(f"internal workflow residue on active surface: {item}" for item in active_internal)

    release_ready = (
        not issues
        and evidence_release != UNRELEASED
        and paper_snapshot != UNRELEASED
        and reproducibility.get("status") == "REPRODUCIBLE"
    )
    return {
        "schema_version": 1,
        "canonical_status": "PASS" if not issues else "FAIL",
        "release_readiness": "READY" if release_ready else "BLOCKED",
        "pointers": {
            "project_evidence_release": evidence_release,
            "results_current": result_pointer,
            "project_paper_snapshot": paper_snapshot,
            "paper_current": paper_pointer,
        },
        "wiki": wiki,
        "paper_snapshot": snapshot,
        "reproducibility_status": reproducibility.get("status"),
        "reproducibility_blockers": reproducibility.get("blockers", []),
        "active_internal_markers": active_internal,
        "quarantine_diagnostics": _quarantine_diagnostics(),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-canonical", action="store_true")
    mode.add_argument("--require-release", action="store_true")
    args = parser.parse_args()
    try:
        result = audit()
    except Exception as exc:  # fail closed while preserving a distinct tool-error code
        print(json.dumps({
            "schema_version": 1,
            "canonical_status": "TOOL_ERROR",
            "error": f"{type(exc).__name__}: {exc}",
        }, indent=2, sort_keys=True))
        return 3
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["canonical_status"] != "PASS":
        return 1
    if args.require_release and result["release_readiness"] != "READY":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
