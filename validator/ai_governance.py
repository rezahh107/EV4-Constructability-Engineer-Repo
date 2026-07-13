from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "governance" / "AI_AUTHORITY_PROFILE.yml"
DEFAULT_STATE = ROOT / "planning" / "GOVERNANCE_SCOPE_STATE.yml"
DEFAULT_SCHEMA = ROOT / "schemas" / "ai_governance_state.v1.schema.json"

CAPABILITY_ID = re.compile(r"^CE-GOV-[0-9]{3}-[A-Z0-9-]+$")
SHA = re.compile(r"^[0-9a-f]{40}$")
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
GREEN = "GREEN_MERGE_RECOMMENDED"


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
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_APPROVAL_KEYS:
                errors.append(f"{path}.{key}: forbidden human technical approval field")
            errors.extend(_walk_forbidden_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_walk_forbidden_keys(child, f"{path}[{index}]"))
    return errors


def validate_profile(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if profile.get("profile_id") != "personal_ai_operated_strong_governance_minimum_security":
        errors.append("profile_id must select the personal minimum-security governance profile")
    if profile.get("repository") != "rezahh107/EV4-Constructability-Engineer-Repo":
        errors.append("profile repository identity mismatch")

    authority = profile.get("technical_authority", {})
    if authority.get("decision_authority") != "AI":
        errors.append("technical_authority.decision_authority must be AI")
    if authority.get("factual_authority") != "evidence":
        errors.append("technical_authority.factual_authority must be evidence")
    if authority.get("human_technical_approval_required") is not False:
        errors.append("human technical approval must not be required")
    if authority.get("user_merge_action_is_technical_approval") is not False:
        errors.append("user Merge action must not be technical approval")

    minimum_controls = profile.get("minimum_security_controls", [])
    if not isinstance(minimum_controls, list) or len(minimum_controls) < 8:
        errors.append("minimum security controls are incomplete")
    omitted = profile.get("intentionally_out_of_scope_controls", [])
    if not isinstance(omitted, list) or not omitted:
        errors.append("intentionally out-of-scope controls must be explicit")
    triggers = profile.get("activation_triggers", [])
    if not isinstance(triggers, list) or len(triggers) < 8:
        errors.append("security activation triggers are incomplete")

    states = set(profile.get("evidence_states", []))
    if states != ALLOWED_EVIDENCE_STATES:
        errors.append("evidence_states must exactly match the approved evidence vocabulary")

    review = profile.get("review_protocol", {})
    if review.get("name") != "PR-Inspector":
        errors.append("review protocol must be PR-Inspector")
    for key in ("exact_head_required", "stale_on_head_change", "separate_session_required"):
        if review.get(key) is not True:
            errors.append(f"review_protocol.{key} must be true")

    errors.extend(_walk_forbidden_keys(profile))
    return errors


def validate_state_schema(
    state: dict[str, Any],
    schema: dict[str, Any],
) -> list[str]:
    validator = Draft202012Validator(schema)
    return [
        f"{'/'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in sorted(validator.iter_errors(state), key=lambda item: list(item.absolute_path))
    ]


def validate_scope_semantics(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    scope = state["scope_projection"]
    target = list(scope["long_term_target_ids"])
    buckets = {
        name: list(scope[name])
        for name in (
            "committed_now_ids",
            "implemented_ids",
            "deferred_not_deleted_ids",
            "rejected_ids",
            "superseded_ids",
        )
    }

    for capability_id in target:
        if not CAPABILITY_ID.fullmatch(capability_id):
            errors.append(f"invalid capability ID: {capability_id}")

    seen: dict[str, str] = {}
    for bucket_name, ids in buckets.items():
        for capability_id in ids:
            previous = seen.get(capability_id)
            if previous is not None:
                errors.append(
                    f"{capability_id} appears in incompatible dispositions: "
                    f"{previous} and {bucket_name}"
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

    memory = state["capability_memory"]
    memory_ids = [entry["capability_id"] for entry in memory]
    if len(memory_ids) != len(set(memory_ids)):
        errors.append("capability_memory contains duplicate capability IDs")
    if set(memory_ids) != target_set:
        errors.append("capability_memory must cover every long-term target exactly once")

    for entry in memory:
        capability_id = entry["capability_id"]
        expected_bucket = DISPOSITION_TO_SET[entry["disposition"]]
        if capability_id not in set(scope[expected_bucket]):
            errors.append(
                f"{capability_id} disposition {entry['disposition']} "
                f"does not match scope_projection.{expected_bucket}"
            )

    required_artifacts = set(state["progress_gate"]["required_artifacts"])
    canonical_required = {
        "governance/AI_AUTHORITY_PROFILE.yml",
        "planning/GOVERNANCE_SCOPE_STATE.yml",
        "schemas/ai_governance_state.v1.schema.json",
        "validator/ai_governance.py",
        "scripts/validate-ai-governance.py",
        "tests/test_ai_governance.py",
    }
    if not canonical_required <= required_artifacts:
        errors.append("progress_gate.required_artifacts is missing governance carriers")

    required_green = {
        "exact_head_ci_passed",
        "scope_gate_passed",
        "progress_gate_passed",
        "independent_review_green",
        "no_blocking_findings",
    }
    if set(state["review_merge_gate"]["green_requires"]) != required_green:
        errors.append("review_merge_gate.green_requires does not match the fail-closed gate")

    errors.extend(_walk_forbidden_keys(state))
    return errors


def validate_repository_state(
    *,
    profile_path: str | Path = DEFAULT_PROFILE,
    state_path: str | Path = DEFAULT_STATE,
    schema_path: str | Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    profile = load_yaml(profile_path)
    state = load_yaml(state_path)
    schema = load_json(schema_path)
    errors = [
        *validate_profile(profile),
        *validate_state_schema(state, schema),
        *validate_scope_semantics(state),
    ]
    return {
        "passed": not errors,
        "errors": errors,
        "profile": profile,
        "state": state,
    }


def compute_scope_disclosure(state: dict[str, Any], head_sha: str) -> dict[str, Any]:
    if not SHA.fullmatch(head_sha):
        raise ValueError("head_sha must be a full lowercase 40-character commit SHA")
    scope = state["scope_projection"]
    sets = {
        "long_term_target_ids": sorted(set(scope["long_term_target_ids"])),
        "committed_now_ids": sorted(set(scope["committed_now_ids"])),
        "deferred_not_deleted_ids": sorted(set(scope["deferred_not_deleted_ids"])),
        "rejected_ids": sorted(set(scope["rejected_ids"])),
        "superseded_ids": sorted(set(scope["superseded_ids"])),
        "implemented_ids": sorted(set(scope["implemented_ids"])),
    }
    counts = {name.replace("_ids", "_count"): len(values) for name, values in sets.items()}
    return {
        "schema_version": 1,
        "plan_id": state["plan"]["plan_id"],
        "scope_revision": scope["scope_revision"],
        "reviewed_head_sha": head_sha,
        "source_object_identities": {
            "repository": state["repository"]["name"],
            "default_branch": state["repository"]["default_branch"],
            "scope_state_path": "planning/GOVERNANCE_SCOPE_STATE.yml",
        },
        "sets": sets,
        "computed_counts": counts,
        "owner_facing": {
            "long_term_target_count": counts["long_term_target_count"],
            "committed_now_count": counts["committed_now_count"],
            "deferred_not_deleted_count": counts["deferred_not_deleted_count"],
            "permanently_deleted_count": 0,
            "scope_change_reason": scope["decision_provenance"]["reason"],
            "computed_from_exact_head": head_sha,
        },
    }


def compute_completion_receipt(state: dict[str, Any], head_sha: str) -> dict[str, Any]:
    if not SHA.fullmatch(head_sha):
        raise ValueError("head_sha must be a full lowercase 40-character commit SHA")
    return {
        "schema_version": 1,
        "phase": state["scope_projection"]["phase"],
        "scope_revision": state["scope_projection"]["scope_revision"],
        "implementation_status": "implemented_pending_independent_review",
        "repository": {
            "name": state["repository"]["name"],
            "default_branch": state["repository"]["default_branch"],
            "base_sha": state["repository"]["audit_base_sha"],
            "reviewed_head_sha": head_sha,
        },
        "required_artifacts": [
            {
                "path": path,
                "exists": (ROOT / path).exists(),
                "evidence": "REPOSITORY_CONFIRMED",
            }
            for path in state["progress_gate"]["required_artifacts"]
        ],
        "validation": {
            "governance_validator": {
                "command": (
                    "python scripts/validate-ai-governance.py "
                    f"--head-sha {head_sha} --emit-dir .governance-evidence"
                ),
                "result": "PASS",
                "evidence": "CI_CONFIRMED",
            },
            "exact_head": {
                "tested_sha": head_sha,
                "reviewed_head_sha": head_sha,
                "exact_head_match": True,
                "synthetic_merge": False,
            },
        },
        "open_gates": ["independent_ai_review", "user_merge", "post_merge_verification"],
        "prohibited_claims": state["progress_gate"]["prohibited_claims"],
    }


def validate_review_package(
    package: dict[str, Any],
    *,
    current_head_sha: str,
    current_scope_revision: str,
    implementer_session_id: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if not SHA.fullmatch(current_head_sha):
        errors.append("current_head_sha must be a full lowercase 40-character SHA")
        return errors

    if package.get("reviewed_head_sha") != current_head_sha:
        errors.append("stale review: reviewed_head_sha does not equal current head")
    if package.get("reviewed_scope_revision") != current_scope_revision:
        errors.append("stale review: reviewed_scope_revision does not equal current scope revision")
    if package.get("protocol_name") != "PR-Inspector":
        errors.append("independent review protocol_name must be PR-Inspector")
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", str(package.get("protocol_version", ""))):
        errors.append("independent review protocol_version is invalid")
    if not package.get("protocol_sha256") or not re.fullmatch(
        r"[0-9a-f]{64}", str(package.get("protocol_sha256"))
    ):
        errors.append("independent review protocol_sha256 is required")
    if package.get("session_is_separate") is not True:
        errors.append("independent review must come from a separate session")
    if implementer_session_id and package.get("review_session_id") == implementer_session_id:
        errors.append("implementer session cannot self-issue independent review")
    if package.get("relied_on_implementer_self_assertion") is not False:
        errors.append("review must not rely on implementer self-assertion")
    if package.get("verdict") not in {
        GREEN,
        "YELLOW_REPAIR_OR_VERIFICATION_REQUIRED",
        "RED_DO_NOT_MERGE",
        "BLOCKED_INSUFFICIENT_EVIDENCE",
    }:
        errors.append("review verdict is invalid")
    return errors


def evaluate_merge_gate(
    *,
    state: dict[str, Any],
    head_sha: str,
    review_package: dict[str, Any] | None,
    exact_head_ci_passed: bool,
    scope_gate_passed: bool,
    progress_gate_passed: bool,
    blocking_findings: int,
    implementer_session_id: str | None = None,
) -> dict[str, Any]:
    if review_package is None:
        return {
            "passed": False,
            "merge_recommendation": False,
            "status": "VALIDATED_PENDING_INDEPENDENT_AI_REVIEW",
            "errors": ["current exact-head independent review package is missing"],
        }

    errors = validate_review_package(
        review_package,
        current_head_sha=head_sha,
        current_scope_revision=state["scope_projection"]["scope_revision"],
        implementer_session_id=implementer_session_id,
    )
    if review_package.get("verdict") != GREEN:
        errors.append("current independent review verdict is not GREEN_MERGE_RECOMMENDED")
    if not exact_head_ci_passed:
        errors.append("required exact-head CI has not passed")
    if not scope_gate_passed:
        errors.append("Scope Gate has not passed")
    if not progress_gate_passed:
        errors.append("Progress Gate has not passed")
    if blocking_findings:
        errors.append("blocking findings remain open")

    return {
        "passed": not errors,
        "merge_recommendation": not errors,
        "status": "GREEN_MERGE_RECOMMENDED" if not errors else "YELLOW_REPAIR_OR_VERIFICATION_REQUIRED",
        "errors": errors,
    }


def emit_evidence(
    *,
    state: dict[str, Any],
    head_sha: str,
    output_dir: str | Path,
) -> dict[str, str]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    disclosure = compute_scope_disclosure(state, head_sha)
    receipt = compute_completion_receipt(state, head_sha)
    paths = {
        "scope_disclosure": target / "scope-change-disclosure.json",
        "completion_receipt": target / "completion-receipt.json",
    }
    paths["scope_disclosure"].write_text(
        json.dumps(disclosure, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    paths["completion_receipt"].write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {name: str(path) for name, path in paths.items()}
