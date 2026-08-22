#!/usr/bin/env python3
"""Fail-closed checks for the standalone public Git object graph."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
BANNED_PATH = re.compile(
    r"^(?:AGENTS\.md|docs/MIGRATION\.md|evidence/audits/|figures/|"
    r"paper/(?:figs|working)/|results/(?:audit|historical)/|resources/corpora/|"
    r"paper/snapshots/LP-SNAP-2026-CONFERENCE-00[12]/)"
)
BANNED_SUFFIX = {".docx", ".zip", ".pyc", ".log", ".out"}
ALLOWED_OVERLEAF_ZIP = re.compile(
    r"^paper/(?:candidate/link-prediction-overleaf\.zip|"
    r"author-submission/Link_Predict_Overleaf\.zip|"
    r"conference/Link_Predict_Overleaf\.zip|"
    r"snapshots/LP-SNAP-[A-Z0-9-]+/link-prediction-overleaf\.zip)$"
)
RETIRED_HEAD_PREFIXES = (
    "paper/author-submission/",
    "paper/candidate/",
    "paper/snapshots/LP-SNAP-",
)
PRIVATE_TEXT = re.compile(
    rb"/(?:users|home|private|scratch)/|ghp_[A-Za-z0-9]{20,}|"
    rb"binben14@ascend-rw01\.ten\.osc\.edu"
)
PUBLIC_EMAIL = "Hoangduong4316@icloud.com"


def _git(*args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        text=text,
        capture_output=True,
        check=True,
    )
    return result.stdout


def verify() -> dict[str, object]:
    issues: list[str] = []
    commits = str(_git("rev-list", "HEAD")).splitlines()
    objects = str(_git("rev-list", "--objects", "HEAD")).splitlines()
    paths: list[str] = []
    blob_ids: set[str] = set()
    for entry in objects:
        object_id, separator, path = entry.partition(" ")
        if not separator or not path:
            continue
        paths.append(path)
        banned_suffix = Path(path).suffix.lower() in BANNED_SUFFIX
        if Path(path).suffix.lower() == ".zip" and ALLOWED_OVERLEAF_ZIP.fullmatch(path):
            banned_suffix = False
        if BANNED_PATH.search(path) or banned_suffix:
            issues.append(f"publication-excluded path is reachable: {path}")
        if str(_git("cat-file", "-t", object_id)).strip() == "blob":
            blob_ids.add(object_id)

    head_paths = str(_git("ls-tree", "-r", "--name-only", "HEAD")).splitlines()
    for path in head_paths:
        if path.startswith(RETIRED_HEAD_PREFIXES):
            issues.append(f"retired paper version remains in HEAD: {path}")

    for commit in commits:
        identity = str(_git("show", "-s", "--format=%ae%n%ce", commit)).splitlines()
        if any(email != PUBLIC_EMAIL for email in identity):
            issues.append(f"non-public commit email: {commit}")
        tree = bytes(_git("ls-tree", "-rz", commit, text=False))
        for entry in tree.split(b"\0"):
            if not entry or b"\t" not in entry:
                continue
            metadata, raw_path = entry.split(b"\t", 1)
            if metadata.split(b" ", 1)[0] != b"120000":
                continue
            path = raw_path.decode("utf-8", errors="surrogateescape")
            target = str(_git("show", f"{commit}:{path}")).strip()
            if target.startswith("/") or ".." in Path(target).parts:
                issues.append(f"unsafe symlink target: {commit}:{path}")

    for object_id in blob_ids:
        size = int(str(_git("cat-file", "-s", object_id)).strip())
        if size > 4 * 1024 * 1024:
            issues.append(f"oversized public blob: {object_id}")
            continue
        content = bytes(_git("cat-file", "blob", object_id, text=False))
        if PRIVATE_TEXT.search(content):
            issues.append(f"private path, email, or credential pattern in blob: {object_id}")

    mapping = json.loads(
        (ROOT / "evidence/export/COMMIT-EQUIVALENCE.json").read_text(encoding="utf-8")
    )
    for original, record in mapping["commits"].items():
        if subprocess.run(
            ["git", "-C", str(ROOT), "cat-file", "-e", f"{original}^{{commit}}"],
            capture_output=True,
            check=False,
        ).returncode == 0:
            issues.append(f"original monorepo commit is reachable: {original}")
        mapped = record.get("public_commit", "") if isinstance(record, dict) else ""
        if subprocess.run(
            ["git", "-C", str(ROOT), "cat-file", "-e", f"{mapped}^{{commit}}"],
            capture_output=True,
            check=False,
        ).returncode != 0:
            issues.append(f"mapped public commit is unavailable: {original}")

    git_dir = Path(str(_git("rev-parse", "--git-dir")).strip())
    if not git_dir.is_absolute():
        git_dir = ROOT / git_dir
    if (git_dir / "objects/info/alternates").exists():
        issues.append("Git object store uses alternates")
    fsck = subprocess.run(
        ["git", "-C", str(ROOT), "fsck", "--full", "--strict", "--no-reflogs"],
        text=True,
        capture_output=True,
        check=False,
    )
    if fsck.returncode != 0:
        issues.append("Git object graph fails strict fsck")

    return {
        "schema_version": 1,
        "status": "PASS" if not issues else "FAIL",
        "reachable_commits": len(commits),
        "reachable_paths": len(paths),
        "issues": issues,
    }


def main() -> int:
    result = verify()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
