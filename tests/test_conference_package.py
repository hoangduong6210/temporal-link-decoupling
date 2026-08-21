from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_conference_figures_are_monochrome_and_value_label_free(tmp_path: Path) -> None:
    figures = _load(ROOT / "scripts/generate_conference_figures.py", "conference_figures")
    artifact = (
        ROOT
        / "results/frozen/LP-REL-2026-A003-001/payload/results/audit/scientific-matrix.json"
    )
    outputs = figures.generate(artifact, tmp_path)
    assert {path.name for path in outputs} == {
        "protocol-contrast.pdf",
        "inductive-ordering.pdf",
    }
    for path in outputs:
        assert path.read_bytes().startswith(b"%PDF-")
        if shutil.which("pdfimages"):
            listing = subprocess.run(
                ["pdfimages", "-list", str(path)], text=True,
                capture_output=True, check=True,
            ).stdout
            assert not [line for line in listing.splitlines() if line.strip()[:1].isdigit()]
    source = (ROOT / "scripts/generate_conference_figures.py").read_text()
    assert "set_xticks([])" in source
    assert '"pdf.fonttype": 42' in source


def test_conference_paper_has_current_authors_and_editorial_boundary() -> None:
    text = (ROOT / "paper/candidate/overleaf/main.tex").read_text(encoding="utf-8")
    for author in ("Duong Viet Hoang", "Duong Viet Huy", "Lun-Min Shih"):
        assert author in text
    assert "Kent State University, United States" in text
    assert "huydv6210@gmail.com" in text
    banned = (
        "Reproducibility note:",
        "will be released upon acceptance",
        "wrong default",
        "near-universal",
        "decisive",
        "To our knowledge",
        "irreversible",
        "achieves state-of-the-art",
        "what we are selling",
    )
    lowered = text.lower()
    assert not [phrase for phrase in banned if phrase.lower() in lowered]


def test_conference_numeric_annotations_are_complete_and_value_verified(tmp_path: Path) -> None:
    annotations = _load(
        ROOT / "scripts/generate_paper_annotations.py", "conference_annotations"
    )
    source = ROOT / "paper/candidate/overleaf/main.tex"
    artifact = (
        ROOT
        / "results/frozen/LP-REL-2026-A003-001/payload/results/audit/scientific-matrix.json"
    )
    records = annotations.generate(source, "overleaf/main.tex", artifact, tmp_path / "numbers.jsonl")
    assert len(records) == 22
    assert sum(item["kind"] == "empirical" for item in records) == 12
    assert sum(item["kind"] == "structural" for item in records) == 10
    assert {item.get("job_id") for item in records if item["kind"] == "empirical"} == {
        "LP-JOB-SLURM-A003-FINAL-RECONCILE-R2"
    }


@pytest.mark.skipif(shutil.which("latexmk") is None, reason="latexmk is not installed")
def test_conference_package_clean_builds(tmp_path: Path) -> None:
    package = _load(ROOT / "scripts/build_conference_package.py", "conference_package")
    payload = package.build(
        source_dir=ROOT / "paper/candidate/overleaf",
        vendor_class=ROOT / "paper/vendor/IEEEtran.cls",
        aggregate=(
            ROOT
            / "results/frozen/LP-REL-2026-A003-001/payload/results/audit/scientific-matrix.json"
        ),
        output_dir=tmp_path,
    )
    assert (tmp_path / "link-prediction-conference.pdf").read_bytes().startswith(b"%PDF-")
    bundle = tmp_path / "link-prediction-overleaf.zip"
    assert bundle.is_file()
    with zipfile.ZipFile(bundle) as archive:
        assert set(archive.namelist()) == {
            "IEEEtran.cls",
            "README.md",
            "figs/inductive-ordering.pdf",
            "figs/protocol-contrast.pdf",
            "main.tex",
        }
    assert payload
