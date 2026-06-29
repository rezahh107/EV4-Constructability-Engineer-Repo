from validator.engine import validate_document


def _safe_node() -> dict:
    return {
        "node_id": "node",
        "node_type": "Flexbox",
        "action_proposed": "create safe node",
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
        },
    }


def _valid_package() -> dict:
    return {
        "package_id": "BEP-TEST",
        "review_ref": "CRR-TEST",
        "selected_candidate_id": "ARCH-FAM-C",
        "approved_class_names": ["test-class"],
        "builder_package_status": "executable_ready",
        "builder_decisions_required": 0,
        "blocking_dependencies": [],
        "selected_candidate_locked": True,
        "selected_candidate_id_unchanged": True,
        "approved_class_names_unchanged": True,
        "confirmation_request": {
            "confirmation_id": "CONFIRM-TEST",
            "confirmed_action_ids": ["A01"],
            "expected_user_token": "confirm test",
        },
        "first_safe_builder_batch": {
            "batch_id": "BATCH-TEST",
            "actions": [
                {
                    "action_id": "A01",
                    "action_type": "create_element",
                    "target_node": "node",
                    "parameters": {},
                    "requires_decision": False,
                }
            ],
        },
    }


def test_review_blocking_dependencies_cannot_be_shadowed_by_package() -> None:
    document = {
        "constructability_review": {
            "review_id": "CRR-TEST",
            "architect_package_ref": "ARCH-PKG-TEST",
            "selected_candidate_id": "ARCH-FAM-C",
            "constructability_status": "executable_ready",
            "builder_decisions_required": 0,
            "blocking_dependencies": ["global-blocker"],
            "reviewed_nodes": [_safe_node()],
        },
        "builder_executable_package": _valid_package(),
    }

    result = validate_document(document)

    assert result["passed"] is False
    assert "R02_BLOCKING_DEPENDENCIES_EMPTY" in result["rules_violated"]


def test_package_production_ready_cannot_be_shadowed_by_review_qa() -> None:
    package = _valid_package()
    package["qa_status"] = {"production_ready": True}
    document = {
        "qa_status": {"placeholder": True},
        "constructability_review": {
            "review_id": "CRR-TEST",
            "architect_package_ref": "ARCH-PKG-TEST",
            "selected_candidate_id": "ARCH-FAM-C",
            "constructability_status": "executable_ready",
            "builder_decisions_required": 0,
            "blocking_dependencies": [],
            "reviewed_nodes": [_safe_node()],
            "qa_status": {"placeholder": True},
        },
        "builder_executable_package": package,
    }

    result = validate_document(document)

    assert result["passed"] is False
    assert "R12_PRODUCTION_READY_REQUIRES_QA_EVIDENCE" in result["rules_violated"]
