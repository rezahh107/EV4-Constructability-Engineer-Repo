from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml
from jsonschema import Draft202012Validator

POLICY_ID = "EV4-PCVP"
POLICY_VERSION = "1.0.0"
ARCHITECTURE_LOCK_ID = "EV4-PCVP-ROLL-LOCK-20260727-R1"
CANONICAL_REPOSITORY = "rezahh107/EV4-Decision-Kernel"
CANONICAL_COMMIT = "069a50fa243b01fa578a7c1bcb8864d9e796d34b"
CE_REPOSITORY = "rezahh107/EV4-Constructability-Engineer-Repo"
SOURCE_STAGE = "CONSTRUCTABILITY_ENGINEER"
CONSUMER_STAGE = "BUILDER_ASSISTANT"
ARCHITECT_STAGE = "ARCHITECT"
ARCHITECT_REPOSITORY = "rezahh107/EV4-Architect-Repo"
ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class PCVPFileIdentity:
    name: str
    sha256: str


@dataclass(frozen=True)
class PCVPSourceProfileIdentity:
    stage_id: str
    profile_id: str
    profile_version: str
    repository: str
    canonical_path: str
    local_path: str
    sha256: str


@dataclass(frozen=True)
class PCVPIdentityDescriptor:
    policy_id: str
    policy_version: str
    architecture_lock_id: str
    canonical_repository: str
    canonical_commit: str
    canonical_schema_root: str
    canonical_profile_path: str
    local_lock_path: str
    local_schema_root: str
    local_profile_path: str
    profile_sha256: str
    source_profiles: tuple[PCVPSourceProfileIdentity, ...]
    schema_files: tuple[PCVPFileIdentity, ...]


DESCRIPTOR = PCVPIdentityDescriptor(
    policy_id=POLICY_ID,
    policy_version=POLICY_VERSION,
    architecture_lock_id=ARCHITECTURE_LOCK_ID,
    canonical_repository=CANONICAL_REPOSITORY,
    canonical_commit=CANONICAL_COMMIT,
    canonical_schema_root="kernel/pcvp/v1.0.0/bundle/04-SCHEMAS",
    canonical_profile_path=(
        "kernel/pcvp/v1.0.0/bundle/03-PROFILES/constructability.profile.yaml"
    ),
    local_lock_path="contracts/pcvp/pcvp-v1.lock.json",
    local_schema_root="contracts/pcvp/vendor/decision-kernel/v1.0.0",
    local_profile_path="contracts/pcvp/constructability.profile.yaml",
    profile_sha256="00b5e3a1b3490f9b81ef8e81fc1b51b8899f2dd6ba5ba416b38a47a270488461",
    source_profiles=(
        PCVPSourceProfileIdentity(
            stage_id=ARCHITECT_STAGE,
            profile_id="EV4-PCVP-PROFILE-ARCHITECT",
            profile_version="1.0.0",
            repository=ARCHITECT_REPOSITORY,
            canonical_path="kernel/pcvp/v1.0.0/bundle/03-PROFILES/architect.profile.yaml",
            local_path="contracts/pcvp/architect.profile.yaml",
            sha256="a4fc9b2912eea0fcba06880759f246c019f3d36b181696824d8c8e54d39b5248",
        ),
    ),
    schema_files=(
        PCVPFileIdentity(
            "authorization.schema.json",
            "8eba853834bc3881ae836857a5bef3d8cc8e7c9edecd535ba22fb58a26fa5ff9",
        ),
        PCVPFileIdentity(
            "claim.schema.json",
            "7d4c686b983330c454d76ebc34ef97ca4c595dd77b221de194e6a75e41859a72",
        ),
        PCVPFileIdentity(
            "effect.schema.json",
            "59c201b7277f3bf3488eb43afbd04f686efae25b9a143c73f97aca5f65a1bbeb",
        ),
        PCVPFileIdentity(
            "handoff.schema.json",
            "dcc3189ef4662b27e440aee3d3c698d503e265f81fb71d5d1904972cfe8728da",
        ),
    ),
)

ARCHITECT_PROFILE_SHA256 = DESCRIPTOR.source_profiles[0].sha256


class PCVPIdentityError(RuntimeError):
    """Raised when a local non-authoritative PCVP mirror loses canonical identity."""

    def __init__(
        self,
        path: str,
        expected: Any,
        actual: Any,
        *,
        message: str = "PCVP canonical identity mismatch",
    ) -> None:
        self.code = "PCVP_CANONICAL_IDENTITY_MISMATCH"
        self.path = path
        self.expected = expected
        self.actual = actual
        super().__init__(f"{message} at {path}: expected {expected!r}; observed {actual!r}")


@dataclass(frozen=True)
class PCVPResources:
    descriptor: PCVPIdentityDescriptor
    lock: dict[str, Any]
    profile: dict[str, Any]
    source_profiles: dict[str, dict[str, Any]]
    schemas: dict[str, dict[str, Any]]


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise PCVPIdentityError(str(path), "readable JSON", type(exc).__name__) from exc


def _expect_exact(actual: Any, expected: Any, path: str) -> None:
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            raise PCVPIdentityError(path, "object", type(actual).__name__)
        expected_keys = set(expected)
        actual_keys = set(actual)
        if actual_keys != expected_keys:
            raise PCVPIdentityError(
                f"{path}.__keys__",
                sorted(expected_keys),
                sorted(actual_keys),
            )
        for key in sorted(expected_keys):
            _expect_exact(actual[key], expected[key], f"{path}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list):
            raise PCVPIdentityError(path, "array", type(actual).__name__)
        if len(actual) != len(expected):
            raise PCVPIdentityError(f"{path}.__length__", len(expected), len(actual))
        for index, (observed, required) in enumerate(zip(actual, expected, strict=True)):
            _expect_exact(observed, required, f"{path}[{index}]")
        return
    if actual != expected:
        raise PCVPIdentityError(path, expected, actual)


def _expected_lock(descriptor: PCVPIdentityDescriptor) -> dict[str, Any]:
    return {
        "schema_version": "ev4-pcvp-contract-lock.v1",
        "architecture_lock_id": descriptor.architecture_lock_id,
        "policy": {
            "id": descriptor.policy_id,
            "version": descriptor.policy_version,
            "adoption_status": "not_yet_adopted",
            "activation": "NONE",
        },
        "canonical": {
            "repository": descriptor.canonical_repository,
            "commit_sha": descriptor.canonical_commit,
            "schema_root": descriptor.canonical_schema_root,
            "profile_path": descriptor.canonical_profile_path,
        },
        "profile": {
            "profile_id": "EV4-PCVP-PROFILE-CONSTRUCTABILITY",
            "profile_version": "1.0.0",
            "repository": CE_REPOSITORY,
            "stage_id": "CONSTRUCTABILITY_ENGINEER",
            "consumes_from": ["ARCHITECT"],
            "path": descriptor.local_profile_path,
            "sha256": descriptor.profile_sha256,
            "local_copy_authoritative": False,
        },
        "source_profiles": {
            item.stage_id: {
                "profile_id": item.profile_id,
                "profile_version": item.profile_version,
                "repository": item.repository,
                "stage_id": item.stage_id,
                "canonical_path": item.canonical_path,
                "path": item.local_path,
                "sha256": item.sha256,
                "local_copy_authoritative": False,
            }
            for item in descriptor.source_profiles
        },
        "producer": {
            "repository": CE_REPOSITORY,
            "source_stage": SOURCE_STAGE,
            "consumer_stage": CONSUMER_STAGE,
            "carrier_path": "builder_executable_package.continuation_assurance",
            "emission_enabled": False,
            "caller_override_allowed": False,
        },
        "vendored": {
            "root": descriptor.local_schema_root,
            "local_copy_authoritative": False,
        },
        "files": [
            {"name": item.name, "sha256": item.sha256}
            for item in descriptor.schema_files
        ],
        "verification": {
            "byte_equality_required": True,
            "compare_against_moving_default_branch": False,
        },
    }


def _load_profile_document(
    path: Path,
    *,
    expected_sha256: str,
    expected_identity: Mapping[str, Any],
    identity_path: str,
) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PCVPIdentityError(str(path), "readable profile", type(exc).__name__) from exc
    observed_digest = _sha256_bytes(raw)
    if observed_digest != expected_sha256:
        raise PCVPIdentityError(
            f"{identity_path}.sha256",
            expected_sha256,
            observed_digest,
        )
    try:
        document = yaml.safe_load(raw.decode("utf-8"))
    except (UnicodeError, yaml.YAMLError) as exc:
        raise PCVPIdentityError(str(path), "valid UTF-8 YAML", type(exc).__name__) from exc
    if not isinstance(document, dict) or not isinstance(
        document.get("continuation_profile"), dict
    ):
        raise PCVPIdentityError(
            f"{identity_path}.continuation_profile", "object", document
        )
    profile = document["continuation_profile"]
    for key, expected in expected_identity.items():
        _expect_exact(
            profile.get(key),
            expected,
            f"{identity_path}.continuation_profile.{key}",
        )
    return copy.deepcopy(document)


def _load_constructability_profile(
    path: Path,
    descriptor: PCVPIdentityDescriptor,
) -> dict[str, Any]:
    return _load_profile_document(
        path,
        expected_sha256=descriptor.profile_sha256,
        expected_identity={
            "profile_id": "EV4-PCVP-PROFILE-CONSTRUCTABILITY",
            "profile_version": "1.0.0",
            "policy_id": descriptor.policy_id,
            "policy_version": descriptor.policy_version,
            "repository": CE_REPOSITORY,
            "stage_id": "CONSTRUCTABILITY_ENGINEER",
            "consumes_from": ["ARCHITECT"],
        },
        identity_path="$.profile",
    )


def _load_source_profile(
    root: Path,
    identity: PCVPSourceProfileIdentity,
    descriptor: PCVPIdentityDescriptor,
) -> dict[str, Any]:
    return _load_profile_document(
        root / identity.local_path,
        expected_sha256=identity.sha256,
        expected_identity={
            "profile_id": identity.profile_id,
            "profile_version": identity.profile_version,
            "policy_id": descriptor.policy_id,
            "policy_version": descriptor.policy_version,
            "repository": identity.repository,
            "stage_id": identity.stage_id,
        },
        identity_path=f"$.source_profiles.{identity.stage_id}",
    )


def load_pcvp_resources(
    repository_root: str | Path = ROOT,
    *,
    descriptor: PCVPIdentityDescriptor = DESCRIPTOR,
) -> PCVPResources:
    root = Path(repository_root)
    lock = _load_json(root / descriptor.local_lock_path)
    _expect_exact(lock, _expected_lock(descriptor), "$")

    profile = _load_constructability_profile(
        root / descriptor.local_profile_path,
        descriptor,
    )
    source_profiles = {
        item.stage_id: _load_source_profile(root, item, descriptor)
        for item in descriptor.source_profiles
    }

    schemas: dict[str, dict[str, Any]] = {}
    for item in descriptor.schema_files:
        path = root / descriptor.local_schema_root / item.name
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise PCVPIdentityError(str(path), "readable schema", type(exc).__name__) from exc
        observed_digest = _sha256_bytes(raw)
        if observed_digest != item.sha256:
            raise PCVPIdentityError(
                f"$.files.{item.name}.sha256",
                item.sha256,
                observed_digest,
            )
        try:
            schema = json.loads(raw.decode("utf-8"))
        except (UnicodeError, ValueError, TypeError) as exc:
            raise PCVPIdentityError(
                f"$.files.{item.name}", "valid UTF-8 JSON schema", type(exc).__name__
            ) from exc
        if not isinstance(schema, dict):
            raise PCVPIdentityError(f"$.files.{item.name}", "object", type(schema).__name__)
        Draft202012Validator.check_schema(schema)
        schemas[item.name] = schema

    return PCVPResources(
        descriptor=descriptor,
        lock=copy.deepcopy(lock),
        profile=profile,
        source_profiles=copy.deepcopy(source_profiles),
        schemas=copy.deepcopy(schemas),
    )


__all__ = [
    "ARCHITECT_PROFILE_SHA256",
    "ARCHITECTURE_LOCK_ID",
    "CANONICAL_COMMIT",
    "CANONICAL_REPOSITORY",
    "DESCRIPTOR",
    "PCVPFileIdentity",
    "PCVPIdentityDescriptor",
    "PCVPIdentityError",
    "PCVPResources",
    "PCVPSourceProfileIdentity",
    "POLICY_ID",
    "POLICY_VERSION",
    "load_pcvp_resources",
]
