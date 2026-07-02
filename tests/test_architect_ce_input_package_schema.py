from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "architect_ce_input_package.v1.schema.json"


def load_schema() -> dict:
    with SCHEMA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def proof(required: bool, state: str, evidence_refs: list[str] | None = None) -> dict:
    return {"required": required, "state": state, "evidence_refs": evidence_refs or []}


def boundary(crosses: bool, state: str, evidence_refs: list[str] | None = None) -> dict:
    return {"crosses_boundary": crosses, "state": state, "evidence_refs": evidence_refs or []}


def valid_package() -> dict:
    not_required = proof(False, "not_required")
    not_proven = proof(True, "not_proven")
    return {
        "schema": "ev4-architect-to-ce-input-package@1.0.0",
        "contract_version": "1.0.0",
        "source_architect_schema": "ev4-architect-output-contract@1.0.0",
        "ingestion_target": "constructability_review",
        "accepted_for_ce_review": True,
        "builder_executable_allowed": False,
        "builder_ready_status": "not_builder_ready_without_ce_proof",
        "selected_candidate_id": "candidate:one",
        "selected_candidate_locked": True,
        "production_ready_allowed": False,
        "architect_contract": {
            "source_ref": "contracts/ARCHITECT_OUTPUT_CONTRACT_V1.md",
            "source_stage": "/builder-feed-export",
            "selected_candidate_id": "candidate:one",
            "approved_class_names": ["ev4-section"],
            "forbidden_work": ["blocked"],
        },
        "source_payload_ledger": [
            {"payload_name": "architect-output", "source_stage": "/builder-feed-export", "source_status": "validated"}
        ],
        "approved_structure_tree": [
            {
                "node_id": "section:one",
                "parent_node_id": None,
                "node_type": "section",
                "approved_role": "section",
                "approved_class_names": ["ev4-section"],
                "child_node_ids": [],
                "architecture_locked": True,
            }
        ],
        "approved_class_names": ["ev4-section"],
        "ce_review_units": [
            {
                "unit_id": "unit:one",
                "source_node_id": "section:one",
                "action_proposed": "review",
                "node_type": "section",
                "approved_class_names": ["ev4-section"],
                "interrogation_inputs": {
                    "geometry": not_proven,
                    "source_target_anchors": not_proven,
                    "asset": not_required,
                    "placeholder_policy": not_required,
                    "overlay": not_required,
                    "containment": not_required,
                    "z_index": not_required,
                    "responsive": not_proven,
                    "interaction": not_required,
                    "dynamic_loop": not_required,
                    "accessibility": not_required,
                    "elementor_ui_control_path": not_required,
                    "reversibility": not_required,
                    "class_boundary": boundary(False, "preserved"),
                    "structure_boundary": boundary(False, "preserved"),
                },
                "default_ce_status": "blocked",
                "builder_action_authorized": False,
            }
        ],
        "evidence_gaps_for_ce": [
            {
                "gap_id": "gap:one",
                "affected_unit_ids": ["unit:one"],
                "gap_type": "geometry_not_proven",
                "required_before_builder": True,
            }
        ],
        "forbidden_work": ["blocked"],
        "mapping_trace": [
            {
                "from_architect_path": "$.ce_review_units[0]",
                "to_ce_path": "$.ce_review_units[0]",
                "mapping_rule": "map_without_inference",
                "loss_policy": "no_loss_allowed",
            }
        ],
        "identity_consistency_checks": {
            "selected_candidate_id_matches_architect_contract": True,
            "approved_class_names_match_architect_contract": True,
            "all_review_units_target_existing_nodes": True,
            "all_evidence_gaps_target_existing_units": True,
            "forbidden_work_preserved_from_architect_output": True,
        },
        "pre_ingestion_validation": {
            "verified_by": "ce_adapter_validator",
            "architect_schema_valid": True,
            "no_additional_properties": True,
            "no_builder_ready_claim": True,
            "selected_candidate_locked": True,
            "approved_class_names_resolved": True,
            "all_review_units_mapped": True,
            "source_payload_ledger_preserved": True,
            "forbidden_work_preserved": True,
            "evidence_gaps_preserved": True,
            "identity_consistency_verified": True,
            "unmapped_fields": [],
        },
        "ce_ingestion_policy": {
            "semantic_guessing_allowed": False,
            "builder_package_emission_allowed_at_ingestion": False,
            "default_status_when_proof_missing": "blocked",
            "ambiguous_fields_allowed": False,
        },
    }


def validator() -> Draft202012Validator:
    schema = load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def assert_valid(instance: dict) -> None:
    errors = list(validator().iter_errors(instance))
    assert not errors, [error.message for error in errors]


def assert_invalid(instance: dict) -> None:
    assert list(validator().iter_errors(instance))


def test_valid_minimal_ce_input_package_passes_schema() -> None:
    assert_valid(valid_package())


def test_evidence_backed_requires_evidence_ref() -> None:
    package = copy.deepcopy(valid_package())
    package["ce_review_units"][0]["interrogation_inputs"]["geometry"] = proof(True, "evidence_backed")
    assert_invalid(package)


def test_not_required_state_requires_empty_evidence_refs() -> None:
    package = copy.deepcopy(valid_package())
    package["ce_review_units"][0]["interrogation_inputs"]["asset"] = proof(False, "not_required", ["proof.md"])
    assert_invalid(package)


def test_required_true_cannot_use_not_required_state() -> None:
    package = copy.deepcopy(valid_package())
    package["ce_review_units"][0]["interrogation_inputs"]["responsive"] = proof(True, "not_required")
    assert_invalid(package)


def test_boundary_crossing_cannot_use_preserved_state() -> None:
    package = copy.deepcopy(valid_package())
    package["ce_review_units"][0]["interrogation_inputs"]["class_boundary"] = boundary(True, "preserved", ["proof.md"])
    assert_invalid(package)


def test_boundary_not_crossed_cannot_use_not_proven_state() -> None:
    package = copy.deepcopy(valid_package())
    package["ce_review_units"][0]["interrogation_inputs"]["class_boundary"] = boundary(False, "not_proven")
    assert_invalid(package)


def test_unknown_source_stage_is_rejected() -> None:
    package = copy.deepcopy(valid_package())
    package["source_payload_ledger"][0]["source_stage"] = "/unknown-stage"
    assert_invalid(package)
