from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

OLD_TRUST_FIELD_PATHS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("schemas/ce_stage_payload.v1.schema.json", ("properties", "payload_status"), "payload_status"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "payload_identity", "properties", "run_id"), "payload_identity.run_id"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "payload_identity", "properties", "synthetic"), "payload_identity.synthetic"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "source_architect_intake", "properties", "artifact_hash"), "source_architect_intake.artifact_hash"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "architecture_identity", "properties", "selected_candidate_locked"), "architecture_identity.selected_candidate_locked"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "architecture_identity", "properties", "selected_candidate_id_unchanged"), "architecture_identity.selected_candidate_id_unchanged"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "architecture_identity", "properties", "approved_class_names_unchanged"), "architecture_identity.approved_class_names_unchanged"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "architecture_identity", "properties", "build_tree_identity_preserved"), "architecture_identity.build_tree_identity_preserved"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "architecture_identity", "properties", "architect_unknowns_preserved"), "architecture_identity.architect_unknowns_preserved"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "architecture_identity", "properties", "architect_forbidden_work_weakened"), "architecture_identity.architect_forbidden_work_weakened"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "review_unit_trace", "properties", "identity_unchanged"), "architecture_identity.review_unit_traces[].identity_unchanged"),
    ("schemas/ce_stage_payload.v1.schema.json", ("properties", "builder_package_emitted"), "builder_package_emitted"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "evidence", "properties", "state"), "evidence_register[].state"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "evidence", "properties", "source"), "evidence_register[].source"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "boundary_assertions", "properties", "ce_did_not_redesign_architecture"), "boundary_assertions.ce_did_not_redesign_architecture"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "boundary_assertions", "properties", "ce_did_not_claim_builder_execution"), "boundary_assertions.ce_did_not_claim_builder_execution"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "boundary_assertions", "properties", "ce_did_not_claim_responsive_completion"), "boundary_assertions.ce_did_not_claim_responsive_completion"),
    ("schemas/ce_stage_payload.v1.schema.json", ("$defs", "boundary_assertions", "properties", "production_ready"), "boundary_assertions.production_ready"),
    ("schemas/constructability_review.schema.json", ("properties", "constructability_status"), "constructability_review.constructability_status"),
    ("schemas/constructability_review.schema.json", ("properties", "builder_decisions_required"), "constructability_review.builder_decisions_required"),
    ("schemas/constructability_review.schema.json", ("$defs", "node_review", "properties", "node_status"), "constructability_review.reviewed_nodes[].node_status"),
    ("schemas/constructability_review.schema.json", ("$defs", "interrogation_result", "properties", "geometry_proven"), "constructability_review.reviewed_nodes[].interrogation_result.geometry_proven"),
    ("schemas/constructability_review.schema.json", ("$defs", "interrogation_result", "properties", "asset_source_present"), "constructability_review.reviewed_nodes[].interrogation_result.asset_source_present"),
    ("schemas/constructability_review.schema.json", ("$defs", "interrogation_result", "properties", "placeholder_policy_present"), "constructability_review.reviewed_nodes[].interrogation_result.placeholder_policy_present"),
    ("schemas/constructability_review.schema.json", ("$defs", "interrogation_result", "properties", "overlay_strategy_proven"), "constructability_review.reviewed_nodes[].interrogation_result.overlay_strategy_proven"),
    ("schemas/constructability_review.schema.json", ("$defs", "interrogation_result", "properties", "responsive_behavior"), "constructability_review.reviewed_nodes[].interrogation_result.responsive_behavior"),
    ("schemas/constructability_review.schema.json", ("$defs", "interrogation_result", "properties", "interaction_approved"), "constructability_review.reviewed_nodes[].interrogation_result.interaction_approved"),
    ("schemas/constructability_review.schema.json", ("$defs", "interrogation_result", "properties", "dynamic_loop_approved"), "constructability_review.reviewed_nodes[].interrogation_result.dynamic_loop_approved"),
    ("schemas/constructability_review.schema.json", ("$defs", "interrogation_result", "properties", "accessibility_evidenced"), "constructability_review.reviewed_nodes[].interrogation_result.accessibility_evidenced"),
    ("schemas/constructability_review.schema.json", ("$defs", "interrogation_result", "properties", "ui_control_evidence_present"), "constructability_review.reviewed_nodes[].interrogation_result.ui_control_evidence_present"),
    ("schemas/constructability_review.schema.json", ("$defs", "interrogation_result", "properties", "architect_decomposition_permission"), "constructability_review.reviewed_nodes[].interrogation_result.architect_decomposition_permission"),
    ("schemas/constructability_review.schema.json", ("properties", "qa_status"), "constructability_review.qa_status"),
    ("schemas/builder_executable_package.schema.json", ("properties", "builder_package_status"), "builder_executable_package.builder_package_status"),
    ("schemas/builder_executable_package.schema.json", ("properties", "builder_decisions_required"), "builder_executable_package.builder_decisions_required"),
    ("schemas/builder_executable_package.schema.json", ("properties", "blocking_dependencies"), "builder_executable_package.blocking_dependencies"),
    ("schemas/builder_executable_package.schema.json", ("properties", "selected_candidate_locked"), "builder_executable_package.selected_candidate_locked"),
    ("schemas/builder_executable_package.schema.json", ("properties", "selected_candidate_id_unchanged"), "builder_executable_package.selected_candidate_id_unchanged"),
    ("schemas/builder_executable_package.schema.json", ("properties", "approved_class_names_unchanged"), "builder_executable_package.approved_class_names_unchanged"),
    ("schemas/builder_executable_package.schema.json", ("$defs", "confirmation_request", "properties", "expected_user_token"), "builder_executable_package.confirmation_request.expected_user_token"),
    ("schemas/builder_executable_package.schema.json", ("properties", "qa_status"), "builder_executable_package.qa_status"),
)

PROHIBITED_AUTHORITY_KEYS = {
    "geometry_proven",
    "overlay_strategy_proven",
    "responsive_behavior",
    "accessibility_evidenced",
    "ui_control_evidence_present",
    "interaction_approved",
    "dynamic_loop_approved",
    "constructability_status",
    "builder_package_status",
    "builder_package_emitted",
    "handoff",
    "payload_status",
    "verification_status",
    "state",
    "source_sha256",
    "run_id",
}


def _load(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _resolve(document: Any, path: tuple[str, ...]) -> Any:
    current = document
    for key in path:
        if not isinstance(current, dict) or key not in current:
            raise AssertionError(f"Schema field path is absent: {'.'.join(path)}")
        current = current[key]
    return current


def _schema_property_names(value: Any) -> set[str]:
    names: set[str] = set()
    if isinstance(value, dict):
        properties = value.get("properties")
        if isinstance(properties, dict):
            names.update(str(key) for key in properties)
        for child in value.values():
            names.update(_schema_property_names(child))
    elif isinstance(value, list):
        for child in value:
            names.update(_schema_property_names(child))
    return names


def build_report() -> dict[str, Any]:
    schemas: dict[str, dict[str, Any]] = {}
    old_paths: list[str] = []
    for schema_path, internal_path, display_path in OLD_TRUST_FIELD_PATHS:
        schema = schemas.setdefault(schema_path, _load(schema_path))
        _resolve(schema, internal_path)
        old_paths.append(display_path)

    if len(old_paths) != len(set(old_paths)):
        raise AssertionError("Old trust-field registry contains duplicate paths")

    draft_schema = _load("schemas/ce_review_draft.v1.schema.json")
    if draft_schema.get("additionalProperties") is not False:
        raise AssertionError("CE Review Draft root must reject unspecified authority fields")
    draft_property_names = _schema_property_names(draft_schema)
    leaked = sorted(PROHIBITED_AUTHORITY_KEYS & draft_property_names)
    if leaked:
        raise AssertionError(
            "CE Review Draft exposes authority-bearing property names: " + ", ".join(leaked)
        )

    old_count = len(old_paths)
    new_count = len(leaked)
    removed = old_count - new_count
    reduction_percent = 0.0 if old_count == 0 else round((removed / old_count) * 100, 2)
    return {
        "method": "explicit authority-bearing field registry resolved against historical Schemas; successor Draft property scan",
        "old_schema_ids": [
            "ev4-ce-stage-payload@1.0.0",
            "EV4 Constructability Review Report",
            "ev4-builder-executable-package@1.0.0",
        ],
        "new_schema_id": "ev4-ce-review-draft@1.0.0",
        "old_model_authored_trust_relevant_fields": old_count,
        "new_model_authored_trust_relevant_fields": new_count,
        "fields_now_runtime_derived": removed,
        "fields_removed_from_model_input": removed,
        "reduction_percent": reduction_percent,
        "old_field_paths": old_paths,
        "new_authority_field_paths": leaked,
    }


def main() -> int:
    print(json.dumps(build_report(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
