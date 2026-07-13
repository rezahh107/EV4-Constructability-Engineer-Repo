from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "governance" / "AI_AUTHORITY_PROFILE.yml"
DEFAULT_STATE = ROOT / "planning" / "GOVERNANCE_SCOPE_STATE.yml"
DEFAULT_SCHEMA = ROOT / "schemas" / "ai_governance_state.v1.schema.json"
EXPECTED_REPOSITORY = "rezahh107/EV4-Constructability-Engineer-Repo"
EXPECTED_PROFILE_ID = "personal_ai_operated_strong_governance_minimum_security"
EXPECTED_PROFILE_VERSION = "v1.0.0"
EXPECTED_INSPECTOR_REPOSITORY = "rezahh107/PR-Inspector"
REQUIRED_REVIEW_ARTIFACTS = (
    "review-package.json",
    "DECISION_PROJECTION.json",
    "artifact-manifest.json",
)

CAPABILITY_ID = re.compile(r"^CE-GOV-[0-9]{3}-[A-Z0-9-]+$")
SHA = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SEMVER = re.compile(r"^v([0-9]+)\.([0-9]+)\.([0-9]+)$")
FORBIDDEN_APPROVAL_KEYS = {
    "human_technical_approval",
    "owner_technical_signoff",
    "owner_scope_acknowledgement",
    "human_review_required",
    "specialist_signoff",
}
DISPOSITION_TO_SET = {
    "committed_now": "committed_now_ids",
    "implemented": "implemented_ids",
    "deferred": "deferred_not_deleted_ids",
    "remembered": "deferred_not_deleted_ids",
    "rejected": "rejected_ids",
    "superseded": "superseded_ids",
    "implemented_elsewhere": "implemented_ids",
    "not_applicable": "rejected_ids",
}
ALLOWED_EVIDENCE_STATES = {
    "REPOSITORY_CONFIRMED",
    "TEST_CONFIRMED",
    "CI_CONFIRMED",
    "TOOL_CONFIRMED",
    "AI_REVIEW_SIGNAL",
    "USER_REPORTED",
    "UNVERIFIED",
    "INSUFFICIENT_EVIDENCE",
}
MINIMUM_SECURITY_CONTROLS_V1 = (
    "no_secrets_in_repository_prompt_log_or_artifact",
    "exact_repository_branch_and_target_identity",
    "destructive_action_scope_and_recovery",
    "untrusted_input_boundary",
    "explicit_authorization_for_production_credentials_dns_billing_or_real_data",
    "dependency_source_and_necessity_review",
    "reversible_version_controlled_changes",
    "fail_closed_on_missing_access_identity_or_evidence",
)
INTENTIONAL_EXCLUSIONS_V1 = (
    "mandatory_branch_protection",
    "merge_queue",
    "CODEOWNERS_security_approval",
    "formal_threat_model_program",
    "penetration_testing",
    "continuous_SAST_DAST",
    "SBOM_and_supply_chain_attestation",
    "signed_artifact_provenance_infrastructure",
    "runtime_security_monitoring",
    "OS_harness_enforcement",
)
ACTIVATION_TRIGGERS_V1 = (
    "external_contributors",
    "real_personal_or_customer_data",
    "production_or_public_service",
    "persistent_credentials_or_privileged_APIs",
    "money_billing_or_financial_assets",
    "physical_health_or_safety_impact",
    "third_party_reliance",
    "legal_contractual_or_regulatory_duties",
    "irreversible_infrastructure_or_account_changes",
)
CANONICAL_REQUIRED_ARTIFACTS = {
    "governance/AI_AUTHORITY_PROFILE.yml",
    "planning/GOVERNANCE_SCOPE_STATE.yml",
    "schemas/ai_governance_state.v1.schema.json",
    "validator/ai_governance.py",
    "validator/ai_governance_core.py",
    "validator/ai_governance_evidence.py",
    "validator/ai_governance_review.py",
    "scripts/validate-ai-governance.py",
    "tests/test_ai_governance.py",
}
REQUIRED_GREEN_PREDICATES = {
    "exact_head_ci_passed",
    "scope_gate_passed",
    "progress_gate_passed",
    "independent_review_green",
    "no_blocking_findings",
}
GREEN = "GREEN_MERGE_RECOMMENDED"
_REPOSITORY_STATE_MARKER = object()
_GATE_EVIDENCE_MARKER = object()
_CANONICAL_REVIEW_MARKER = object()
_REVIEW_CAPABILITY_MARKER = object()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    match = SEMVER.fullmatch(value)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else MappingProxyType({})


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def load_yaml(path: str | Path) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _walk_forbidden_keys(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in FORBIDDEN_APPROVAL_KEYS:
                errors.append(f"{path}.{key}: forbidden human technical approval field")
            errors.extend(_walk_forbidden_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_walk_forbidden_keys(child, f"{path}[{index}]"))
    return errors


def _validate_exact_identity_list(
    name: str,
    value: Any,
    expected: tuple[str, ...],
) -> list[str]:
    if not isinstance(value, list):
        return [f"{name} must be an array containing the v1.0.0 identity set"]
    if any(not isinstance(item, str) for item in value):
        return [f"{name} entries must all be strings"]
    errors: list[str] = []
    if len(value) != len(set(value)):
        errors.append(f"{name} contains duplicate padding")
    actual = set(value)
    required = set(expected)
    missing = sorted(required - actual)
    unexpected = sorted(actual - required)
    if missing:
        errors.append(f"{name} is missing required identities: {', '.join(missing)}")
    if unexpected:
        errors.append(f"{name} contains substituted or unversioned identities: {', '.join(unexpected)}")
    if len(value) != len(expected):
        errors.append(f"{name} must contain exactly {len(expected)} unique v1.0.0 identities")
    return errors


def validate_profile(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if profile.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if profile.get("profile_version") != EXPECTED_PROFILE_VERSION:
        errors.append("profile_version must be v1.0.0")
    if profile.get("profile_id") != EXPECTED_PROFILE_ID:
        errors.append("profile_id must select the personal minimum-security governance profile")
    if profile.get("repository") != EXPECTED_REPOSITORY:
        errors.append("profile repository identity mismatch")

    authority = _mapping(profile.get("technical_authority"))
    if authority.get("decision_authority") != "AI":
        errors.append("technical_authority.decision_authority must be AI")
    if authority.get("factual_authority") != "evidence":
        errors.append("technical_authority.factual_authority must be evidence")
    if authority.get("human_technical_approval_required") is not False:
        errors.append("human technical approval must not be required")
    if authority.get("user_merge_action_is_technical_approval") is not False:
        errors.append("user Merge action must not be technical approval")

    errors.extend(
        _validate_exact_identity_list(
            "minimum_security_controls",
            profile.get("minimum_security_controls"),
            MINIMUM_SECURITY_CONTROLS_V1,
        )
    )
    errors.extend(
        _validate_exact_identity_list(
            "intentionally_out_of_scope_controls",
            profile.get("intentionally_out_of_scope_controls"),
            INTENTIONAL_EXCLUSIONS_V1,
        )
    )
    errors.extend(
        _validate_exact_identity_list(
            "activation_triggers",
            profile.get("activation_triggers"),
            ACTIVATION_TRIGGERS_V1,
        )
    )

    states_raw = profile.get("evidence_states")
    if not isinstance(states_raw, list) or any(not isinstance(item, str) for item in states_raw):
        errors.append("evidence_states must be an array of strings")
    else:
        if len(states_raw) != len(set(states_raw)):
            errors.append("evidence_states contains duplicates")
        if set(states_raw) != ALLOWED_EVIDENCE_STATES:
            errors.append("evidence_states must exactly match the approved evidence vocabulary")

    review = _mapping(profile.get("review_protocol"))
    if review.get("name") != "PR-Inspector":
        errors.append("review protocol must be PR-Inspector")
    if review.get("inspector_repository") != EXPECTED_INSPECTOR_REPOSITORY:
        errors.append("review_protocol.inspector_repository identity mismatch")
    if review.get("minimum_protocol_version") != "v1.9.0":
        errors.append("review_protocol.minimum_protocol_version must be v1.9.0")
    artifacts = review.get("canonical_artifacts")
    if artifacts != list(REQUIRED_REVIEW_ARTIFACTS):
        errors.append("review_protocol.canonical_artifacts must match the exact canonical set")
    for key in (
        "exact_head_required",
        "stale_on_head_change",
        "separate_session_required",
        "official_completion_required",
    ):
        if review.get(key) is not True:
            errors.append(f"review_protocol.{key} must be true")

    errors.extend(_walk_forbidden_keys(profile))
    return errors


def validate_state_schema(state: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema)
    return [
        f"{'/'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(state), key=lambda item: list(item.absolute_path))
    ]


def validate_scope_semantics(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    scope = _mapping(state.get("scope_projection"))
    if not scope:
        return ["scope_projection must be an object"]
    target = _list(scope.get("long_term_target_ids"))
    bucket_names = (
        "committed_now_ids",
        "implemented_ids",
        "deferred_not_deleted_ids",
        "rejected_ids",
        "superseded_ids",
    )
    buckets: dict[str, list[Any]] = {name: _list(scope.get(name)) for name in bucket_names}

    if any(not isinstance(item, str) for item in target):
        errors.append("long_term_target_ids must contain only strings")
        target = [item for item in target if isinstance(item, str)]
    if len(target) != len(set(target)):
        errors.append("long_term_target_ids contains duplicates")
    for capability_id in target:
        if not CAPABILITY_ID.fullmatch(capability_id):
            errors.append(f"invalid capability ID: {capability_id}")

    seen: dict[str, str] = {}
    for bucket_name, ids in buckets.items():
        if any(not isinstance(item, str) for item in ids):
            errors.append(f"scope_projection.{bucket_name} must contain only strings")
        for capability_id in (item for item in ids if isinstance(item, str)):
            previous = seen.get(capability_id)
            if previous is not None:
                errors.append(
                    f"{capability_id} appears in incompatible dispositions: {previous} and {bucket_name}"
                )
            seen[capability_id] = bucket_name

    target_set = set(target)
    known_set = set(seen)
    missing = sorted(target_set - known_set)
    unknown = sorted(known_set - target_set)
    if missing:
        errors.append(f"silent capability deletion: {', '.join(missing)}")
    if unknown:
        errors.append(f"unknown capability IDs outside long-term target: {', '.join(unknown)}")

    memory = state.get("capability_memory")
    if not isinstance(memory, list):
        errors.append("capability_memory must be an array")
        memory = []
    memory_ids: list[str] = []
    for index, raw_entry in enumerate(memory):
        entry = _mapping(raw_entry)
        capability_id = entry.get("capability_id")
        disposition = entry.get("disposition")
        if not isinstance(capability_id, str):
            errors.append(f"capability_memory[{index}].capability_id must be a string")
            continue
        memory_ids.append(capability_id)
        expected_bucket = DISPOSITION_TO_SET.get(str(disposition))
        if expected_bucket is None:
            errors.append(f"{capability_id} has invalid disposition {disposition}")
        elif capability_id not in set(buckets[expected_bucket]):
            errors.append(
                f"{capability_id} disposition {disposition} does not match "
                f"scope_projection.{expected_bucket}"
            )
    if len(memory_ids) != len(set(memory_ids)):
        errors.append("capability_memory contains duplicate capability IDs")
    if set(memory_ids) != target_set:
        errors.append("capability_memory must cover every long-term target exactly once")

    progress = _mapping(state.get("progress_gate"))
    required_artifacts = progress.get("required_artifacts")
    if not isinstance(required_artifacts, list) or any(
        not isinstance(item, str) for item in required_artifacts
    ):
        errors.append("progress_gate.required_artifacts must be an array of strings")
    elif not CANONICAL_REQUIRED_ARTIFACTS <= set(required_artifacts):
        errors.append("progress_gate.required_artifacts is missing governance carriers")

    review_gate = _mapping(state.get("review_merge_gate"))
    green_requires = review_gate.get("green_requires")
    if not isinstance(green_requires, list) or set(green_requires) != REQUIRED_GREEN_PREDICATES:
        errors.append("review_merge_gate.green_requires does not match the fail-closed gate")

    errors.extend(_walk_forbidden_keys(state))
    return errors


def validate_required_artifacts(
    state: dict[str, Any],
    *,
    repository_root: str | Path = ROOT,
) -> tuple[list[dict[str, Any]], list[str]]:
    root = Path(repository_root).resolve()
    progress = _mapping(state.get("progress_gate"))
    required = progress.get("required_artifacts")
    if not isinstance(required, list):
        return [], ["progress_gate.required_artifacts must be an array"]
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for raw_path in required:
        if not isinstance(raw_path, str) or not raw_path:
            errors.append("required artifact paths must be non-empty strings")
            continue
        relative = Path(raw_path)
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"required artifact path escapes repository root: {raw_path}")
            continue
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            errors.append(f"required artifact path escapes repository root: {raw_path}")
            continue
        exists = target.is_file()
        size = target.stat().st_size if exists else 0
        digest = _sha256(target.read_bytes()) if exists and size > 0 else None
        record = {
            "path": raw_path,
            "exists": exists,
            "non_empty": size > 0,
            "size_bytes": size,
            "sha256": digest,
            "evidence": "REPOSITORY_CONFIRMED" if exists and size > 0 else "INSUFFICIENT_EVIDENCE",
        }
        records.append(record)
        if not exists:
            errors.append(f"required artifact is missing: {raw_path}")
        elif size == 0:
            errors.append(f"required artifact is empty: {raw_path}")
    return records, errors


@dataclass(frozen=True, slots=True)
class ValidatedGovernanceState:
    profile: Mapping[str, Any]
    state: Mapping[str, Any]
    repository_root: Path
    artifact_records: tuple[Mapping[str, Any], ...]
    _marker: object = field(repr=False, compare=False)


def is_validated_governance_state(value: object) -> bool:
    return isinstance(value, ValidatedGovernanceState) and value._marker is _REPOSITORY_STATE_MARKER


def _diagnostic(stage: str, path: str, message: str) -> dict[str, str]:
    return {"stage": stage, "path": path, "message": message}


def validate_repository_state(
    *,
    profile_path: str | Path = DEFAULT_PROFILE,
    state_path: str | Path = DEFAULT_STATE,
    schema_path: str | Path = DEFAULT_SCHEMA,
    repository_root: str | Path = ROOT,
) -> dict[str, Any]:
    diagnostics: list[dict[str, str]] = []
    profile: dict[str, Any] = {}
    state: dict[str, Any] = {}
    schema: dict[str, Any] = {}
    for stage, path, loader in (
        ("profile_load", profile_path, load_yaml),
        ("state_load", state_path, load_yaml),
        ("schema_load", schema_path, load_json),
    ):
        try:
            loaded = loader(path)
        except Exception as exc:
            diagnostics.append(_diagnostic(stage, str(path), str(exc)))
            loaded = {}
        if stage == "profile_load":
            profile = loaded
        elif stage == "state_load":
            state = loaded
        else:
            schema = loaded
    if diagnostics:
        return {
            "passed": False,
            "errors": [item["message"] for item in diagnostics],
            "diagnostics": diagnostics,
            "profile": profile,
            "state": state,
            "verification": None,
        }

    for message in validate_profile(profile):
        diagnostics.append(_diagnostic("profile_semantics", str(profile_path), message))
    schema_errors = validate_state_schema(state, schema)
    for message in schema_errors:
        diagnostics.append(_diagnostic("state_schema", str(state_path), message))
    if not schema_errors:
        for message in validate_scope_semantics(state):
            diagnostics.append(_diagnostic("scope_semantics", str(state_path), message))
    artifact_records: list[dict[str, Any]] = []
    if not schema_errors:
        artifact_records, artifact_errors = validate_required_artifacts(
            state,
            repository_root=repository_root,
        )
        for message in artifact_errors:
            diagnostics.append(_diagnostic("progress_artifacts", str(state_path), message))

    verification = None
    if not diagnostics:
        verification = ValidatedGovernanceState(
            MappingProxyType(profile),
            MappingProxyType(state),
            Path(repository_root).resolve(),
            tuple(MappingProxyType(record) for record in artifact_records),
            _REPOSITORY_STATE_MARKER,
        )
    return {
        "passed": not diagnostics,
        "errors": [item["message"] for item in diagnostics],
        "diagnostics": diagnostics,
        "profile": profile,
        "state": state,
        "artifact_records": artifact_records,
        "verification": verification,
    }
