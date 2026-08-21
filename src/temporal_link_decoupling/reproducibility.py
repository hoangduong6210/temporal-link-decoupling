"""Reproducibility primitives shared by the scientific runners.

This module deliberately does not decide whether an artifact is admissible
evidence.  It records enough resolved state for the repository provenance gate
to make that decision without relying on CLI defaults or human-written prose.
"""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import subprocess
import sys
import tempfile
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence, Union

import numpy as np
import torch

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    try:
        import tomli as tomllib
    except ModuleNotFoundError:  # Local pre-install compatibility only.
        import toml as tomllib


STRICT_CUBLAS_WORKSPACE = ":4096:8"
SUPPORTED_DETERMINISM_MODES = {"strict", "warn", "off"}


def utc_now() -> str:
    """Return an RFC-3339 UTC timestamp with second precision."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def sha256_file(path: Path) -> str:
    """Hash one regular file without loading it into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _project_file(project_root: Path, value: Union[str, Path], label: str) -> Path:
    root = project_root.resolve()
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"{label} must remain inside the project root: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"Missing {label}: {path}")
    return path


def _unique(values: Iterable[Any], label: str) -> tuple[Any, ...]:
    resolved = tuple(values)
    if not resolved:
        raise ValueError(f"{label} must not be empty")
    if len(set(resolved)) != len(resolved):
        raise ValueError(f"{label} contains duplicates: {resolved}")
    return resolved


def parse_chronological_split(value: str) -> tuple[float, float, float]:
    """Parse the canonical ``chronological-70-15-15`` split notation."""

    prefix = "chronological-"
    if not value.startswith(prefix):
        raise ValueError(f"Unsupported split {value!r}; expected {prefix}<train>-<val>-<test>")
    pieces = value[len(prefix):].split("-")
    if len(pieces) != 3 or any(not piece.isdigit() for piece in pieces):
        raise ValueError(f"Malformed chronological split: {value!r}")
    percentages = tuple(int(piece) for piece in pieces)
    if any(part <= 0 for part in percentages) or sum(percentages) != 100:
        raise ValueError(f"Split percentages must be positive and sum to 100: {value!r}")
    return tuple(part / 100.0 for part in percentages)  # type: ignore[return-value]


@dataclass(frozen=True)
class ResolvedRunConfig:
    """Fully resolved protocol/config values consumed by a runner."""

    protocol_id: str
    protocol_status: str
    protocol_path: str
    protocol_sha256: str
    config_path: str
    config_sha256: str
    dependency_lock_path: str
    dependency_lock_sha256: str
    datasets: tuple[str, ...]
    seeds: tuple[int, ...]
    split: str
    train_ratio: float
    validation_ratio: float
    test_ratio: float
    epochs: int
    hidden: int
    batch_size: int
    learning_rate: float
    optimizer: str
    weight_decay: float
    scheduler: str
    determinism: str
    python_hash_seed: int
    cublas_workspace_config: str
    warmup_policy: str
    finite_policy: str
    node_memory_collision_semantics: str
    causal_batch_scope: str
    disjoint_bipartite_datasets: tuple[str, ...]
    homogeneous_shared_node_space_datasets: tuple[str, ...]
    protocol_conformant: bool
    deviations: tuple[str, ...]

    def as_metadata(self) -> dict[str, Any]:
        return asdict(self)


def resolve_run_config(
    project_root: Path,
    *,
    config_path: Union[str, Path] = "configs/default.toml",
    protocol_path: Union[str, Path] = "protocols/link_prediction_v1.toml",
    datasets: Optional[Sequence[str]] = None,
    seeds: Optional[Sequence[int]] = None,
    epochs: Optional[int] = None,
    hidden: Optional[int] = None,
    batch_size: Optional[int] = None,
    learning_rate: Optional[float] = None,
    determinism: Optional[str] = None,
) -> ResolvedRunConfig:
    """Resolve defaults from tracked files and make every deviation explicit.

    The config is an executable default profile.  The protocol is the authority
    against which that profile is checked.  Dataset/seed subsets are conformant
    scheduler tasks; changing training or determinism values is recorded as a
    protocol deviation rather than silently changing the study.
    """

    root = project_root.resolve()
    config_file = _project_file(root, config_path, "configuration")
    protocol_file = _project_file(root, protocol_path, "protocol")
    config = _load_toml(config_file)
    protocol = _load_toml(protocol_file)

    protocol_study = protocol.get("study", {})
    config_study = config.get("study", {})
    protocol_training = protocol.get("training", {})
    config_training = config.get("training", {})
    protocol_optimizer = protocol.get("optimizer", {})
    config_optimizer = config.get("optimizer", {})
    protocol_repro = protocol.get("reproducibility", {})
    config_repro = config.get("reproducibility", {})
    protocol_topology = protocol.get("dataset_topology", {})
    protocol_identity = {
        "finite_policy": protocol_repro.get("finite_policy"),
        "node_memory_collision_semantics": protocol_repro.get(
            "node_memory_collision_semantics"
        ),
        "causal_batch_scope": protocol_repro.get("causal_batch_scope"),
        "disjoint_bipartite_datasets": protocol_topology.get("disjoint_bipartite"),
        "homogeneous_shared_node_space_datasets": protocol_topology.get(
            "homogeneous_shared_node_space"
        ),
    }
    missing_identity = sorted(
        key for key, value in protocol_identity.items() if value in (None, "")
    )
    if missing_identity:
        raise ValueError(f"Protocol is missing execution semantics: {missing_identity}")

    authoritative = {
        "datasets": tuple(protocol_study.get("datasets", protocol.get("datasets", ()))),
        "seeds": tuple(protocol_study.get("seeds", ())),
        "split": protocol_study.get("split"),
        "epochs": protocol_training.get("epochs"),
        "hidden": protocol_training.get("hidden"),
        "batch_size": protocol_training.get("batch_size"),
        "learning_rate": protocol_training.get("learning_rate"),
        "optimizer": protocol_optimizer.get("name"),
        "weight_decay": protocol_optimizer.get("weight_decay"),
        "scheduler": protocol_optimizer.get("scheduler"),
        "determinism": protocol_repro.get("determinism"),
        "python_hash_seed": protocol_repro.get("python_hash_seed"),
        "cublas_workspace_config": protocol_repro.get("cublas_workspace_config"),
        "warmup_policy": protocol_repro.get("warmup_policy"),
        "dependency_lock": protocol_repro.get("dependency_lock"),
        "dependency_lock_sha256": protocol_repro.get("dependency_lock_sha256"),
    }
    profile = {
        "datasets": tuple(config_study.get("datasets", ())),
        "seeds": tuple(config_study.get("seeds", ())),
        "split": config_study.get("split"),
        "epochs": config_training.get("epochs"),
        "hidden": config_training.get("hidden"),
        "batch_size": config_training.get("batch_size"),
        "learning_rate": config_training.get("learning_rate"),
        "optimizer": config_optimizer.get("name"),
        "weight_decay": config_optimizer.get("weight_decay"),
        "scheduler": config_optimizer.get("scheduler"),
        "determinism": config_repro.get("determinism"),
        "python_hash_seed": config_repro.get("python_hash_seed"),
        "cublas_workspace_config": config_repro.get("cublas_workspace_config"),
        "warmup_policy": config_repro.get("warmup_policy"),
        "dependency_lock": config_repro.get("dependency_lock"),
        "dependency_lock_sha256": config_repro.get("dependency_lock_sha256"),
    }
    missing = sorted(key for key, value in authoritative.items() if value in (None, (), ""))
    if missing:
        raise ValueError(f"Protocol is missing required runner fields: {missing}")
    if tuple(protocol.get("datasets", ())) != authoritative["datasets"]:
        raise ValueError("Protocol top-level datasets drift from [study].datasets")
    if tuple(protocol.get("seeds", ())) != authoritative["seeds"]:
        raise ValueError("Protocol top-level seeds drift from [study].seeds")
    drift = sorted(key for key in authoritative if profile[key] != authoritative[key])
    if drift:
        raise ValueError(f"Configuration/profile drift from protocol: {drift}")

    dependency_lock = _project_file(
        root, str(authoritative["dependency_lock"]), "scientific dependency lock"
    )
    expected_lock_hash = str(authoritative["dependency_lock_sha256"])
    actual_lock_hash = sha256_file(dependency_lock)
    if re.fullmatch(r"[0-9a-f]{64}", expected_lock_hash) is None:
        raise ValueError("Scientific dependency lock SHA-256 is malformed")
    if actual_lock_hash != expected_lock_hash:
        raise ValueError(
            f"Scientific dependency lock checksum mismatch: expected "
            f"{expected_lock_hash}, got {actual_lock_hash}"
        )

    allowed_datasets = _unique((str(item) for item in authoritative["datasets"]), "datasets")
    disjoint_datasets = _unique(
        (str(item) for item in protocol_identity["disjoint_bipartite_datasets"]),
        "disjoint bipartite datasets",
    )
    homogeneous_datasets = _unique(
        (
            str(item)
            for item in protocol_identity["homogeneous_shared_node_space_datasets"]
        ),
        "homogeneous shared-node-space datasets",
    )
    if set(disjoint_datasets).intersection(homogeneous_datasets):
        raise ValueError("Dataset topology classes overlap")
    if set(disjoint_datasets).union(homogeneous_datasets) != set(allowed_datasets):
        raise ValueError("Dataset topology classes do not partition the protocol datasets")
    manifest = _load_toml(root / "resources/manifest.toml")
    manifest_topology = {
        Path(str(item.get("path", ""))).stem: str(item.get("topology", ""))
        for item in manifest.get("dataset", [])
        if str(item.get("state", "")).startswith("CURRENT")
    }
    expected_topology = {
        **{name: "disjoint-bipartite" for name in disjoint_datasets},
        **{name: "homogeneous-shared-node-space" for name in homogeneous_datasets},
    }
    if manifest_topology != expected_topology:
        raise ValueError("Current resource manifest topology drifts from the protocol")
    allowed_seeds = _unique((int(item) for item in authoritative["seeds"]), "seeds")
    selected_datasets = _unique(
        (str(item) for item in (datasets if datasets is not None else allowed_datasets)),
        "selected datasets",
    )
    selected_seeds = _unique(
        (int(item) for item in (seeds if seeds is not None else allowed_seeds)),
        "selected seeds",
    )
    unsupported_datasets = sorted(set(selected_datasets) - set(allowed_datasets))
    unsupported_seeds = sorted(set(selected_seeds) - set(allowed_seeds))
    if unsupported_datasets:
        raise ValueError(f"Datasets outside {protocol.get('protocol_id')}: {unsupported_datasets}")
    if unsupported_seeds:
        raise ValueError(f"Seeds outside {protocol.get('protocol_id')}: {unsupported_seeds}")

    split = str(authoritative["split"])
    train_ratio, validation_ratio, test_ratio = parse_chronological_split(split)
    resolved_values = {
        "epochs": int(epochs if epochs is not None else authoritative["epochs"]),
        "hidden": int(hidden if hidden is not None else authoritative["hidden"]),
        "batch_size": int(
            batch_size if batch_size is not None else authoritative["batch_size"]
        ),
        "learning_rate": float(
            learning_rate
            if learning_rate is not None
            else authoritative["learning_rate"]
        ),
        "determinism": str(
            determinism if determinism is not None else authoritative["determinism"]
        ),
    }
    if resolved_values["epochs"] <= 0 or resolved_values["hidden"] <= 0:
        raise ValueError("epochs and hidden must be positive")
    if resolved_values["batch_size"] <= 0 or resolved_values["learning_rate"] <= 0:
        raise ValueError("batch_size and learning_rate must be positive")
    if resolved_values["determinism"] not in SUPPORTED_DETERMINISM_MODES:
        raise ValueError(f"Unsupported determinism policy: {resolved_values['determinism']!r}")

    deviations = tuple(
        key
        for key in ("epochs", "hidden", "batch_size", "learning_rate", "determinism")
        if resolved_values[key] != authoritative[key]
    )
    relative = lambda path: path.relative_to(root).as_posix()
    return ResolvedRunConfig(
        protocol_id=str(protocol["protocol_id"]),
        protocol_status=str(protocol["status"]),
        protocol_path=relative(protocol_file),
        protocol_sha256=sha256_file(protocol_file),
        config_path=relative(config_file),
        config_sha256=sha256_file(config_file),
        dependency_lock_path=relative(dependency_lock),
        dependency_lock_sha256=actual_lock_hash,
        datasets=tuple(str(item) for item in selected_datasets),
        seeds=tuple(int(item) for item in selected_seeds),
        split=split,
        train_ratio=train_ratio,
        validation_ratio=validation_ratio,
        test_ratio=test_ratio,
        epochs=int(resolved_values["epochs"]),
        hidden=int(resolved_values["hidden"]),
        batch_size=int(resolved_values["batch_size"]),
        learning_rate=float(resolved_values["learning_rate"]),
        optimizer=str(authoritative["optimizer"]),
        weight_decay=float(authoritative["weight_decay"]),
        scheduler=str(authoritative["scheduler"]),
        determinism=str(resolved_values["determinism"]),
        python_hash_seed=int(authoritative["python_hash_seed"]),
        cublas_workspace_config=str(authoritative["cublas_workspace_config"]),
        warmup_policy=str(authoritative["warmup_policy"]),
        finite_policy=str(protocol_identity["finite_policy"]),
        node_memory_collision_semantics=str(
            protocol_identity["node_memory_collision_semantics"]
        ),
        causal_batch_scope=str(protocol_identity["causal_batch_scope"]),
        disjoint_bipartite_datasets=tuple(disjoint_datasets),
        homogeneous_shared_node_space_datasets=tuple(homogeneous_datasets),
        protocol_conformant=not deviations,
        deviations=deviations,
    )


def validate_task_profile(
    protocol_path: Path,
    *,
    task_id: Optional[str],
    runner: str,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate runner-specific arguments against a checksum-owned task profile."""

    profiles = _load_toml(protocol_path).get("task_profiles", {})
    errors: list[str] = []
    profile: Mapping[str, Any] = {}
    if not task_id:
        errors.append("task_id is missing")
    elif task_id not in profiles:
        errors.append(f"unknown task_id: {task_id}")
    else:
        profile = profiles[task_id]
        if profile.get("runner") != runner:
            errors.append(
                f"task profile runner is {profile.get('runner')!r}, expected {runner!r}"
            )

    mismatches: list[dict[str, Any]] = []
    if profile and runner == "run_model":
        expected_parameters = profile.get("parameters", {})
        for field, expected in expected_parameters.items():
            actual = arguments.get(field)
            normalized_actual = "UNSET" if actual is None else actual
            if normalized_actual != expected:
                mismatches.append({
                    "field": field,
                    "expected": expected,
                    "actual": normalized_actual,
                })
    elif profile and runner == "run_baselines":
        raw_models = arguments.get("models", ())
        models = (
            [item.strip() for item in str(raw_models).split(",") if item.strip()]
            if isinstance(raw_models, str)
            else [str(item) for item in raw_models]
        )
        allowed = [str(item) for item in profile.get("allowed_models", ())]
        if not models:
            errors.append("baseline model selection is empty")
        if len(models) != len(set(models)):
            errors.append("baseline model selection contains duplicates")
        unknown = sorted(set(models) - set(allowed))
        if unknown:
            errors.append(f"baseline models outside registry: {unknown}")
        if not profile.get("allow_model_subsets", False) and models != allowed:
            mismatches.append({"field": "models", "expected": allowed, "actual": models})

    return {
        "task_id": task_id or "MISSING",
        "runner": runner,
        "profile_found": bool(profile),
        "valid": bool(profile) and not errors and not mismatches,
        "scientific_matrix_eligible": bool(
            profile.get("scientific_matrix_eligible", True)
        ) if profile else False,
        "errors": errors,
        "mismatches": mismatches,
    }


def seed_everything(seed: int) -> None:
    """Seed all RNGs used by the runner."""

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def configure_determinism(
    mode: str,
    *,
    python_hash_seed: int,
    cublas_workspace_config: str = STRICT_CUBLAS_WORKSPACE,
) -> dict[str, Any]:
    """Apply and report the requested deterministic execution policy.

    Process-start variables cannot be made effective after Python/CUDA startup.
    Strict mode therefore refuses to run when they are absent instead of
    pretending that assigning them here would make the process deterministic.
    """

    if mode not in SUPPORTED_DETERMINISM_MODES:
        raise ValueError(f"Unsupported determinism policy: {mode!r}")
    warnings: list[str] = []
    expected_hash_seed = str(python_hash_seed)
    if mode != "off" and os.environ.get("PYTHONHASHSEED") != expected_hash_seed:
        warnings.append(f"PYTHONHASHSEED must be {expected_hash_seed} at process start")
    if (
        mode != "off"
        and torch.cuda.is_available()
        and os.environ.get("CUBLAS_WORKSPACE_CONFIG") != cublas_workspace_config
    ):
        warnings.append(
            f"CUBLAS_WORKSPACE_CONFIG must be {cublas_workspace_config} before CUDA startup"
        )
    if mode == "strict" and warnings:
        raise RuntimeError("Strict determinism prerequisites are unmet: " + "; ".join(warnings))

    enabled = mode != "off"
    torch.use_deterministic_algorithms(enabled, warn_only=(mode == "warn"))
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = enabled
        if hasattr(torch.backends.cudnn, "allow_tf32"):
            torch.backends.cudnn.allow_tf32 = False
    if hasattr(torch.backends, "cuda") and hasattr(torch.backends.cuda, "matmul"):
        torch.backends.cuda.matmul.allow_tf32 = False
    return {
        "mode": mode,
        "strict_prerequisites_satisfied": not warnings,
        "warnings": warnings,
        "python_hash_seed": os.environ.get("PYTHONHASHSEED"),
        "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        "torch_deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "cudnn_benchmark": bool(getattr(torch.backends.cudnn, "benchmark", False)),
        "cudnn_deterministic": bool(getattr(torch.backends.cudnn, "deterministic", False)),
    }


def _capture_rng_state() -> dict[str, Any]:
    return {
        "python": random.getstate(),
        "numpy": np.random.get_state(),
        "torch": torch.random.get_rng_state().clone(),
        "cuda": [state.clone() for state in torch.cuda.get_rng_state_all()]
        if torch.cuda.is_available()
        else [],
    }


def _restore_rng_state(state: Mapping[str, Any]) -> None:
    random.setstate(state["python"])
    np.random.set_state(state["numpy"])
    torch.random.set_rng_state(state["torch"])
    if state["cuda"]:
        torch.cuda.set_rng_state_all(state["cuda"])


def state_neutral_optimizer_warmup(
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    run_training_pass: Callable[[], Any],
) -> dict[str, Any]:
    """Warm kernels without retaining a hidden optimizer epoch.

    Model parameters/buffers, optimizer slots and every runner RNG are restored.
    Stateful temporal stores are cleared through ``model.reset()``.  A model that
    creates new state-dict entries during warmup is rejected because restoration
    could not be proven complete.
    """

    model_state = {
        key: value.detach().clone() if isinstance(value, torch.Tensor) else copy.deepcopy(value)
        for key, value in model.state_dict().items()
    }
    optimizer_state = copy.deepcopy(optimizer.state_dict())
    rng_state = _capture_rng_state()
    original_keys = tuple(model_state)
    try:
        run_training_pass()
        if tuple(model.state_dict()) != original_keys:
            raise RuntimeError("Warmup changed the model state schema; neutral restore is unsafe")
    finally:
        if hasattr(model, "reset"):
            model.reset()
        model.load_state_dict(model_state, strict=True)
        optimizer.load_state_dict(optimizer_state)
        _restore_rng_state(rng_state)
    return {
        "policy": "state-neutral-training-pass",
        "retained_optimizer_steps": 0,
        "model_state_restored": True,
        "optimizer_state_restored": True,
        "rng_state_restored": True,
        "temporal_state_reset": hasattr(model, "reset"),
    }


def _run_git(project_root: Path, *args: str) -> Optional[str]:
    result = subprocess.run(
        ["git", "-C", str(project_root), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def capture_source_state(project_root: Path) -> dict[str, Any]:
    commit = _run_git(project_root, "rev-parse", "HEAD")
    status = _run_git(project_root, "status", "--porcelain", "--untracked-files=normal", "--", ".")
    available = commit is not None and status is not None
    return {
        "vcs": "git" if available else "unavailable",
        "commit": commit if available else "UNKNOWN",
        "dirty": bool(status) if available else True,
        "state": "DIRTY" if (not available or status) else "CLEAN",
    }


def _package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for package in ("numpy", "pandas", "torch", "scikit-learn", "tqdm", "scipy", "matplotlib"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "NOT_INSTALLED"
    return versions


def _normalized_distribution_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _locked_requirements(lock_path: Path) -> dict[str, str]:
    requirements: dict[str, str] = {}
    pattern = re.compile(r"^([A-Za-z0-9_.-]+)==([^ \\\n]+)", re.MULTILINE)
    for name, version in pattern.findall(lock_path.read_text(encoding="utf-8")):
        normalized = _normalized_distribution_name(name)
        if normalized in requirements:
            raise ValueError(f"Duplicate requirement in scientific lock: {normalized}")
        requirements[normalized] = version
    if not requirements:
        raise ValueError(f"Scientific dependency lock has no exact requirements: {lock_path}")
    return requirements


def verify_locked_environment(lock_path: Path, policy_path: Path) -> dict[str, Any]:
    """Compare the active runtime with the hash-verified scientific lock."""

    requirements = _locked_requirements(lock_path)
    installed: dict[str, str] = {}
    mismatches: list[dict[str, str]] = []
    for package, expected in sorted(requirements.items()):
        try:
            actual = str(torch.__version__) if package == "torch" else metadata.version(package)
        except metadata.PackageNotFoundError:
            actual = "MISSING"
        installed[package] = actual
        if actual != expected:
            mismatches.append({"package": package, "expected": expected, "actual": actual})

    policy = _load_toml(policy_path).get("lock", {})
    expected_python = str(policy.get("python_version", "UNKNOWN"))
    expected_abi = str(policy.get("python_abi", "UNKNOWN"))
    expected_platform = str(policy.get("platform", "UNKNOWN"))
    expected_accelerator = str(policy.get("accelerator_stack", "UNKNOWN"))
    current_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    current_abi = (
        f"CPython-cp{sys.version_info.major}{sys.version_info.minor}"
        if platform.python_implementation() == "CPython"
        else f"{platform.python_implementation()}-UNKNOWN"
    )
    machine = platform.machine()
    libc_name, libc_version = platform.libc_ver()
    platform_matches = expected_platform.startswith(machine + "-")
    if "manylinux_2_28" in expected_platform:
        try:
            libc_tuple = tuple(int(piece) for piece in libc_version.split(".")[:2])
        except ValueError:
            libc_tuple = (0, 0)
        platform_matches = platform_matches and libc_name == "glibc" and libc_tuple >= (2, 28)
    accelerator_matches = expected_accelerator == f"PyTorch-{torch.__version__}"
    runtime_checks = {
        "python": {
            "expected": expected_python,
            "actual": current_python,
            "matches": current_python == expected_python,
        },
        "python_abi": {
            "expected": expected_abi,
            "actual": current_abi,
            "matches": current_abi == expected_abi,
        },
        "platform": {
            "expected": expected_platform,
            "actual": f"{machine}-{libc_name}_{libc_version}",
            "matches": platform_matches,
        },
        "accelerator_stack": {
            "expected": expected_accelerator,
            "actual": f"PyTorch-{torch.__version__}",
            "matches": accelerator_matches,
        },
    }
    runtime_mismatches = [name for name, check in runtime_checks.items() if not check["matches"]]
    digest_payload = {
        "lock_sha256": sha256_file(lock_path),
        "installed": installed,
        "runtime": runtime_checks,
        "torch_cuda_runtime": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
    }
    environment_digest = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "lock_path": lock_path.name,
        "lock_sha256": sha256_file(lock_path),
        "declared_package_count": len(requirements),
        "declared_versions": dict(sorted(requirements.items())),
        "installed_versions": installed,
        "package_mismatches": mismatches,
        "runtime": runtime_checks,
        "runtime_mismatches": runtime_mismatches,
        "matches": not mismatches and not runtime_mismatches,
        "environment_digest_sha256": environment_digest,
    }


def capture_environment(device: torch.device) -> dict[str, Any]:
    environment: dict[str, Any] = {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "system": platform.system(),
        "system_release": platform.release(),
        "machine": platform.machine(),
        "packages": _package_versions(),
        "torch_cuda_runtime": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "device_type": device.type,
    }
    if device.type == "cuda" and torch.cuda.is_available():
        index = device.index if device.index is not None else torch.cuda.current_device()
        properties = torch.cuda.get_device_properties(index)
        visible_devices = os.environ.get("CUDA_VISIBLE_DEVICES", "NOT_SET")
        visible_selectors = [item.strip() for item in visible_devices.split(",")]
        nvidia_smi_selector = (
            visible_selectors[index]
            if visible_devices != "NOT_SET" and index < len(visible_selectors)
            else str(index)
        )
        accelerator: dict[str, Any] = {
            "record_state": "PARTIAL",
            "visible_device_index": index,
            "name": properties.name,
            "compute_capability": [properties.major, properties.minor],
            "total_memory_bytes": properties.total_memory,
            "multiprocessor_count": properties.multi_processor_count,
            "cuda_visible_devices": visible_devices,
            "nvidia_smi_selector": nvidia_smi_selector,
        }
        for attribute in ("uuid", "pci_bus_id"):
            value = getattr(properties, attribute, None)
            if value is not None:
                accelerator[attribute] = str(value)
        try:
            query = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=uuid,pci.bus_id,driver_version,name",
                    "--format=csv,noheader,nounits",
                    f"--id={nvidia_smi_selector}",
                ],
                text=True,
                capture_output=True,
                check=False,
                timeout=10,
            )
            if query.returncode == 0 and query.stdout.strip():
                fields = [part.strip() for part in query.stdout.strip().splitlines()[0].split(",")]
                if len(fields) == 4:
                    accelerator["nvidia_smi"] = {
                        "uuid": fields[0],
                        "pci_bus_id": fields[1],
                        "driver_version": fields[2],
                        "name": fields[3],
                    }
                    accelerator["record_state"] = "RECORDED"
                else:
                    accelerator["nvidia_smi_error"] = "unexpected query field count"
            else:
                accelerator["nvidia_smi_error"] = (
                    query.stderr.strip() or f"exit code {query.returncode}"
                )
        except (OSError, subprocess.SubprocessError) as error:
            accelerator["nvidia_smi_error"] = f"{type(error).__name__}: {error}"
        environment["device_name"] = properties.name
        environment["device_capability"] = [properties.major, properties.minor]
        environment["accelerator"] = accelerator
    else:
        environment["accelerator"] = {"record_state": "NOT_APPLICABLE"}
    return environment


def _relative_path(project_root: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return "OUTSIDE_PROJECT"


def normalize_arguments(arguments: Mapping[str, Any], project_root: Path) -> dict[str, Any]:
    """Normalize path-like CLI values without publishing machine-specific roots."""

    normalized: dict[str, Any] = {}
    for key, value in arguments.items():
        if value is None or isinstance(value, (bool, int, float)):
            normalized[key] = value
        elif key in {"config", "protocol", "out", "dump_dir"}:
            normalized[key] = _relative_path(project_root, Path(value))
        else:
            normalized[key] = str(value)
    return normalized


def build_job_metadata(
    project_root: Path,
    *,
    job_id: Optional[str],
    runner_path: Path,
    resolved: ResolvedRunConfig,
    arguments: Mapping[str, Any],
    expected_tasks: Sequence[str],
    determinism_state: Mapping[str, Any],
    task_profile_validation: Optional[Mapping[str, Any]],
    device: torch.device,
    started_at: str,
) -> dict[str, Any]:
    """Build a non-self-certifying job envelope for one runner invocation."""

    root = project_root.resolve()
    bootstrap_constraints = root / "configs/dependencies.lock"
    dependency_lock = root / resolved.dependency_lock_path
    lock_policy = root / "configs/dependency-lock-policy.toml"
    resource_manifest = root / "resources/manifest.toml"
    source = capture_source_state(root)
    scheduler_job_id = os.environ.get("SLURM_JOB_ID")
    normalized_job_id = job_id or os.environ.get("LP_JOB_ID") or "UNREGISTERED"
    scientific_blockers: list[str] = []
    submission_script: Optional[Path] = None
    if normalized_job_id == "UNREGISTERED":
        scientific_blockers.append("normalized job_id is absent")
    elif re.fullmatch(r"LP-JOB-[A-Z0-9-]+", normalized_job_id) is None:
        scientific_blockers.append("normalized job_id does not match LP-JOB-* syntax")
    if scheduler_job_id is None:
        scientific_blockers.append("scheduler identity is absent")
    else:
        submission_value = os.environ.get("LP_SUBMISSION_SCRIPT")
        if not submission_value:
            scientific_blockers.append("scheduler submission script identity is absent")
        else:
            try:
                submission_script = _project_file(
                    root, submission_value, "scheduler submission script"
                )
            except (FileNotFoundError, ValueError) as error:
                scientific_blockers.append(str(error))
    if source["dirty"]:
        scientific_blockers.append("source tree is dirty or unavailable")
    if not resolved.protocol_conformant:
        scientific_blockers.append("resolved parameters deviate from the protocol")
    if resolved.protocol_status not in {"FROZEN", "ADMITTED"}:
        scientific_blockers.append(f"protocol status is {resolved.protocol_status}")
    if resolved.determinism != "strict":
        scientific_blockers.append(f"determinism mode is {resolved.determinism}")
    if not determinism_state.get("strict_prerequisites_satisfied", False):
        scientific_blockers.append("strict determinism prerequisites are unmet")
    if not task_profile_validation or not task_profile_validation.get("valid", False):
        scientific_blockers.append("task profile is missing or does not match resolved arguments")
    elif not task_profile_validation.get("scientific_matrix_eligible", True):
        scientific_blockers.append("task profile is quarantined from the scientific matrix")
    lock_status = "MISSING"
    if lock_policy.is_file():
        lock_section = _load_toml(lock_policy).get("lock", {})
        lock_status = str(lock_section.get("status", "UNKNOWN"))
        if lock_section.get("scientific_lock") != resolved.dependency_lock_path:
            scientific_blockers.append("dependency lock path disagrees with lock policy")
        if lock_section.get("scientific_lock_sha256") != resolved.dependency_lock_sha256:
            scientific_blockers.append("dependency lock hash disagrees with lock policy")
    if lock_status != "SCIENTIFIC-FROZEN":
        scientific_blockers.append(f"dependency lock status is {lock_status}")
    locked_environment = verify_locked_environment(dependency_lock, lock_policy)
    if not locked_environment["matches"]:
        scientific_blockers.append(
            "active environment does not exactly match the scientific dependency lock"
        )
    scientific_mode_requested = bool(
        normalized_job_id != "UNREGISTERED"
        and scheduler_job_id is not None
        and resolved.determinism == "strict"
    )

    def file_record(path: Path) -> dict[str, str]:
        return {
            "path": _relative_path(root, path),
            "sha256": sha256_file(path) if path.is_file() else "MISSING",
        }

    manifest_data = _load_toml(resource_manifest)
    current_datasets: dict[str, dict[str, Any]] = {}
    for entry in manifest_data.get("dataset", []):
        dataset_path = Path(str(entry.get("path", "")))
        if str(entry.get("state", "")).startswith("CURRENT"):
            current_datasets[dataset_path.stem] = {
                "id": entry.get("id"),
                "path": dataset_path.as_posix(),
                "sha256": entry.get("sha256"),
                "state": entry.get("state"),
            }
    missing_dataset_records = sorted(set(resolved.datasets) - set(current_datasets))
    if missing_dataset_records:
        scientific_blockers.append(
            f"current dataset records are missing: {missing_dataset_records}"
        )
    data_root = Path(
        os.environ.get("LINK_PREDICTION_DATA_DIR", root / "resources/corpora")
    ).resolve()
    for dataset_name in resolved.datasets:
        entry = current_datasets.get(dataset_name)
        if entry is None:
            continue
        dataset_path = data_root / Path(str(entry["path"])).name
        if not dataset_path.is_file():
            scientific_blockers.append(f"dataset bytes are missing: {dataset_name}")
            entry["local_verification"] = "MISSING"
        else:
            actual_dataset_hash = sha256_file(dataset_path)
            entry["local_verification"] = (
                "MATCH" if actual_dataset_hash == entry["sha256"] else "CHECKSUM-MISMATCH"
            )
            if actual_dataset_hash != entry["sha256"]:
                scientific_blockers.append(f"dataset checksum mismatch: {dataset_name}")
    source_registry_value = manifest_data.get("source_registry", "resources/source_registry.json")
    source_registry = root / str(source_registry_value)

    environment = capture_environment(device)
    if scientific_mode_requested:
        accelerator = environment.get("accelerator", {})
        if device.type != "cuda" or accelerator.get("record_state") != "RECORDED":
            scientific_blockers.append("deterministic accelerator record is absent")

    return {
        "schema_version": 1,
        "job_id": normalized_job_id,
        "execution_kind": "scheduler" if scheduler_job_id else "local",
        "scheduler": {
            "system": "slurm" if scheduler_job_id else "none",
            "job_id": scheduler_job_id or "NOT_APPLICABLE",
            "array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID", "NOT_APPLICABLE"),
            "array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID", "NOT_APPLICABLE"),
            "restart_count": int(os.environ.get("SLURM_RESTART_COUNT", "0")),
            "submission_script": (
                file_record(submission_script)
                if submission_script is not None
                else {"path": "NOT_RECORDED", "sha256": "MISSING"}
            ),
        },
        "started_at": started_at,
        "finished_at": None,
        "status": "RUNNING",
        "exit_code": None,
        "source": source,
        "resolved_configuration": resolved.as_metadata(),
        "resolved_arguments": normalize_arguments(arguments, root),
        "task_profile_validation": dict(task_profile_validation or {}),
        "determinism": dict(determinism_state),
        "environment": environment,
        "inputs": {
            "runner": file_record(runner_path),
            "protocol": file_record(root / resolved.protocol_path),
            "configuration": file_record(root / resolved.config_path),
            "dependency_constraints": file_record(bootstrap_constraints),
            "scientific_dependency_lock": file_record(dependency_lock),
            "dependency_lock_policy": file_record(lock_policy),
            "dataset_manifest": file_record(resource_manifest),
            "dataset_source_registry": file_record(source_registry),
            "datasets": [
                current_datasets[name]
                for name in resolved.datasets if name in current_datasets
            ],
        },
        "coverage": {
            "expected": list(expected_tasks),
            "completed": [],
            "failed": [],
            "excluded": [],
        },
        "scientific_execution_prerequisites_satisfied": not scientific_blockers,
        "scientific_mode_requested": scientific_mode_requested,
        "scientific_evidence_eligible": False,
        "scientific_evidence_blockers": scientific_blockers,
        "locked_environment": locked_environment,
    }


def finish_job_metadata(job: dict[str, Any], failures: Sequence[Mapping[str, Any]]) -> None:
    job["finished_at"] = utc_now()
    job["status"] = "FAILED" if failures else "COMPLETED"
    job["exit_code"] = 1 if failures else 0
    coverage = job["coverage"]
    complete = (
        not coverage["failed"]
        and not coverage["excluded"]
        and sorted(coverage["completed"]) == sorted(coverage["expected"])
    )
    if not complete and "task coverage is incomplete" not in job["scientific_evidence_blockers"]:
        job["scientific_evidence_blockers"].append("task coverage is incomplete")
    job["scientific_evidence_eligible"] = bool(
        job["scientific_execution_prerequisites_satisfied"]
        and not failures
        and complete
    )


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if value is None or isinstance(value, (str, bool, int)):
        return value
    return str(value)


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Atomically replace a runner JSON document with strict JSON."""

    destination = path.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=destination.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        json.dump(_json_safe(payload), stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
