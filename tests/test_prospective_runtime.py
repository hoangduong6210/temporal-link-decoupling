import base64
import hashlib

import pytest

from scripts.check_prospective_runtime import (
    RuntimeVerificationError, installed_distributions, locked_packages, verify_record,
)


def test_runtime_lock_rejects_unhashed_unpinned_and_duplicate_requirements():
    valid = "Demo_Pkg==1.2 \\\n    --hash=sha256:" + "a" * 64 + "\n"
    assert locked_packages(valid) == {"demo-pkg": "1.2"}
    for bad in ["", "demo>=1.2", "demo==1.2 \\\n", valid + valid,
                "demo==1.2; python_version>'3' \\\n    --hash=sha256:" + "a" * 64]:
        with pytest.raises(RuntimeVerificationError):
            locked_packages(bad)


def test_installed_record_rejects_modified_payload_and_external_paths(tmp_path):
    site = tmp_path / "lib"
    site.mkdir()
    path = site / "module.py"
    path.write_bytes(b"original")
    value = base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).decode().rstrip("=")
    record = "module.py,sha256=" + value + ",8\n"
    rows = verify_record(site, tmp_path, record)
    assert rows[0][0] == "lib/module.py"
    path.write_bytes(b"modified")
    with pytest.raises(RuntimeVerificationError, match="differs"):
        verify_record(site, tmp_path, record)
    with pytest.raises(RuntimeVerificationError, match="escapes"):
        verify_record(site, tmp_path, "../../outside.py,,\n")
    with pytest.raises(RuntimeVerificationError, match="unhashed"):
        verify_record(site, tmp_path, "module.py,,8\n")


def test_runtime_deduplicates_directory_aliases_but_preserves_distinct_installs(tmp_path):
    for name in ["lib", "other"]:
        metadata = tmp_path / name / "demo-1.0.dist-info"
        metadata.mkdir(parents=True)
        (metadata / "METADATA").write_text("Name: demo\nVersion: 1.0\n")
    (tmp_path / "lib64").symlink_to(tmp_path / "lib", target_is_directory=True)
    assert len(list(installed_distributions([tmp_path / "lib", tmp_path / "lib64"]))) == 1
    assert len(list(installed_distributions([tmp_path / "lib", tmp_path / "other"]))) == 2
