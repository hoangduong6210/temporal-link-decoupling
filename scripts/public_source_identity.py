#!/usr/bin/env python3
"""Resolve private-monorepo commit IDs to public projection commits."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any


HEX40 = re.compile(r"[0-9a-f]{40}")
MAP_PATH = Path("evidence/export/COMMIT-EQUIVALENCE.json")
POLICY_PATH = Path("evidence/export/PUBLIC-HISTORY-POLICY.toml")


class SourceIdentityError(RuntimeError):
    """The declared source identity cannot be verified in this checkout."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _commit_exists(root: Path, commit: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def _load_map(root: Path) -> dict[str, Any]:
    map_path = root / MAP_PATH
    policy_path = root / POLICY_PATH
    try:
        payload = json.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SourceIdentityError(f"invalid public source map: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise SourceIdentityError("unsupported public source map schema")
    if payload.get("policy_sha256") != _sha256(policy_path):
        raise SourceIdentityError("public history policy checksum mismatch")
    commits = payload.get("commits")
    if not isinstance(commits, dict):
        raise SourceIdentityError("public source map has no commit mapping")
    return payload


def resolve_commit(root: Path, commit: str) -> str:
    """Return a locally resolvable commit for an original or public identity."""
    if HEX40.fullmatch(commit) is None:
        raise SourceIdentityError(f"source commit is not full 40-hex: {commit}")
    if _commit_exists(root, commit):
        return commit
    payload = _load_map(root)
    record = payload["commits"].get(commit)
    if not isinstance(record, dict):
        raise SourceIdentityError(f"source commit is absent and unmapped: {commit}")
    mapped = record.get("public_commit")
    if (
        not isinstance(mapped, str)
        or HEX40.fullmatch(mapped) is None
        or record.get("relation") != "EXACT_PUBLIC_ALLOWLIST_PROJECTION"
        or not _commit_exists(root, mapped)
    ):
        raise SourceIdentityError(f"invalid public mapping for source commit: {commit}")
    return mapped


def git_blob(root: Path, commit: str, project_relative: str) -> bytes:
    """Read a project blob at an original or mapped public commit."""
    mapped = resolve_commit(root, commit)
    git_root_result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if git_root_result.returncode != 0:
        raise SourceIdentityError("cannot resolve git repository root")
    git_root = Path(git_root_result.stdout.strip()).resolve()
    if mapped == commit:
        prefix = root.resolve().relative_to(git_root)
        repository_path = (prefix / project_relative).as_posix()
    else:
        repository_path = project_relative
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{mapped}:{repository_path}"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SourceIdentityError(
            f"source is absent from declared commit: {project_relative}"
        )
    return result.stdout


def tree_matches_head(root: Path, commit: str, project_relative: str) -> bool:
    """Return whether a project subtree is unchanged from the declared commit."""
    try:
        mapped = resolve_commit(root, commit)
    except SourceIdentityError:
        return False
    git_root_result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if git_root_result.returncode != 0:
        return False
    git_root = Path(git_root_result.stdout.strip()).resolve()
    if mapped == commit:
        path = (root.resolve().relative_to(git_root) / project_relative).as_posix()
    else:
        path = project_relative
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", mapped, "HEAD", "--", f":(top){path}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    changed = {item for item in result.stdout.splitlines() if item}
    if not changed:
        return True
    if mapped == commit:
        return False
    try:
        overlays = set(_load_map(root).get("allowed_public_overlays", []))
    except SourceIdentityError:
        return False
    return changed <= overlays
