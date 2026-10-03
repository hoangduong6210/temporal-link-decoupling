"""Verify and attest the isolated, hash-installed prospective CPU runtime on Slurm."""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import socket
import subprocess
import sys
import sysconfig


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "configs/prospective-requirements-py39-cpu.lock"


class RuntimeVerificationError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise RuntimeVerificationError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest_rows(rows):
    return hashlib.sha256(json.dumps(sorted(rows), separators=(",", ":")).encode()).hexdigest()


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def locked_packages(text):
    """Only the concrete, single-platform generated lock format is accepted."""
    result, current, hashes = {}, None, 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("--index-url ") or line.startswith("--extra-index-url "):
            continue
        if line.startswith("--hash=sha256:"):
            require(current is not None and re.fullmatch(r"--hash=sha256:[a-f0-9]{64}(?:\s+\\)?", line), "invalid artifact hash")
            hashes += 1
            continue
        require(current is None or hashes > 0, "unhashed dependency")
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s;]+)\s+\\", line)
        require(match is not None, "lock must contain concrete hashed exact pins")
        name, version = normalize(match[1]), match[2]
        require(name not in result, "duplicate dependency pin")
        result[name], current, hashes = version, name, 0
    require(result and hashes > 0, "empty or unhashed dependency lock")
    return result


def verify_record(site, prefix, record_text):
    """Check installed RECORD hashes and bind every listed installed file."""
    rows = []
    for relative, encoded, size in csv.reader(record_text.splitlines()):
        path = (site / relative).resolve()
        require(path.is_relative_to(prefix), "distribution file escapes isolated environment")
        require(path.is_file(), "missing installed distribution file")
        digest = sha(path)
        if encoded:
            algorithm, value = encoded.split("=", 1)
            require(algorithm == "sha256", "unsupported RECORD hash")
            expected = base64.urlsafe_b64encode(bytes.fromhex(digest)).decode().rstrip("=")
            require(value == expected, "installed distribution payload differs from RECORD")
        else:
            require(path.name == "RECORD" or path.suffix == ".pyc", "unexpected unhashed installed payload")
        if size:
            require(path.stat().st_size == int(size), "installed distribution size differs from RECORD")
        if path.suffix != ".pyc":
            rows.append([path.relative_to(prefix).as_posix(), digest])
    require(rows, "empty distribution RECORD")
    return rows


def attest(lock=LOCK):
    require(sys.prefix != sys.base_prefix, "requires an isolated virtual environment")
    prefix = Path(sys.prefix).resolve()
    cfg = (prefix / "pyvenv.cfg").read_text().lower()
    require(re.search(r"include-system-site-packages\s*=\s*false", cfg), "system site-packages must be disabled")
    require(platform.python_version() == "3.9.21", "requires registered CPython patch version")
    require(platform.python_implementation() == "CPython" and platform.machine() == "x86_64", "unsupported interpreter/platform")
    expected = locked_packages(lock.read_text())
    packages, payload = {}, []
    for dist in importlib.metadata.distributions():
        name = normalize(dist.metadata["Name"])
        require(name not in packages, "duplicate installed distribution")
        require(expected.get(name) == dist.version, "unexpected package or package version: " + name)
        site = Path(dist.locate_file("")).resolve()
        require(site.is_relative_to(prefix), "ambient distribution outside isolated environment")
        record = dist.read_text("RECORD")
        require(record is not None, "distribution has no installed RECORD")
        records = verify_record(site, prefix, record)
        packages[name] = {"version": dist.version, "file_count": len(records), "payload_sha256": digest_rows(records)}
        payload.extend(records)
    require(set(packages) == set(expected), "missing locked distribution")

    # Bind Python's base installation separately from its wheel packages. Ignore
    # bytecode and ambient site-packages, neither of which is the stdlib payload.
    standard = Path(sysconfig.get_path("stdlib")).resolve()
    standard_rows = []
    for folder, directories, files in os.walk(standard):
        directories[:] = sorted(d for d in directories if d not in {"site-packages", "__pycache__"})
        for name in sorted(files):
            path = Path(folder) / name
            if path.suffix in {".py", ".so"}:
                standard_rows.append([path.relative_to(standard).as_posix(), sha(path)])
    library = Path(sysconfig.get_config_var("LIBDIR")) / sysconfig.get_config_var("LDLIBRARY")
    require(library.is_file() and standard_rows, "missing Python base installation payload")
    import numpy as np
    import torch
    require(torch.__version__ == "2.8.0+cpu" and torch.version.cuda is None, "requires the registered CPU torch build")
    return {
        "kind": "prospective-cpu-runtime-attestation", "schema_version": 1,
        "lock_sha256": sha(lock), "python_version": platform.python_version(),
        "implementation": platform.python_implementation(), "abi": sysconfig.get_config_var("SOABI"),
        "machine": platform.machine(), "libc": list(platform.libc_ver()),
        "python_executable_sha256": sha(Path(sys.executable).resolve()),
        "python_library_sha256": sha(library), "stdlib_sha256": digest_rows(standard_rows),
        "stdlib_files": len(standard_rows), "isolated": True, "packages": packages,
        "installed_payload_sha256": digest_rows(payload),
        "numpy_version": np.__version__, "torch_version": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "boundary": "Wheel hashes checked at installation; installed RECORD and base Python payload checked here. This is not a container or a promise of bitwise equality across CPU hardware.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=LOCK)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expect", type=Path)
    args = parser.parse_args()
    require(os.environ.get("SLURM_JOB_ID", "").isdigit() and "login" not in socket.gethostname().lower(), "runtime hashing requires Slurm compute allocation")
    result = attest(args.lock)
    if args.expect:
        reference = json.loads(args.expect.read_text())
        require(reference["runtime"] == result, "runtime differs from the registered installed environment")
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    report = {"runtime": result, "source_commit": source, "job_id": os.environ["SLURM_JOB_ID"],
              "source_clean": not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip(),
              "verifier_sha256": sha(__file__)}
    if args.output:
        with args.output.open("x") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
    print("PASS: isolated prospective CPU runtime, exact package pins and installed payload; " + result["installed_payload_sha256"])


if __name__ == "__main__":
    main()
