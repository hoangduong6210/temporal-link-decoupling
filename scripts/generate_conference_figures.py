#!/usr/bin/env python3
"""Generate deterministic monochrome figures from the frozen LP aggregate."""

from __future__ import annotations

import argparse
from io import BytesIO
import json
import math
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42})


ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("coupled-end-to-end", "decoupled")
DATASETS = ("coedit", "mooc", "wikipedia")


class FigureBuildError(RuntimeError):
    """The frozen aggregate cannot produce the declared conference figures."""


def _load_rows(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = payload.get("summary")
    if not isinstance(summary, list):
        raise FigureBuildError("aggregate has no summary array")
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in summary:
        if not isinstance(raw, dict):
            continue
        key = (str(raw.get("task_profile")), str(raw.get("dataset")))
        if key[0] not in PROFILES or key[1] not in DATASETS:
            continue
        if key in rows:
            raise FigureBuildError(f"duplicate aggregate row: {key}")
        for field in ("ind_ap_mean", "ind_ap_std", "n_seeds"):
            value = raw.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise FigureBuildError(f"invalid {field} in aggregate row {key}")
            if not math.isfinite(float(value)):
                raise FigureBuildError(f"non-finite {field} in aggregate row {key}")
        rows[key] = raw
    expected = {(profile, dataset) for profile in PROFILES for dataset in DATASETS}
    if set(rows) != expected:
        raise FigureBuildError(f"aggregate coverage mismatch: {sorted(expected - set(rows))}")
    seed_counts = {int(row["n_seeds"]) for row in rows.values()}
    if len(seed_counts) != 1:
        raise FigureBuildError("registered arms do not share one seed count")
    return rows


def _save_monochrome(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    preview = BytesIO()
    fig.savefig(
        preview,
        format="png",
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
        metadata={"Software": "temporal-link-decoupling"},
    )
    preview.seek(0)
    image = mpimg.imread(preview, format="png")
    spread = abs(image[..., :3].max(axis=2) - image[..., :3].min(axis=2)).max()
    if float(spread) > 1e-6:
        raise FigureBuildError(f"figure is not monochrome: {path}")
    fig.savefig(
        path,
        format="pdf",
        bbox_inches="tight",
        facecolor="white",
        metadata={
            "Creator": "temporal-link-decoupling",
            "Producer": "matplotlib",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    plt.close(fig)


def _protocol_figure(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")

    boxes = (
        (0.2, 1.45, 2.0, 1.1, "Registered\nevent stream", "white"),
        (3.0, 2.55, 2.4, 0.9, "Coupled\nbackbone", "0.82"),
        (3.0, 0.55, 2.4, 0.9, "Decoupled\nbackbone", "white"),
        (6.3, 2.55, 2.4, 0.9, "Prediction loss\nupdates backbone", "0.82"),
        (6.3, 0.55, 2.4, 0.9, "Prediction gradient\nstops at boundary", "white"),
    )
    for x, y, width, height, label, shade in boxes:
        patch = FancyBboxPatch(
            (x, y), width, height,
            boxstyle="round,pad=0.04,rounding_size=0.06",
            linewidth=1.3, edgecolor="black", facecolor=shade,
        )
        ax.add_patch(patch)
        ax.text(x + width / 2, y + height / 2, label, ha="center", va="center", fontsize=10)

    arrows = (((2.2, 2.0), (3.0, 3.0)), ((2.2, 2.0), (3.0, 1.0)),
              ((5.4, 3.0), (6.3, 3.0)), ((5.4, 1.0), (6.3, 1.0)))
    for start, end in arrows:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="->", mutation_scale=13,
                                     linewidth=1.2, color="black"))
    ax.text(5.0, 3.75, "Shared data, split, schedule, and evaluation",
            ha="center", va="center", fontsize=10, fontweight="bold")
    _save_monochrome(fig, path)


def _ordering_figure(rows: dict[tuple[str, str], dict[str, Any]], path: Path) -> None:
    labels = ("CoEdit", "MOOC", "Wikipedia")
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    for offset, (dataset, label) in enumerate(zip(DATASETS, labels)):
        coupled = float(rows[("coupled-end-to-end", dataset)]["ind_ap_mean"])
        decoupled = float(rows[("decoupled", dataset)]["ind_ap_mean"])
        ax.plot([coupled, decoupled], [offset, offset], color="0.45", linewidth=1.5, zorder=1)
        ax.scatter(coupled, offset, marker="s", s=70, facecolor="white",
                   edgecolor="black", linewidth=1.2, label="Coupled" if offset == 0 else None,
                   zorder=2)
        ax.scatter(decoupled, offset, marker="o", s=70, facecolor="black",
                   edgecolor="black", linewidth=1.2, label="Decoupled" if offset == 0 else None,
                   zorder=3)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xticks([])
    ax.set_xlabel("Lower  ←  inductive average precision  →  Higher")
    ax.set_title("Registered mean ordering across current corpora", fontweight="bold")
    ax.grid(False)
    for spine in ("top", "right", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.legend(frameon=False, loc="lower right", ncol=2)
    _save_monochrome(fig, path)


def generate(artifact: Path, output_dir: Path) -> list[Path]:
    rows = _load_rows(artifact)
    outputs = [output_dir / "protocol-contrast.pdf", output_dir / "inductive-ordering.pdf"]
    _protocol_figure(outputs[0])
    _ordering_figure(rows, outputs[1])
    return outputs


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact",
        type=Path,
        default=ROOT / "results/frozen/LP-REL-2026-A003-001/payload/results/audit/scientific-matrix.json",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    for output in generate(args.artifact.resolve(), args.output_dir.resolve()):
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
