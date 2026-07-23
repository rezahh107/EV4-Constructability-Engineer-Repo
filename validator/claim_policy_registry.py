from __future__ import annotations

from types import MappingProxyType
from typing import Any, Final, Mapping


def _policy(
    *,
    semantic_class: str,
    authority_owner: str,
    subject_binding_required: bool,
    admissible_evidence_modes: tuple[str, ...],
    required_semantics: tuple[str, ...],
    derivation_rule: str,
    unavailable_evidence_behavior: str,
    may_authorize_builder_handoff: bool,
) -> Mapping[str, Any]:
    return MappingProxyType(
        {
            "semantic_class": semantic_class,
            "authority_owner": authority_owner,
            "subject_binding_required": subject_binding_required,
            "admissible_evidence_modes": admissible_evidence_modes,
            "required_semantics": required_semantics,
            "derivation_rule": derivation_rule,
            "unavailable_evidence_behavior": unavailable_evidence_behavior,
            "may_authorize_builder_handoff": may_authorize_builder_handoff,
        }
    )


CLAIM_POLICIES: Final[Mapping[str, Mapping[str, Any]]] = MappingProxyType(
    {
        "geometry": _policy(
            semantic_class="COMPUTED_FACT",
            authority_owner="CE",
            subject_binding_required=True,
            admissible_evidence_modes=(
                "VERIFIED_ARTIFACT",
                "ATTRIBUTED_ENGINEERING_JUDGMENT",
            ),
            required_semantics=(
                "subject_ref",
                "anchor_model",
                "coordinate_or_layout_model",
                "derivation_method",
            ),
            derivation_rule="verified_or_attributed_supported",
            unavailable_evidence_behavior="INSUFFICIENT_EVIDENCE",
            may_authorize_builder_handoff=True,
        ),
        "overlay_strategy": _policy(
            semantic_class="COMPUTED_FACT",
            authority_owner="CE",
            subject_binding_required=True,
            admissible_evidence_modes=(
                "VERIFIED_ARTIFACT",
                "ATTRIBUTED_ENGINEERING_JUDGMENT",
            ),
            required_semantics=(
                "subject_ref",
                "containment_model",
                "positioning_model",
                "stacking_model",
                "derivation_method",
            ),
            derivation_rule="verified_or_attributed_supported",
            unavailable_evidence_behavior="INSUFFICIENT_EVIDENCE",
            may_authorize_builder_handoff=True,
        ),
        "responsive_behavior": _policy(
            semantic_class="TOOL_EXECUTION",
            authority_owner="downstream_runtime_validation",
            subject_binding_required=True,
            admissible_evidence_modes=("VERIFIED_TOOL_EXECUTION",),
            required_semantics=(
                "subject_ref",
                "target_identity",
                "result_digest",
            ),
            derivation_rule="verified_runtime_execution_only",
            unavailable_evidence_behavior="DOWNSTREAM_VALIDATION_REQUIRED",
            may_authorize_builder_handoff=True,
        ),
        "ui_control_path": _policy(
            semantic_class="OBSERVED_FACT",
            authority_owner="CE",
            subject_binding_required=True,
            admissible_evidence_modes=("VERIFIED_ARTIFACT",),
            required_semantics=(
                "subject_ref",
                "source_identity",
                "source_bytes_sha256",
            ),
            derivation_rule="verified_artifact_only",
            unavailable_evidence_behavior="INSUFFICIENT_EVIDENCE",
            may_authorize_builder_handoff=True,
        ),
        "accessibility": _policy(
            semantic_class="TOOL_EXECUTION",
            authority_owner="downstream_runtime_validation",
            subject_binding_required=True,
            admissible_evidence_modes=("VERIFIED_TOOL_EXECUTION",),
            required_semantics=(
                "subject_ref",
                "target_identity",
                "result_digest",
            ),
            derivation_rule="verified_runtime_execution_only",
            unavailable_evidence_behavior="DOWNSTREAM_VALIDATION_REQUIRED",
            may_authorize_builder_handoff=True,
        ),
        "dynamic_loop_approval": _policy(
            semantic_class="ARCHITECT_DECISION",
            authority_owner="Architect",
            subject_binding_required=True,
            admissible_evidence_modes=("VERIFIED_ARCHITECT_DECISION",),
            required_semantics=(
                "subject_ref",
                "decision_ref",
                "selected_candidate_id",
                "source_digest",
            ),
            derivation_rule="architect_decision_only",
            unavailable_evidence_behavior="ARCHITECT_DECISION_REQUIRED",
            may_authorize_builder_handoff=True,
        ),
        "interaction_approval": _policy(
            semantic_class="ARCHITECT_DECISION",
            authority_owner="Architect",
            subject_binding_required=True,
            admissible_evidence_modes=("VERIFIED_ARCHITECT_DECISION",),
            required_semantics=(
                "subject_ref",
                "decision_ref",
                "selected_candidate_id",
                "source_digest",
            ),
            derivation_rule="architect_decision_only",
            unavailable_evidence_behavior="ARCHITECT_DECISION_REQUIRED",
            may_authorize_builder_handoff=True,
        ),
        "asset_source": _policy(
            semantic_class="OBSERVED_FACT",
            authority_owner="CE",
            subject_binding_required=True,
            admissible_evidence_modes=("VERIFIED_ARTIFACT",),
            required_semantics=(
                "subject_ref",
                "source_identity",
                "source_bytes_sha256",
            ),
            derivation_rule="verified_artifact_only",
            unavailable_evidence_behavior="INSUFFICIENT_EVIDENCE",
            may_authorize_builder_handoff=True,
        ),
        "placeholder_policy": _policy(
            semantic_class="ATTRIBUTED_ENGINEERING_JUDGMENT",
            authority_owner="CE",
            subject_binding_required=True,
            admissible_evidence_modes=("ATTRIBUTED_ENGINEERING_JUDGMENT",),
            required_semantics=(
                "subject_ref",
                "premises",
                "derivation_method",
            ),
            derivation_rule="attributed_supported_only",
            unavailable_evidence_behavior="INSUFFICIENT_EVIDENCE",
            may_authorize_builder_handoff=True,
        ),
        "QA": _policy(
            semantic_class="TOOL_EXECUTION",
            authority_owner="downstream_runtime_validation",
            subject_binding_required=True,
            admissible_evidence_modes=("VERIFIED_TOOL_EXECUTION",),
            required_semantics=(
                "subject_ref",
                "target_identity",
                "result_digest",
            ),
            derivation_rule="verified_tool_execution_only",
            unavailable_evidence_behavior="DOWNSTREAM_VALIDATION_REQUIRED",
            may_authorize_builder_handoff=True,
        ),
        "constructability_status": _policy(
            semantic_class="COMPUTED_FACT",
            authority_owner="CE runtime",
            subject_binding_required=False,
            admissible_evidence_modes=(),
            required_semantics=(),
            derivation_rule="derive_from_claim_resolution",
            unavailable_evidence_behavior="blocked",
            may_authorize_builder_handoff=True,
        ),
        "builder_eligibility": _policy(
            semantic_class="COMPUTED_FACT",
            authority_owner="CE runtime",
            subject_binding_required=False,
            admissible_evidence_modes=(),
            required_semantics=(),
            derivation_rule="derive_from_constructability_and_package",
            unavailable_evidence_behavior="blocked",
            may_authorize_builder_handoff=True,
        ),
    }
)


def mutable_claim_policies() -> dict[str, dict[str, Any]]:
    """Return a detached mutable projection for canonical JSON and legacy adapters."""
    return {claim_id: dict(policy) for claim_id, policy in CLAIM_POLICIES.items()}
