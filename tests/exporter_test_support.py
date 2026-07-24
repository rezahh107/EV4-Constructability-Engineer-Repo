from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from validator.project_gate_export import canonical_bytes, load_json
from validator.project_gate_exporter import GitProvenance

ROOT = Path(__file__).resolve().parents[1]
INTAKE_FIXTURE = (
    ROOT
    / "fixtures/architect-stage-intake-v1-1/valid/"
    "project-gate-transition-complete.v1_1.json"
)
SOURCE_WRAPPER = (
    ROOT
    / "fixtures/architect-stage-intake-v1-1/source-bundles/"
    "synthetic-architect-stage-bundle.v1.json"
)
INTERMEDIATE_INPUTS_FILENAME = "ce-intermediate-export-inputs.json"


def _write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")
    return path


def _real_source_pair(tmp_path: Path) -> tuple[dict, dict, Path, Path]:
    intake = copy.deepcopy(load_json(INTAKE_FIXTURE))
    source = copy.deepcopy(load_json(SOURCE_WRAPPER)["source_bundle"])
    intake["synthetic"] = False
    for item in intake["evidence_register"]:
        if item.get("fact_class") == "synthetic_fixture":
            item["fact_class"] = "project_specific_behavior"
        source_ref = item.get("source_ref") or {}
        if source_ref.get("source_type") == "synthetic_fixture":
            source_ref["source_type"] = "stage_payload"
    for item in source["payload"]["evidence_register"]:
        if item.get("fact_class") == "synthetic_fixture":
            item["fact_class"] = "project_specific_behavior"
        source_ref = item.get("source_ref") or {}
        if source_ref.get("source_type") == "synthetic_fixture":
            source_ref["source_type"] = "stage_payload"
    intake["project_gate_transition"]["source_bundle_hash"]["value"] = hashlib.sha256(
        canonical_bytes(source)
    ).hexdigest()
    intake_path = _write_json(tmp_path / "ce-input.json", intake)
    source_path = _write_json(tmp_path / "architect-source-bundle.json", source)
    return intake, source, intake_path, source_path


def _unit_id(source_node_id: str) -> str:
    return f"ce-unit-{source_node_id.removeprefix('node-')}"


def _payload(intake: dict, intake_path: Path, *, synthetic: bool = False) -> dict:
    classes = intake["architect_intent_preserved"]["class_intent"]["approved_class_names"]
    candidate = intake["selected_architecture"]["selected_candidate_id"]
    source_hash = hashlib.sha256(canonical_bytes(intake)).hexdigest()
    nodes = sorted(
        intake["structure_projection"]["nodes"],
        key=lambda item: item["source_node_id"],
    )
    reviewed_nodes = []
    strategies = []
    traces = []
    for node in nodes:
        source_id = node["source_node_id"]
        review_unit_id = _unit_id(source_id)
        evidence_refs = sorted(node.get("evidence_refs") or [])
        reviewed_nodes.append(
            {
                "node_id": source_id,
                "review_unit_id": review_unit_id,
                "architect_node_ref": source_id,
                "architect_evidence_refs": evidence_refs,
                "node_type": node.get("node_kind") or "unknown",
                "action_proposed": "preserve approved structure",
                "node_status": "executable_ready",
                "blocking_reason": None,
                "interrogation_result": {
                    "geometry_required": False,
                    "geometry_proven": None,
                    "asset_required": False,
                    "asset_source_present": None,
                    "placeholder_policy_present": None,
                    "overlay_strategy_required": False,
                    "overlay_strategy_proven": None,
                    "responsive_behavior": "not_applicable",
                    "action_targets_responsive": False,
                    "interaction_implied": False,
                    "interaction_approved": None,
                    "dynamic_loop_implied": False,
                    "dynamic_loop_approved": None,
                    "accessibility_claimed": False,
                    "accessibility_evidenced": None,
                    "exact_ui_control_path_used": False,
                    "ui_control_evidence_present": None,
                    "reversible_if_wrong": True,
                    "requires_class_change": False,
                    "requires_structure_change": False,
                    "architect_decomposition_permission": False,
                },
            }
        )
        strategies.append(
            {
                "strategy_id": f"STR-{review_unit_id.upper()}",
                "node_id": review_unit_id,
                "strategy_selected": "preserve-approved-structure",
                "alternatives_considered": [],
                "rationale": "Accepted architecture identity is preserved.",
                "evidence_source": "architect_package",
                "builder_decisions_required": 0,
                "architect_amendment_required": False,
                "class_names_affected": [],
            }
        )
        traces.append(
            {
                "architect_node_ref": source_id,
                "architect_evidence_refs": evidence_refs,
                "ce_review_unit_id": review_unit_id,
                "identity_unchanged": True,
            }
        )

    review = {
        "review_id": "CRR-EXPORT-001",
        "architect_package_ref": str(intake_path),
        "selected_candidate_id": candidate,
        "approved_class_names": list(classes),
        "architect_unknowns": copy.deepcopy(intake.get("unresolved_evidence") or []),
        "preserved_forbidden_work": list(intake.get("forbidden_work") or []),
        "constructability_status": "executable_ready",
        "builder_decisions_required": 0,
        "blocking_dependencies": [],
        "reviewed_nodes": reviewed_nodes,
    }
    strategy = {
        "strategy_map_id": "ISM-EXPORT-001",
        "review_ref": "CRR-EXPORT-001",
        "selected_candidate_id": candidate,
        "strategies": strategies,
    }
    package = {
        "schema": "ev4-builder-executable-package@1.0.0",
        "package_id": "BEP-EXPORT-001",
        "review_ref": "CRR-EXPORT-001",
        "strategy_map_ref": "ISM-EXPORT-001",
        "architect_contract": {
            "source_ref": str(intake_path),
            "selected_candidate_id": candidate,
            "approved_class_names": list(classes),
        },
        "selected_candidate_id": candidate,
        "approved_class_names": list(classes),
        "builder_package_status": "executable_ready",
        "builder_decisions_required": 0,
        "blocking_dependencies": [],
        "selected_candidate_locked": True,
        "selected_candidate_id_unchanged": True,
        "approved_class_names_unchanged": True,
        "confirmation_request": {
            "confirmation_id": "CONFIRM-EXPORT-001",
            "confirmed_action_ids": ["ACTION-EXPORT-001"],
            "expected_user_token": "confirm ACTION-EXPORT-001",
        },
        "first_safe_builder_batch": {
            "batch_id": "BATCH-EXPORT-001",
            "risk": "low",
            "actions": [
                {
                    "action_id": "ACTION-EXPORT-001",
                    "action_type": "create_element",
                    "target_node": "node-root",
                    "parameters": {"element_type": "Container"},
                    "requires_decision": False,
                }
            ],
        },
        "qa_status": {"production_ready": False},
    }
    payload = {
        "schema_id": "ev4-ce-stage-payload@1.0.0",
        "schema_version": "1.0.0",
        "owner_repository": "rezahh107/EV4-Constructability-Engineer-Repo",
        "payload_status": "complete",
        "payload_identity": {
            "payload_id": "ce-payload-test-001",
            "pipeline_id": "ev4-ce-project-gate-producer-pipeline",
            "run_id": "ce-run-test-001",
            "synthetic": synthetic,
        },
        "source_architect_intake": {
            "schema_id": "ev4-ce-architect-stage-intake@1.1.0",
            "schema_version": "1.1.0",
            "artifact_ref": str(intake_path),
            "artifact_hash": {
                "algorithm": "sha256",
                "value": source_hash,
                "scope": "canonical_json",
            },
            "transition_metadata_is_review_evidence": False,
        },
        "architecture_identity": {
            "selected_candidate_id": candidate,
            "selected_candidate_locked": True,
            "selected_candidate_id_unchanged": True,
            "approved_class_names": list(classes),
            "approved_class_names_unchanged": True,
            "build_tree_identity_preserved": True,
            "architect_unknowns_preserved": True,
            "architect_forbidden_work_weakened": False,
            "review_unit_traces": traces,
        },
        "constructability_review": copy.deepcopy(review),
        "implementation_strategy_map": copy.deepcopy(strategy),
        "builder_executable_package": copy.deepcopy(package),
        "builder_package_emitted": True,
        "builder_package_not_emitted_reason": None,
        "evidence_register": [
            {
                "id": "ev-stage7",
                "kind": "validator",
                "state": "validated",
                "description": "CE constructability and package validation evidence.",
                "source": {"type": "repo_path", "reference": "validator/engine.py"},
            }
        ],
        "unresolved_evidence": [],
        "repair_routing": {"repair_owner": "ce", "status": "not_required"},
        "boundary_assertions": {
            "ce_did_not_redesign_architecture": True,
            "ce_did_not_claim_builder_execution": True,
            "ce_did_not_claim_responsive_completion": True,
            "production_ready": False,
        },
        "validation_contract": {
            "validator_id": "ev4-ce-project-gate-export-validator",
            "validator_version": "1.0.0",
            "intermediate_inputs": "ev4-ce-intermediate-export-inputs@1.0.0",
        },
        "extension_records": [],
    }
    _write_json(
        intake_path.with_name(INTERMEDIATE_INPUTS_FILENAME),
        {
            "schema_id": "ev4-ce-intermediate-export-inputs@1.0.0",
            "schema_version": "1.0.0",
            "run_id": payload["payload_identity"]["run_id"],
            "constructability_review": review,
            "implementation_strategy_map": strategy,
            "builder_executable_package": package,
        },
    )
    return payload


def _provenance(*, dirty: bool = False) -> GitProvenance:
    return GitProvenance(
        repository="rezahh107/EV4-Constructability-Engineer-Repo",
        ref="feature/ce-project-gate-exporter",
        commit_sha="5fa3b8aec25a22f576e65c51ffb9dd843ddb727f",
        dirty=dirty,
        dirty_paths=("validator/changed.py",) if dirty else (),
    )
