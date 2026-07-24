from __future__ import annotations

import copy
from typing import Any, Final

from .action_contract_registry import ACTION_CONTRACTS

PRE_BUILDER_STATIC = "pre_builder_static"
PRE_BUILDER_CAPABILITY = "pre_builder_capability"
POST_BUILDER_RUNTIME = "post_builder_runtime"


def _policy(
    *,
    authority_owner: str,
    lifecycle_phase: str,
    evaluator_kind: str,
    allowed_evidence_modes: tuple[str, ...],
    required_semantics: tuple[str, ...],
    applicable_rule: str,
    evaluator: str,
    builder_handoff_effect: str,
    final_completion_effect: str,
    missing_status: str,
) -> dict[str, Any]:
    return {
        "authority_owner": authority_owner,
        "lifecycle_phase": lifecycle_phase,
        "evaluator_kind": evaluator_kind,
        "allowed_evidence_modes": allowed_evidence_modes,
        "required_semantics": required_semantics,
        "applicable_rule": applicable_rule,
        "evaluator": evaluator,
        "builder_handoff_effect": builder_handoff_effect,
        "final_completion_effect": final_completion_effect,
        # Compatibility keys consumed by the existing deterministic payload validator.
        "success_modes": allowed_evidence_modes,
        "missing_status": missing_status,
        "blocking": lifecycle_phase != POST_BUILDER_RUNTIME,
        "may_authorize_builder_handoff": lifecycle_phase != POST_BUILDER_RUNTIME,
    }


# One canonical phase-aware claim registry.
CLAIM_POLICIES: Final[dict[str, dict[str, Any]]] = {
    "geometry": _policy(
        authority_owner="CE",
        lifecycle_phase=PRE_BUILDER_STATIC,
        evaluator_kind="attributed_judgment_or_original_source_parser",
        allowed_evidence_modes=("ATTRIBUTED_ENGINEERING_JUDGMENT", "VERIFIED_ARTIFACT"),
        required_semantics=("anchor_model", "coordinate_or_layout_model", "derivation_method"),
        applicable_rule="R03_GEOMETRY_MUST_BE_PROVEN",
        evaluator="evaluate_geometry",
        builder_handoff_effect="require_satisfied",
        final_completion_effect="carry_forward",
        missing_status="insufficient_evidence",
    ),
    "overlay_strategy": _policy(
        authority_owner="CE",
        lifecycle_phase=PRE_BUILDER_STATIC,
        evaluator_kind="attributed_judgment_or_original_source_parser",
        allowed_evidence_modes=("ATTRIBUTED_ENGINEERING_JUDGMENT", "VERIFIED_ARTIFACT"),
        required_semantics=(
            "containment_model",
            "positioning_model",
            "stacking_model",
            "derivation_method",
        ),
        applicable_rule="R05_OVERLAY_STRATEGY_MUST_BE_PROVEN",
        evaluator="evaluate_overlay_strategy",
        builder_handoff_effect="require_satisfied",
        final_completion_effect="carry_forward",
        missing_status="insufficient_evidence",
    ),
    "responsive_strategy": _policy(
        authority_owner="CE",
        lifecycle_phase=PRE_BUILDER_STATIC,
        evaluator_kind="attributed_engineering_judgment",
        allowed_evidence_modes=("ATTRIBUTED_ENGINEERING_JUDGMENT",),
        required_semantics=("breakpoint_strategy", "layout_adaptation", "derivation_method"),
        applicable_rule="R06_RESPONSIVE_ACTION_REQUIRES_STRATEGY_OR_BLOCK",
        evaluator="evaluate_responsive_strategy",
        builder_handoff_effect="require_satisfied",
        final_completion_effect="carry_forward",
        missing_status="insufficient_evidence",
    ),
    "accessibility_strategy": _policy(
        authority_owner="CE",
        lifecycle_phase=PRE_BUILDER_STATIC,
        evaluator_kind="attributed_engineering_judgment",
        allowed_evidence_modes=("ATTRIBUTED_ENGINEERING_JUDGMENT",),
        required_semantics=("semantic_strategy", "keyboard_strategy", "derivation_method"),
        applicable_rule="R16_ACCESSIBILITY_CLAIM_REQUIRES_EVIDENCE",
        evaluator="evaluate_accessibility_strategy",
        builder_handoff_effect="require_satisfied",
        final_completion_effect="carry_forward",
        missing_status="insufficient_evidence",
    ),
    "placeholder_policy": _policy(
        authority_owner="CE",
        lifecycle_phase=PRE_BUILDER_STATIC,
        evaluator_kind="attributed_engineering_judgment",
        allowed_evidence_modes=("ATTRIBUTED_ENGINEERING_JUDGMENT",),
        required_semantics=("premises", "derivation_method"),
        applicable_rule="R04_ASSET_SOURCE_OR_PLACEHOLDER",
        evaluator="evaluate_placeholder_policy",
        builder_handoff_effect="require_satisfied",
        final_completion_effect="carry_forward",
        missing_status="insufficient_evidence",
    ),
    "interaction_approval": _policy(
        authority_owner="Architect",
        lifecycle_phase=PRE_BUILDER_STATIC,
        evaluator_kind="canonical_architect_decision",
        allowed_evidence_modes=("VERIFIED_ARCHITECT_DECISION",),
        required_semantics=(),
        applicable_rule="R07_INTERACTION_REQUIRES_APPROVAL",
        evaluator="evaluate_architect_decision",
        builder_handoff_effect="require_satisfied",
        final_completion_effect="carry_forward",
        missing_status="architect_decision_required",
    ),
    "dynamic_loop_approval": _policy(
        authority_owner="Architect",
        lifecycle_phase=PRE_BUILDER_STATIC,
        evaluator_kind="canonical_architect_decision",
        allowed_evidence_modes=("VERIFIED_ARCHITECT_DECISION",),
        required_semantics=(),
        applicable_rule="R08_DYNAMIC_LOOP_REQUIRES_APPROVAL",
        evaluator="evaluate_architect_decision",
        builder_handoff_effect="require_satisfied",
        final_completion_effect="carry_forward",
        missing_status="architect_decision_required",
    ),
    "asset_source": _policy(
        authority_owner="CE",
        lifecycle_phase=PRE_BUILDER_CAPABILITY,
        evaluator_kind="original_source_parser",
        allowed_evidence_modes=("VERIFIED_ARTIFACT",),
        required_semantics=("subject_suitability",),
        applicable_rule="R04_ASSET_SOURCE_OR_PLACEHOLDER",
        evaluator="evaluate_asset_source",
        builder_handoff_effect="require_satisfied",
        final_completion_effect="carry_forward",
        missing_status="insufficient_evidence",
    ),
    "ui_control_path": _policy(
        authority_owner="CE",
        lifecycle_phase=PRE_BUILDER_CAPABILITY,
        evaluator_kind="original_source_parser",
        allowed_evidence_modes=("VERIFIED_ARTIFACT",),
        required_semantics=("control_path",),
        applicable_rule="R10_UI_CONTROL_PATH_REQUIRES_EVIDENCE",
        evaluator="evaluate_ui_control_path",
        builder_handoff_effect="require_satisfied",
        final_completion_effect="carry_forward",
        missing_status="insufficient_evidence",
    ),
    # Existing public IDs keep their runtime-outcome meaning. They are not strategy claims.
    "responsive_behavior": _policy(
        authority_owner="Responsive/Builder runtime",
        lifecycle_phase=POST_BUILDER_RUNTIME,
        evaluator_kind="runtime_obligation",
        allowed_evidence_modes=("DOWNSTREAM_TEST_OBLIGATION", "VERIFIED_TOOL_EXECUTION"),
        required_semantics=(),
        applicable_rule="R06_RESPONSIVE_ACTION_REQUIRES_STRATEGY_OR_BLOCK",
        evaluator="emit_runtime_obligation",
        builder_handoff_effect="require_complete_obligation",
        final_completion_effect="require_executed_pass",
        missing_status="downstream_validation_required",
    ),
    "interaction_validation": _policy(
        authority_owner="Builder/runtime validation",
        lifecycle_phase=POST_BUILDER_RUNTIME,
        evaluator_kind="runtime_obligation",
        allowed_evidence_modes=("DOWNSTREAM_TEST_OBLIGATION", "VERIFIED_TOOL_EXECUTION"),
        required_semantics=(),
        applicable_rule="R07_INTERACTION_REQUIRES_APPROVAL",
        evaluator="emit_runtime_obligation",
        builder_handoff_effect="require_complete_obligation",
        final_completion_effect="require_executed_pass",
        missing_status="downstream_validation_required",
    ),
    "accessibility": _policy(
        authority_owner="Responsive/accessibility runtime",
        lifecycle_phase=POST_BUILDER_RUNTIME,
        evaluator_kind="runtime_obligation",
        allowed_evidence_modes=("DOWNSTREAM_TEST_OBLIGATION", "VERIFIED_TOOL_EXECUTION"),
        required_semantics=(),
        applicable_rule="R16_ACCESSIBILITY_CLAIM_REQUIRES_EVIDENCE",
        evaluator="emit_runtime_obligation",
        builder_handoff_effect="require_complete_obligation",
        final_completion_effect="require_executed_pass",
        missing_status="downstream_validation_required",
    ),
    "QA": _policy(
        authority_owner="Builder/QA runtime",
        lifecycle_phase=POST_BUILDER_RUNTIME,
        evaluator_kind="runtime_obligation",
        allowed_evidence_modes=("DOWNSTREAM_TEST_OBLIGATION", "VERIFIED_TOOL_EXECUTION"),
        required_semantics=(),
        applicable_rule="R17_QA_REQUIRES_EXECUTION_EVIDENCE",
        evaluator="emit_runtime_obligation",
        builder_handoff_effect="require_complete_obligation",
        final_completion_effect="require_executed_pass",
        missing_status="downstream_validation_required",
    ),
}


# Compatibility view derived from the canonical Action Contract Registry.
ACTION_CLAIMS: Final[dict[str, tuple[str, ...]]] = {
    action_type: tuple(str(value) for value in contract["required_claims"])
    for action_type, contract in ACTION_CONTRACTS.items()
}

PROPOSED_ACTION_HINTS: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("overlay", ("geometry", "overlay_strategy")),
    ("absolute", ("geometry", "overlay_strategy")),
    ("connector", ("geometry",)),
    ("responsive", ("responsive_strategy", "responsive_behavior")),
    ("mobile", ("responsive_strategy", "responsive_behavior")),
    (
        "interaction",
        (
            "interaction_approval",
            "accessibility_strategy",
            "accessibility",
            "interaction_validation",
        ),
    ),
    ("dynamic loop", ("dynamic_loop_approval",)),
    ("asset", ("asset_source",)),
    ("placeholder", ("placeholder_policy",)),
    ("ui control", ("ui_control_path",)),
    ("accessibility", ("accessibility_strategy", "accessibility")),
)


def policy_projection(claim_id: str) -> dict[str, Any]:
    return copy.deepcopy(CLAIM_POLICIES[claim_id])


def derive_action_claims(action_type: str) -> tuple[str, ...] | None:
    return ACTION_CLAIMS.get(action_type)


def mutable_claim_policies() -> dict[str, dict[str, Any]]:
    return copy.deepcopy(CLAIM_POLICIES)


def is_post_builder_claim(claim_id: str) -> bool:
    policy = CLAIM_POLICIES.get(claim_id)
    return bool(policy and policy["lifecycle_phase"] == POST_BUILDER_RUNTIME)


__all__ = [
    "ACTION_CLAIMS",
    "CLAIM_POLICIES",
    "POST_BUILDER_RUNTIME",
    "PRE_BUILDER_CAPABILITY",
    "PRE_BUILDER_STATIC",
    "PROPOSED_ACTION_HINTS",
    "derive_action_claims",
    "is_post_builder_claim",
    "mutable_claim_policies",
    "policy_projection",
]
