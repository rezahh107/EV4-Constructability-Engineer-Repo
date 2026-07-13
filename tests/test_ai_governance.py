from __future__ import annotations

import json
from pathlib import Path

from validator.ai_governance import (
    DEFAULT_PROFILE,
    DEFAULT_SCHEMA,
    DEFAULT_STATE,
    compute_completion_receipt,
    compute_scope_disclosure,
    emit_evidence,
    evaluate_merge_gate,
    load_json,
    load_yaml,
    validate_profile,
    validate_repository_state,
    validate_review_package,
    validate_scope_semantics,
    validate_state_schema,
)

ROOT = Path(__file__).resolve().parents[1]
HEAD = "f" * 40


def test_repository_governance_state_is_valid() -> None:
    result = validate_repository_state()
    assert result["passed"], result["errors"]


def test_scope_projection_rejects_silent_capability_deletion() -> None:
    state = load_yaml(ROOT / "fixtures" / "governance" / "invalid" / "silent-scope-deletion.yml")
    errors = validate_scope_semantics(state)
    assert any("silent capability deletion" in error for error in errors)


def test_scope_projection_rejects_incompatible_dispositions() -> None:
    state = load_yaml(DEFAULT_STATE)
    capability_id = state["scope_projection"]["implemented_ids"][0]
    state["scope_projection"]["committed_now_ids"].append(capability_id)
    errors = validate_scope_semantics(state)
    assert any("incompatible dispositions" in error for error in errors)


def test_capability_memory_must_match_projection_disposition() -> None:
    state = load_yaml(DEFAULT_STATE)
    state["capability_memory"][0]["disposition"] = "committed_now"
    errors = validate_scope_semantics(state)
    assert any("does not match" in error for error in errors)


def test_schema_rejects_human_technical_approval_field() -> None:
    state = load_yaml(ROOT / "fixtures" / "governance" / "invalid" / "human-approval.yml")
    schema = load_json(DEFAULT_SCHEMA)
    errors = validate_state_schema(state, schema)
    assert errors


def test_profile_rejects_human_technical_approval_requirement() -> None:
    profile = load_yaml(DEFAULT_PROFILE)
    profile["technical_authority"]["human_technical_approval_required"] = True
    errors = validate_profile(profile)
    assert any("must not be required" in error for error in errors)


def test_scope_disclosure_counts_are_computed_and_exact_head_bound() -> None:
    state = load_yaml(DEFAULT_STATE)
    disclosure = compute_scope_disclosure(state, HEAD)
    assert disclosure["reviewed_head_sha"] == HEAD
    assert disclosure["computed_counts"]["long_term_target_count"] == 5
    assert disclosure["computed_counts"]["committed_now_count"] == 4
    assert disclosure["computed_counts"]["implemented_count"] == 1
    assert disclosure["owner_facing"]["permanently_deleted_count"] == 0


def test_completion_receipt_is_pending_independent_review() -> None:
    state = load_yaml(DEFAULT_STATE)
    receipt = compute_completion_receipt(state, HEAD)
    assert receipt["implementation_status"] == "implemented_pending_independent_review"
    assert receipt["repository"]["reviewed_head_sha"] == HEAD
    assert receipt["validation"]["exact_head"]["exact_head_match"] is True
    assert receipt["validation"]["exact_head"]["synthetic_merge"] is False
    assert "independent_ai_review" in receipt["open_gates"]


def test_evidence_files_are_emitted(tmp_path: Path) -> None:
    state = load_yaml(DEFAULT_STATE)
    emitted = emit_evidence(state=state, head_sha=HEAD, output_dir=tmp_path)
    disclosure = json.loads(Path(emitted["scope_disclosure"]).read_text(encoding="utf-8"))
    receipt = json.loads(Path(emitted["completion_receipt"]).read_text(encoding="utf-8"))
    assert disclosure["reviewed_head_sha"] == HEAD
    assert receipt["repository"]["reviewed_head_sha"] == HEAD


def test_stale_review_package_is_rejected() -> None:
    package = load_json(ROOT / "fixtures" / "governance" / "invalid" / "stale-review.json")
    errors = validate_review_package(
        package,
        current_head_sha=HEAD,
        current_scope_revision="CE-GOV-ALL-v2",
    )
    assert any("stale review" in error for error in errors)


def test_implementer_session_cannot_self_review() -> None:
    package = load_json(ROOT / "fixtures" / "governance" / "invalid" / "self-review.json")
    errors = validate_review_package(
        package,
        current_head_sha=HEAD,
        current_scope_revision="CE-GOV-ALL-v2",
        implementer_session_id="implementer-session-001",
    )
    assert any("cannot self-issue" in error for error in errors)


def test_missing_review_stays_pending_not_green() -> None:
    state = load_yaml(DEFAULT_STATE)
    result = evaluate_merge_gate(
        state=state,
        head_sha=HEAD,
        review_package=None,
        exact_head_ci_passed=True,
        scope_gate_passed=True,
        progress_gate_passed=True,
        blocking_findings=0,
    )
    assert result["passed"] is False
    assert result["merge_recommendation"] is False
    assert result["status"] == "VALIDATED_PENDING_INDEPENDENT_AI_REVIEW"


def test_green_review_still_requires_all_merge_predicates() -> None:
    state = load_yaml(DEFAULT_STATE)
    package = load_json(ROOT / "fixtures" / "governance" / "valid" / "independent-review-green.json")
    result = evaluate_merge_gate(
        state=state,
        head_sha=HEAD,
        review_package=package,
        exact_head_ci_passed=False,
        scope_gate_passed=True,
        progress_gate_passed=True,
        blocking_findings=0,
    )
    assert result["passed"] is False
    assert any("exact-head CI" in error for error in result["errors"])


def test_valid_exact_head_independent_review_can_pass_merge_gate() -> None:
    state = load_yaml(DEFAULT_STATE)
    package = load_json(ROOT / "fixtures" / "governance" / "valid" / "independent-review-green.json")
    result = evaluate_merge_gate(
        state=state,
        head_sha=HEAD,
        review_package=package,
        exact_head_ci_passed=True,
        scope_gate_passed=True,
        progress_gate_passed=True,
        blocking_findings=0,
        implementer_session_id="implementer-session-001",
    )
    assert result["passed"] is True
    assert result["status"] == "GREEN_MERGE_RECOMMENDED"


def test_security_activation_triggers_are_required() -> None:
    profile = load_yaml(DEFAULT_PROFILE)
    profile["activation_triggers"] = []
    errors = validate_profile(profile)
    assert any("activation triggers" in error for error in errors)
