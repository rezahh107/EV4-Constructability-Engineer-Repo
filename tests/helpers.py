from pathlib import Path

from validator.engine import validate_document

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_BUILDER_EXECUTABLE_PACKAGE_SCHEMA = "ev4-builder-executable-package@1.0.0"


def _doc() -> dict:
    return {
        "constructability_review": {
            "review_id": "CRR-LOCK",
            "architect_package_ref": "ARCH-PKG-LOCK",
            "selected_candidate_id": "ARCH-FAM-C",
            "constructability_status": "executable_ready",
            "builder_decisions_required": 0,
            "blocking_dependencies": [],
            "reviewed_nodes": [
                {
                    "node_id": "root",
                    "node_type": "Flexbox",
                    "action_proposed": "create root",
                    "node_status": "executable_ready",
                    "interrogation_result": {
                        "geometry_required": False,
                        "asset_required": False,
                        "overlay_strategy_required": False,
                        "responsive_behavior": "not_applicable",
                        "action_targets_responsive": False,
                        "interaction_implied": False,
                        "dynamic_loop_implied": False,
                        "accessibility_claimed": False,
                        "exact_ui_control_path_used": False,
                        "requires_class_change": False,
                        "requires_structure_change": False,
                    },
                }
            ],
        },
        "builder_executable_package": {
            "schema": SUPPORTED_BUILDER_EXECUTABLE_PACKAGE_SCHEMA,
            "package_id": "BEP-LOCK",
            "review_ref": "CRR-LOCK",
            "architect_contract": {
                "source_ref": "ARCH-PKG-LOCK",
                "selected_candidate_id": "ARCH-FAM-C",
                "approved_class_names": ["root-class"],
            },
            "selected_candidate_id": "ARCH-FAM-C",
            "approved_class_names": ["root-class"],
            "builder_package_status": "executable_ready",
            "builder_decisions_required": 0,
            "blocking_dependencies": [],
            "selected_candidate_locked": True,
            "selected_candidate_id_unchanged": True,
            "approved_class_names_unchanged": True,
            "confirmation_request": {
                "confirmation_id": "CONFIRM-LOCK",
                "confirmed_action_ids": ["A01"],
                "expected_user_token": "confirm lock",
            },
            "first_safe_builder_batch": {
                "batch_id": "BATCH-LOCK",
                "actions": [
                    {
                        "action_id": "A01",
                        "action_type": "create_element",
                        "target_node": "root",
                        "parameters": {},
                        "requires_decision": False,
                    }
                ],
            },
        },
    }


def _result(document: dict) -> dict:
    return validate_document(document, repo_root=ROOT, mode="package")


def _interrogation(document: dict) -> dict:
    return document["constructability_review"]["reviewed_nodes"][0]["interrogation_result"]
