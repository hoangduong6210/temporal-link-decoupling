from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
CONFERENCE = ROOT / "paper/conference"
SOURCE_SHA256 = "22ab0d4806c619769f9991ad43260cfc7afee7827a2c8bd6a7ce9d83189ba459"
PDF_SHA256 = "3a8f342f1585cfcd28059cb15c60947c874692d3e407d493be734a0db72b4793"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_single_conference_manuscript_is_hash_closed_and_unadmitted() -> None:
    assert (ROOT / "paper/CURRENT").read_text(encoding="utf-8").strip() == "UNRELEASED"
    assert not (ROOT / "paper/candidate").exists()
    assert not [
        path for path in (ROOT / "paper/snapshots").iterdir() if path.is_dir()
    ]

    source_path = CONFERENCE / "overleaf/main.tex"
    source = source_path.read_text(encoding="utf-8")
    assert _sha256(source_path) == SOURCE_SHA256
    assert _sha256(CONFERENCE / "Link_Predict.pdf") == PDF_SHA256
    assert "Duong Viet Huy" in source
    assert "huydv6210@gmail.com" in source
    assert "Reproducibility note:" not in source

    for line in (CONFERENCE / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        artifact = CONFERENCE / relative
        assert artifact.is_file()
        assert _sha256(artifact) == expected

    with zipfile.ZipFile(CONFERENCE / "Link_Predict_Overleaf.zip") as archive:
        assert set(archive.namelist()) == {
            "IEEEtran.cls",
            "README.md",
            "figs/fig4_coedit_headline.png",
            "figs/fig5_cross_dataset.png",
            "figs/fig6_decoupling_ablation.png",
            "main.tex",
        }
        assert archive.testzip() is None


@pytest.mark.skipif(shutil.which("latexmk") is None, reason="latexmk is not installed")
def test_conference_overleaf_package_clean_builds(tmp_path: Path) -> None:
    with zipfile.ZipFile(CONFERENCE / "Link_Predict_Overleaf.zip") as archive:
        archive.extractall(tmp_path)
    build = tmp_path / "build"
    build.mkdir()
    environment = {
        **os.environ,
        "SOURCE_DATE_EPOCH": "1767225600",
        "FORCE_SOURCE_DATE": "1",
        "TZ": "UTC",
    }
    result = subprocess.run(
        [
            "latexmk",
            "-pdf",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            f"-outdir={build}",
            "main.tex",
        ],
        cwd=tmp_path,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert result.returncode == 0, "\n".join(result.stdout.splitlines()[-40:])
    assert _sha256(build / "main.pdf") == PDF_SHA256
