from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ai_governance_core import (
    ACTIVATION_TRIGGERS_V1,
    ALLOWED_EVIDENCE_STATES,
    CANONICAL_REQUIRED_ARTIFACTS,
    DEFAULT_PROFILE,
    DEFAULT_SCHEMA,
    DEFAULT_STATE,
    EXPECTED_INSPECTOR_REPOSITORY,
    EXPECTED_PROFILE_ID,
    EXPECTED_PROFILE_VERSION,
    EXPECTED_REPOSITORY,
    GREEN,
    INTENTIONAL_EXCLUSIONS_V1,
    MINIMUM_SECURITY_CONTROLS_V1,
    REQUIRED_GREEN_PREDICATES,
    REQUIRED_REVIEW_ARTIFACTS,
    ValidatedGovernanceState,
    is_validated_governance_state,
    load_json,
    load_yaml,
    validate_profile,
    validate_repository_state,
    validate_required_artifacts,
    validate_scope_semantics,
    validate_state_schema,
)
from .ai_governance_evidence import (
    VerifiedGateEvidence,
    compute_completion_receipt,
    compute_scope_disclosure,
    derive_gate_evidence,
    is_verified_gate_evidence,
    record_ci_context,
)
from .ai_governance_review import (
    CanonicalReviewBundleEvidence,
    VerifiedReviewCapability,
    inspect_canonical_review_bundle,
    is_canonical_review_bundle_evidence,
    is_verified_review_capability,
    verify_pr_inspector_review_bundle,
)


def evaluate_merge_gate(
    *,
    gate_evidence: VerifiedGateEvidence | object,
    review_capability: VerifiedReviewCapability | object | None,
) -> dict[str, Any]:
    errors: list[str] = []
    if not is_verified_gate_evidence(gate_evidence):
        return {
            "passed": False,
            "merge_recommendation": False,
            "status": "FAIL-CLOSED",
            "errors": ["merge gate requires verifier-created gate evidence; mappings and booleans are rejected"],
        }
    if review_capability is None:
        return {
            "passed": False,
            "merge_recommendation": False,
            "status": "IMPLEMENTED_PENDING_REREVIEW",
            "errors": ["authoritative current-head PR Inspector completion is missing"],
        }
    if not is_verified_review_capability(review_capability):
        return {
            "passed": False,
            "merge_recommendation": False,
            "status": "FAIL-CLOSED",
            "errors": [
                "merge gate requires official PR Inspector VerifiedReviewCompletion provenance; "
                "plain mappings and locally verified bundles are insufficient"
            ],
        }
    if (
        review_capability.repository,
        review_capability.pr_number,
        review_capability.head_sha,
        review_capability.scope_revision,
    ) != (
        gate_evidence.repository,
        gate_evidence.pr_number,
        gate_evidence.head_sha,
        gate_evidence.scope_revision,
    ):
        errors.append("stale review: repository/PR/head/scope identity mismatch")
    if review_capability.technical_status != GREEN:
        errors.append("current authoritative review verdict is not GREEN_MERGE_RECOMMENDED")
    if review_capability.blocking_findings_count != 0:
        errors.append("blocking findings remain in the authoritative review package")
    if not gate_evidence.scope_gate_passed:
        errors.append("Scope Gate has not passed")
    if not gate_evidence.progress_gate_passed:
        errors.append("Progress Gate has not passed")
    if not gate_evidence.exact_head_ci_passed:
        errors.append("authoritative final exact-head CI success is not attached")
    return {
        "passed": not errors,
        "merge_recommendation": not errors,
        "status": GREEN if not errors else "YELLOW_REPAIR_OR_VERIFICATION_REQUIRED",
        "errors": errors,
    }


def emit_evidence(
    *,
    gate_evidence: VerifiedGateEvidence,
    output_dir: str | Path,
    review_capability: VerifiedReviewCapability | None = None,
) -> dict[str, str]:
    if not is_verified_gate_evidence(gate_evidence):
        raise ValueError("evidence emission requires verifier-created gate evidence")
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    disclosure = compute_scope_disclosure(gate_evidence.state, gate_evidence.head_sha)
    receipt = compute_completion_receipt(gate_evidence, review_capability)
    gate_record = {
        "schema_version": 1,
        "repository": gate_evidence.repository,
        "pr_number": gate_evidence.pr_number,
        "head_sha": gate_evidence.head_sha,
        "scope_revision": gate_evidence.scope_revision,
        "scope_gate_passed": gate_evidence.scope_gate_passed,
        "progress_gate_passed": gate_evidence.progress_gate_passed,
        "exact_head_context_verified": gate_evidence.exact_head_context_verified,
        "exact_head_ci_passed": gate_evidence.exact_head_ci_passed,
        "evidence_state": gate_evidence.evidence_state,
        "ci_context_sha256": gate_evidence.ci_context_sha256,
        "artifact_sha256": {
            record["path"]: record["sha256"] for record in gate_evidence.artifact_records
        },
        "diagnostics": list(gate_evidence.diagnostics),
    }
    paths = {
        "scope_disclosure": target / "scope-change-disclosure.json",
        "completion_receipt": target / "completion-receipt.json",
        "gate_evidence": target / "governance-gate-evidence.json",
    }
    for key, value in (
        ("scope_disclosure", disclosure),
        ("completion_receipt", receipt),
        ("gate_evidence", gate_record),
    ):
        paths[key].write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return {name: str(path) for name, path in paths.items()}
