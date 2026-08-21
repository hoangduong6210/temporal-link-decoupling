#!/usr/bin/env python3
"""Generate fail-closed numeric annotations for the conference TeX source."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Sequence

try:
    from scripts import numeric_evidence
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    import numeric_evidence  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_REL = "payload/results/audit/scientific-matrix.json"
CLAIM_ID = "LP-C-DECOUPLING-001"
EVIDENCE_ID = "LP-E-SCIENTIFIC-MATRIX-001"
JOB_ID = "LP-JOB-SLURM-A003-FINAL-RECONCILE-R2"
TABLE_ROW = re.compile(
    r"^(CoEdit|MOOC|Wikipedia) & (Coupled|Decoupled) & "
    r"(\d\.\d{4}) & (\d\.\d{4}) \\\\s*$"
)
SELECTORS = {
    ("CoEdit", "Coupled"): ("$.summary[0].ind_ap_mean", "$.summary[0].ind_ap_std"),
    ("CoEdit", "Decoupled"): ("$.summary[3].ind_ap_mean", "$.summary[3].ind_ap_std"),
    ("MOOC", "Coupled"): ("$.summary[1].ind_ap_mean", "$.summary[1].ind_ap_std"),
    ("MOOC", "Decoupled"): ("$.summary[4].ind_ap_mean", "$.summary[4].ind_ap_std"),
    ("Wikipedia", "Coupled"): ("$.summary[2].ind_ap_mean", "$.summary[2].ind_ap_std"),
    ("Wikipedia", "Decoupled"): ("$.summary[5].ind_ap_mean", "$.summary[5].ind_ap_std"),
}


class AnnotationError(RuntimeError):
    """A paper number is missing an explicit admissible classification."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _structural_exemption(line: str, literal: str) -> str | None:
    stripped = line.strip()
    if stripped == r"\pdfminorversion=5" and literal == "5":
        return "software-version"
    if stripped == r"\pdfinfoomitdate=1" and literal == "1":
        return "page-layout"
    if stripped == r"\begin{thebibliography}{9}" and literal == "9":
        return "page-layout"
    if re.search(r"(?:Proc\. [A-Z]+\}, |learning,'' |probes,'' )\d{4}\.$", stripped):
        return "bibliographic-locator"
    return None


def generate(source: Path, target_name: str, artifact: Path, output: Path) -> list[dict[str, Any]]:
    artifact_sha256 = _sha256(artifact)
    records: list[dict[str, Any]] = []
    seen_rows: set[tuple[str, str]] = set()
    for lineno, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        occurrences: dict[str, int] = {}
        row = TABLE_ROW.fullmatch(line)
        row_literals = set(row.groups()[2:]) if row else set()
        for match in numeric_evidence.NUMBER_TOKEN.finditer(line):
            literal = match.group(0)
            occurrences[literal] = occurrences.get(literal, 0) + 1
            key = {
                "file": target_name,
                "line": lineno,
                "literal": literal,
                "occurrence": occurrences[literal],
            }
            if row and literal in row_literals:
                corpus, arm, mean, std = row.groups()
                row_key = (corpus, arm)
                selectors = SELECTORS.get(row_key)
                if selectors is None:
                    raise AnnotationError(f"unregistered result row at line {lineno}: {row_key}")
                selector = selectors[0] if literal == mean else selectors[1]
                assertion = {
                    "mode": "rounded",
                    "transform": "identity",
                    "decimal_places": 4,
                    "rounding": "half-even",
                }
                numeric_evidence.verify_numeric_assertion(
                    artifact=artifact,
                    selector=selector,
                    literal=literal,
                    assertion=assertion,
                )
                key.update({
                    "kind": "empirical",
                    "claim_id": CLAIM_ID,
                    "evidence_id": EVIDENCE_ID,
                    "job_id": JOB_ID,
                    "artifact_path": ARTIFACT_REL,
                    "artifact_sha256": artifact_sha256,
                    "artifact_selector": selector,
                    "value_assertion": assertion,
                })
                seen_rows.add(row_key)
            else:
                exemption = _structural_exemption(line, literal)
                if exemption is None:
                    raise AnnotationError(
                        f"unclassified numeric occurrence: {source}:{lineno}:{literal}"
                    )
                key.update({"kind": "structural", "exemption": exemption})
            records.append(key)
    if seen_rows != set(SELECTORS):
        raise AnnotationError(f"paper result coverage mismatch: {sorted(set(SELECTORS) - seen_rows)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(
            json.dumps(item, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n"
            for item in records
        ),
        encoding="utf-8",
    )
    return records


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "paper/candidate/overleaf/main.tex")
    parser.add_argument("--target-name", default="overleaf/main.tex")
    parser.add_argument(
        "--artifact", type=Path,
        default=ROOT / "results/frozen/LP-REL-2026-A003-001/payload/results/audit/scientific-matrix.json",
    )
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "paper/candidate/overleaf/numeric-annotations.jsonl",
    )
    args = parser.parse_args(argv)
    records = generate(
        args.source.resolve(), args.target_name, args.artifact.resolve(), args.output.resolve()
    )
    print(json.dumps({"records": len(records), "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
