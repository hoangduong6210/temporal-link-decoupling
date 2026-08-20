"""Deterministic artifact helpers used by the explicit dataset builders."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Mapping
import hashlib
import zipfile

import numpy as np


_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest for ``path``."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_npz_deterministic(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    """Write a byte-stable, uncompressed NPZ with fixed ZIP metadata.

    NumPy's array encoding is pinned to NPY v1.0 and pickle is forbidden.  The
    member order follows the mapping insertion order supplied by the caller.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with zipfile.ZipFile(temporary, mode="w", compression=zipfile.ZIP_STORED) as archive:
        for name, array in arrays.items():
            buffer = BytesIO()
            np.lib.format.write_array(
                buffer,
                np.ascontiguousarray(array),
                version=(1, 0),
                allow_pickle=False,
            )
            member = zipfile.ZipInfo(f"{name}.npy", date_time=_ZIP_EPOCH)
            member.compress_type = zipfile.ZIP_STORED
            member.create_system = 3
            member.external_attr = 0o100644 << 16
            archive.writestr(member, buffer.getvalue())
    temporary.replace(path)
