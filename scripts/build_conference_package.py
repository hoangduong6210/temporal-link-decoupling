#!/usr/bin/env python3
"""Clean-build the conference PDF and deterministic self-contained Overleaf ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Sequence
import zipfile

try:
    from scripts.generate_conference_figures import generate
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from generate_conference_figures import generate  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
FIXED_ZIP_TIME = (2026, 8, 21, 0, 0, 0)


class PackageBuildError(RuntimeError):
    """The publication package could not be built reproducibly."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _copy_file(source: Path, target: Path) -> None:
    if not source.is_file() or source.is_symlink():
        raise PackageBuildError(f"missing regular source file: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def _deterministic_zip(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(relative, date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, path.read_bytes(), compresslevel=9)


def build(
    *,
    source_dir: Path,
    vendor_class: Path,
    aggregate: Path,
    output_dir: Path,
) -> dict[str, str]:
    if shutil.which("latexmk") is None:
        raise PackageBuildError("latexmk is required for the conference build")
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="lp-conference-build-") as raw_stage:
        stage = Path(raw_stage)
        package_dir = stage / "overleaf"
        build_dir = stage / "build"
        stage_figures = generate(aggregate, package_dir / "figs")
        _copy_file(source_dir / "main.tex", package_dir / "main.tex")
        _copy_file(source_dir / "README.md", package_dir / "README.md")
        _copy_file(vendor_class, package_dir / "IEEEtran.cls")
        build_dir.mkdir()

        environment = os.environ.copy()
        environment.update({
            "SOURCE_DATE_EPOCH": "1787270400",
            "FORCE_SOURCE_DATE": "1",
            "TZ": "UTC",
        })
        command = [
            "latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error",
            "-file-line-error", f"-outdir={build_dir}", "main.tex",
        ]
        result = subprocess.run(
            command, cwd=package_dir, env=environment, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
        )
        if result.returncode != 0 or not (build_dir / "main.pdf").is_file():
            tail = "\n".join(result.stdout.splitlines()[-40:])
            raise PackageBuildError(f"LaTeX build failed:\n{tail}")

        pdf = output_dir / "link-prediction-conference.pdf"
        bundle = output_dir / "link-prediction-overleaf.zip"
        _copy_file(build_dir / "main.pdf", pdf)
        _deterministic_zip(package_dir, bundle)
        figures = []
        for figure in stage_figures:
            target = output_dir / "overleaf" / "figs" / figure.name
            _copy_file(figure, target)
            figures.append(target)

    artifacts = [pdf, bundle, *figures, vendor_class]

    def display_path(path: Path) -> str:
        try:
            return path.relative_to(ROOT).as_posix()
        except ValueError:
            return path.resolve().as_posix()

    return {display_path(path): _sha256(path) for path in artifacts}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "paper/candidate/overleaf")
    parser.add_argument("--vendor-class", type=Path, default=ROOT / "paper/vendor/IEEEtran.cls")
    parser.add_argument(
        "--aggregate", type=Path,
        default=ROOT / "results/frozen/LP-REL-2026-A003-001/payload/results/audit/scientific-matrix.json",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "paper/candidate")
    args = parser.parse_args(argv)
    payload = build(
        source_dir=args.source_dir.resolve(),
        vendor_class=args.vendor_class.resolve(),
        aggregate=args.aggregate.resolve(),
        output_dir=args.output_dir.resolve(),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
