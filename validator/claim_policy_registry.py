from __future__ import annotations

import copy
from typing import Any, Final


# One canonical registry. Every evaluator imports this object directly.
CLAIM_POLICIES: Final[dict[str, dict[str, Any]]] = {
    "geometry": {
        "authority_owner": "CE",
        "applicable_rule": "R03_GEOMETRY_MUST_BE_PROVEN",
        "evaluator": "evaluate_geometry",
        "required_semantics": (
            "anchor_model",
            "coordinate_or_layout_model",
            "derivation_method",
        ),
        "success_modes": (
            "ATTRIBUTED_ENGINEERING_JUDGMENT",
            "VERIFIED_ARTIFACT",
        ),
        "missing_status": "insufficient_evidence",
        "blocking": True,
        "may_authorize_builder_handoff": True,
    },
    "asset_source": {
        "authority_owner": "CE",
        "applicable_rule": "R04_ASSET_SOURCE_OR_PLACEHOLDER",
        "evaluator": "evaluate_asset_source",
        "required_semantics": ("subject_suitability",),
        "success_modes": ("VERIFIED_ARTIFACT",),
        "missing_status": "insufficient_evidence",
        "blocking": True,
        "may_authorize_builder_handoff": True,
    },
    "placeholder_policy": {
        "authority_owner": "CE",
        "applicable_rule": "R04_ASSET_SOURCE_OR_PLACEHOLDER",
        "evaluator": "evaluate_placeholder_policy",
        "required_semantics": ("premises", "derivation_method"),
        "success_modes": ("ATTRIBUTED_ENGINEERING_JUDGMENT",),
        "missing_status": "insufficient_evidence",
        "blocking": True,
        "may_authorize_builder_handoff": True,
    },
    "overlay_strategy": {
        "authority_owner": "CE",
        "applicable_rule": "R05_OVERLAY_STRATEGY_MUST_BE_PROVEN",
        "evaluator": "evaluate_overlay_strategy",
        "required_semantics": (
            "containment_model",
            "positioning_model",
            "stacking_model",
            "derivation_method",
        ),
        "success_modes": (
            "ATTRIBUTED_ENGINEERING_JUDGMENT",
            "VERIFIED_ARTIFACT",
        ),
        "missing_status": "insufficient_evidence",
        "blocking": True,
        "may_authorize_builder_handoff": True,
    },
    "responsive_behavior": {
        "authority_owner": "downstream_runtime_validation",
        "applicable_rule": "R06_RESPONSIVE_ACTION_REQUIRES_STRATEGY_OR_BLOCK",
        "evaluator": "evaluate_responsive_behavior",
        "required_semantics": (),
        "success_modes": ("VERIFIED_TOOL_EXECUTION",),
        "missing_status": "downstream_validation_required",
        "blocking": True,
        "may_authorize_builder_handoff": True,
    },
    "interaction_approval": {
        "authority_owner": "Architect",
        "applicable_rule": "R07_INTERACTION_REQUIRES_APPROVAL",
        "evaluator": "evaluate_architect_decision",
        "required_semantics": (),
        "success_modes": ("VERIFIED_ARCHITECT_DECISION",),
        "missing_status": "architect_decision_required",
        "blocking": True,
        "may_authorize_builder_handoff": True,
    },
    "dynamic_loop_approval": {
        "authority_owner": "Architect",
        "applicable_rule": "R08_DYNAMIC_LOOP_REQUIRES_APPROVAL",
        "evaluator": "evaluate_architect_decision",
        "required_semantics": (),
        "success_modes": ("VERIFIED_ARCHITECT_DECISION",),
        "missing_status": "architect_decision_required",
        "blocking": True,
        "may_authorize_builder_handoff": True,
    },
    "ui_control_path": {
        "authority_owner": "CE",
        "applicable_rule": "R10_UI_CONTROL_PATH_REQUIRES_EVIDENCE",
        "evaluator": "evaluate_ui_control_path",
        "required_semantics": ("control_path",),
        "success_modes": ("VERIFIED_ARTIFACT",),
        "missing_status": "insufficient_evidence",
        "blocking": True,
        "may_authorize_builder_handoff": True,
    },
    "accessibility": {
        "authority_owner": "downstream_runtime_validation",
        "applicable_rule": "R16_ACCESSIBILITY_CLAIM_REQUIRES_EVIDENCE",
        "evaluator": "evaluate_accessibility",
        "required_semantics": (),
        "success_modes": ("VERIFIED_TOOL_EXECUTION",),
        "missing_status": "downstream_validation_required",
        "blocking": True,
        "may_authorize_builder_handoff": True,
    },
    "QA": {
        "authority_owner": "downstream_runtime_validation",
        "applicable_rule": "R17_QA_REQUIRES_EXECUTION_EVIDENCE",
        "evaluator": "evaluate_qa",
        "required_semantics": (),
        "success_modes": ("VERIFIED_TOOL_EXECUTION",),
        "missing_status": "downstream_validation_required",
        "blocking": True,
        "may_authorize_builder_handoff": True,
    },
}


# Small explicit rule matrix for the currently supported Builder action vocabulary.
# Empty tuples are explicit repository-defined non-applicability, never accidental emptiness.
ACTION_CLAIMS: Final[dict[str, tuple[str, ...]]] = {
    "preserve_existing": (),
    "inspect_only": (),
    "create_element": ("geometry",),
    "configure_layout": ("geometry",),
    "set_style": ("geometry",),
    "apply_class": ("geometry",),
    "configure_overlay": ("geometry", "overlay_strategy"),
    "set_responsive": ("responsive_behavior",),
    "configure_interaction": ("interaction_approval", "accessibility"),
    "bind_dynamic_loop": ("dynamic_loop_approval",),
    "attach_asset": ("asset_source",),
    "use_placeholder": ("placeholder_policy",),
    "set_ui_control": ("ui_control_path",),
    "run_qa": ("QA",),
}


PROPOSED_ACTION_HINTS: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("overlay", ("geometry", "overlay_strategy")),
    ("absolute", ("geometry", "overlay_strategy")),
    ("connector", ("geometry",)),
    ("responsive", ("responsive_behavior",)),
    ("mobile", ("responsive_behavior",)),
    ("interaction", ("interaction_approval", "accessibility")),
    ("dynamic loop", ("dynamic_loop_approval",)),
    ("asset", ("asset_source",)),
    ("placeholder", ("placeholder_policy",)),
    ("ui control", ("ui_control_path",)),
    ("accessibility", ("accessibility",)),
)


def policy_projection(claim_id: str) -> dict[str, Any]:
    policy = CLAIM_POLICIES[claim_id]
    return {
        "authority_owner": policy["authority_owner"],
        "applicable_rule": policy["applicable_rule"],
        "evaluator": policy["evaluator"],
        "required_semantics": list(policy["required_semantics"]),
        "success_modes": list(policy["success_modes"]),
        "missing_status": policy["missing_status"],
        "blocking": policy["blocking"],
        "may_authorize_builder_handoff": policy["may_authorize_builder_handoff"],
    }


def derive_action_claims(action_type: str) -> tuple[str, ...] | None:
    return ACTION_CLAIMS.get(action_type)


def mutable_claim_policies() -> dict[str, dict[str, Any]]:
    """Return a detached reporting copy; runtime modules import CLAIM_POLICIES directly."""

    return copy.deepcopy(CLAIM_POLICIES)
