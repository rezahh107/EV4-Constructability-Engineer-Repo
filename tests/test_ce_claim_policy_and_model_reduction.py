from __future__ import annotations

import importlib.util
from pathlib import Path

from validator.claim_policy_registry import CLAIM_POLICIES

ROOT = Path(__file__).resolve().parents[1]


def _load_report_module():
    path = ROOT / "scripts/report-ce-model-trust-field-reduction.py"
    spec = importlib.util.spec_from_file_location("ce_model_trust_reduction", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_claim_policy_registry_covers_required_authority_surfaces() -> None:
    assert set(CLAIM_POLICIES) == {
        "geometry",
        "overlay_strategy",
        "responsive_behavior",
        "ui_control_path",
        "accessibility",
        "dynamic_loop_approval",
        "interaction_approval",
        "asset_source",
        "placeholder_policy",
        "QA",
        "constructability_status",
        "builder_eligibility",
    }
    for claim_id, policy in CLAIM_POLICIES.items():
        assert set(policy) == {
            "semantic_class",
            "authority_owner",
            "subject_binding_required",
            "admissible_evidence_modes",
            "required_semantics",
            "derivation_rule",
            "unavailable_evidence_behavior",
            "may_authorize_builder_handoff",
        }, claim_id


def test_runtime_only_claims_reject_editor_artifact_substitution() -> None:
    for claim_id in ("responsive_behavior", "accessibility", "QA"):
        policy = CLAIM_POLICIES[claim_id]
        assert policy["authority_owner"] == "downstream_runtime_validation"
        assert policy["admissible_evidence_modes"] == ("VERIFIED_TOOL_EXECUTION",)
        assert policy["unavailable_evidence_behavior"] == (
            "DOWNSTREAM_VALIDATION_REQUIRED"
        )
        assert policy["may_authorize_builder_handoff"] is True


def test_architect_owned_claims_cannot_be_ce_self_approved() -> None:
    for claim_id in ("dynamic_loop_approval", "interaction_approval"):
        policy = CLAIM_POLICIES[claim_id]
        assert policy["authority_owner"] == "Architect"
        assert policy["admissible_evidence_modes"] == (
            "VERIFIED_ARCHITECT_DECISION",
        )


def test_schema_derived_model_workload_reduction_is_exact() -> None:
    report = _load_report_module().build_report()
    assert report["old_model_authored_trust_relevant_fields"] == 40
    assert report["new_model_authored_trust_relevant_fields"] == 0
    assert report["fields_now_runtime_derived"] == 40
    assert report["fields_removed_from_model_input"] == 40
    assert report["reduction_percent"] == 100.0
    assert len(report["old_field_paths"]) == 40
    assert report["new_authority_field_paths"] == []
