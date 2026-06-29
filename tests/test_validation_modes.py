from pathlib import Path

from validator.engine import validate_document, validate_file

ROOT = Path(__file__).resolve().parents[1]


def test_report_mode_accepts_non_executable_review_without_package() -> None:
    result = validate_file(
        ROOT / "fixtures/valid/report/v01_needs_user_evidence_geometry.yaml",
        repo_root=ROOT,
        mode="report",
    )

    assert result["passed"] is True
    assert result["mode"] == "report"
    assert result["rules_violated"] == []


def test_report_mode_rejects_executable_ready_review_without_package() -> None:
    result = validate_document(
        {
            "constructability_review": {
                "review_id": "CRR-REPORT-EXEC",
                "architect_package_ref": "ARCH-PKG-REPORT-EXEC",
                "selected_candidate_id": "ARCH-FAM-C",
                "constructability_status": "executable_ready",
                "builder_decisions_required": 0,
                "blocking_dependencies": [],
                "reviewed_nodes": [
                    {
                        "node_id": "root",
                        "node_type": "Flexbox",
                        "action_proposed": "report incorrectly claims executable status",
                        "node_status": "executable_ready",
                        "interrogation_result": {
                            "geometry_required": False,
                            "asset_required": False,
                            "overlay_strategy_required": False,
                            "responsive_behavior": "not_applicable",
                            "interaction_implied": False,
                            "dynamic_loop_implied": False,
                            "accessibility_claimed": False,
                            "exact_ui_control_path_used": False,
                            "requires_class_change": False,
                            "requires_structure_change": False,
                        },
                    }
                ],
            }
        },
        repo_root=ROOT,
        mode="report",
    )

    assert result["passed"] is False
    assert "R21_REPORT_MODE_MUST_BE_NON_EXECUTABLE" in result["rules_violated"]


def test_package_mode_requires_builder_package() -> None:
    result = validate_file(
        ROOT / "fixtures/valid/report/v01_needs_user_evidence_geometry.yaml",
        repo_root=ROOT,
        mode="package",
    )

    assert result["passed"] is False
    assert "R18_PACKAGE_MODE_REQUIRES_BUILDER_PACKAGE" in result["rules_violated"]


def test_package_mode_accepts_executable_builder_package() -> None:
    result = validate_file(
        ROOT / "fixtures/valid/v01_pure_structure.yaml",
        repo_root=ROOT,
        mode="package",
    )

    assert result["passed"] is True
    assert result["mode"] == "package"


def test_non_executable_review_cannot_emit_package_in_full_mode() -> None:
    result = validate_file(
        ROOT / "fixtures/invalid/i09_blocked_review_with_builder_package.yaml",
        repo_root=ROOT,
        mode="full",
    )

    assert result["passed"] is False
    assert "R19_NON_EXECUTABLE_REVIEW_MUST_NOT_EMIT_BUILDER_PACKAGE" in result["rules_violated"]


def test_report_mode_rejects_builder_package_output() -> None:
    result = validate_file(
        ROOT / "fixtures/valid/v01_pure_structure.yaml",
        repo_root=ROOT,
        mode="report",
    )

    assert result["passed"] is False
    assert "R17_REPORT_MODE_MUST_NOT_EMIT_BUILDER_PACKAGE" in result["rules_violated"]
