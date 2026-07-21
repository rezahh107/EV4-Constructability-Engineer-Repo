from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _yaml_block(text: str, key: str) -> str:
    start = text.index(key)
    end = text.index("```", start)
    return text[start:end]


def test_pr37_status_reconciliation_preserves_history_and_records_live_state() -> None:
    text = (ROOT / "STATUS.md").read_text(encoding="utf-8")

    current = _yaml_block(text, "project_status:")
    assert (
        "ce_project_gate_exporter_command: "
        "implemented_merged_pending_fresh_independent_rereview"
    ) in current
    assert (
        "ce_project_gate_exporter_post_merge_audit: "
        "repair_merged_content_equivalent_review_not_observed"
    ) in current
    assert "ce_project_gate_exporter_exact_pr_head_validation: confirmed" in current
    assert "ce_project_gate_exporter_exact_merged_main_ci: not_observed" in current
    assert (
        "ce_project_gate_exporter_post_merge_content_verification: "
        "confirmed_content_equivalent"
    ) in current
    assert "ce_project_gate_exporter_fresh_independent_review: not_observed" in current
    assert "ce_project_gate_exporter_findings_closed: false" in current
    assert "production_ready: false" in current
    assert "post_merge_audit_repair_in_pr_pending_exact_head_validation_and_review" not in current

    historical = _yaml_block(text, "CE_02_POST_MERGE_EXPORTER_AUDIT:")
    assert "exact_head_validation: pending" in historical
    assert "independent_repair_review: pending" in historical
    assert "repair_merged: false" in historical

    reconciliation = _yaml_block(
        text,
        "CE_02_POST_MERGE_STATUS_RECONCILIATION:",
    )
    expected_facts = (
        "pull_request: 37",
        "pull_request_state: merged",
        "validated_head_sha: 677ff32edc8bca3e4c4156031d72b89a9c0a26d5",
        "merge_commit_sha: 6650c31304e5a0472b276c36018c1df8f42ac983",
        "current_main_sha_at_reconciliation: 6650c31304e5a0472b276c36018c1df8f42ac983",
        "current_main_relationship_to_merge_commit: identical",
        "merge_commit_file_delta_from_validated_head: none",
        "run_id: 29563815214",
        "run_id: 29563815485",
        "exact_merged_main_ci: not_observed",
        "implementation_merged: true",
        "repair_merged: true",
        "post_merge_content_verification: confirmed",
        "fresh_independent_review_on_repaired_head: not_observed",
        "independent_review: insufficient_evidence",
        "findings_closed: false",
        "project_gate_runtime_acceptance: unverified",
        "real_non_synthetic_cross_repository_handoff: unverified",
        "builder_acceptance: unverified",
        "responsive_completion: unverified",
        "deployment: unverified",
    )
    for fact in expected_facts:
        assert fact in reconciliation
