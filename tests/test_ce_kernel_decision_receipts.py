from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from validator import kernel_decision_receipts as receipts

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-ce-kernel-decision-receipts.py"
spec = importlib.util.spec_from_file_location("ce_kernel_decision_receipts", SCRIPT)
receipt_script = importlib.util.module_from_spec(spec)
sys.modules["ce_kernel_decision_receipts"] = receipt_script
assert spec.loader is not None
spec.loader.exec_module(receipt_script)


def _complete_lineage() -> dict:
    return {
        "decision_family": "layout_structure",
        "decision_card_ref": "DK-CARD-layout-structure-001",
        "selected_option": "center_anchored_symmetric_pill_cards",
        "rejected_options": ["freeform_builder_layout", "unanchored_grid"],
        "evidence_refs": ["architect-stage-evidence-layout-001"],
        "evidence_state": "validated",
        "consumer_stage": "ce_intake",
    }


def _success_receipt() -> dict:
    return {
        "visible_status_marker": "✅",
        "status": receipts.SUCCESS_STATUS,
        "message": receipts.SUCCESS_RECEIPT_TEXT,
    }


def test_complete_machine_trace_allows_success_receipt() -> None:
    surface = {"decision_lineage": [_complete_lineage()]}
    receipt = receipts.render_ce_kernel_decision_receipt(surface)

    assert receipt["visible_status_marker"] == "✅"
    assert receipt["status"] == receipts.SUCCESS_STATUS
    assert receipt["message"] == receipts.SUCCESS_RECEIPT_TEXT
    assert receipts.validate_receipt_surface(
        {**surface, "kernel_decision_receipt": receipt},
        "$.ce_output",
    ) == []


def test_missing_decision_card_ref_blocks_success_receipt() -> None:
    lineage = _complete_lineage()
    lineage.pop("decision_card_ref")
    surface = {
        "decision_lineage": [lineage],
        "kernel_decision_receipt": _success_receipt(),
    }

    diagnostics = receipts.validate_receipt_surface(surface, "$.ce_output")

    assert any(
        diagnostic.code == receipts.DIAGNOSTIC_GREEN_WITHOUT_TRACE
        for diagnostic in diagnostics
    )


def test_missing_evidence_refs_blocks_success_receipt() -> None:
    lineage = _complete_lineage()
    lineage["evidence_refs"] = []
    surface = {
        "decision_lineage": [lineage],
        "kernel_decision_receipt": _success_receipt(),
    }

    diagnostics = receipts.validate_receipt_surface(surface, "$.ce_output")

    assert any(
        diagnostic.code == receipts.DIAGNOSTIC_GREEN_WITHOUT_TRACE
        for diagnostic in diagnostics
    )


def test_invalid_evidence_state_blocks_success_receipt() -> None:
    invalid_values = ["", None, 7, [], {}, "insufficient_evidence", "not_a_state"]

    for invalid_value in invalid_values:
        lineage = _complete_lineage()
        lineage["evidence_state"] = invalid_value
        surface = {
            "decision_lineage": [lineage],
            "kernel_decision_receipt": _success_receipt(),
        }

        diagnostics = receipts.validate_receipt_surface(surface, "$.ce_output")

        assert "evidence_state" in receipts.missing_machine_trace_fields(lineage)
        assert any(
            diagnostic.code == receipts.DIAGNOSTIC_GREEN_WITHOUT_TRACE
            for diagnostic in diagnostics
        )


def test_warning_receipt_is_used_when_trace_is_incomplete() -> None:
    lineage = _complete_lineage()
    lineage.pop("decision_card_ref")
    surface = {"decision_lineage": [lineage]}
    receipt = receipts.render_ce_kernel_decision_receipt(surface)

    assert receipt["visible_status_marker"] == "⚠️"
    assert receipt["status"] == receipts.WARNING_STATUS
    assert receipt["message"] == receipts.WARNING_RECEIPT_TEXT
    assert receipts.validate_receipt_surface(
        {**surface, "kernel_decision_receipt": receipt},
        "$.ce_output",
    ) == []


def test_ce_constructability_receipt_does_not_replace_machine_trace() -> None:
    surface = {"decision_lineage": [_complete_lineage()]}
    receipt = receipts.render_ce_kernel_decision_receipt(surface)

    assert "decision_card_ref" not in receipt
    assert "DK-CARD-layout-structure-001" not in receipt["message"]
    assert surface["decision_lineage"][0]["decision_card_ref"] == "DK-CARD-layout-structure-001"


def test_ce_cannot_claim_constructability_pass_without_trace() -> None:
    surface = {
        "constructability_status": "executable_ready",
        "kernel_decision_receipt": {
            "visible_status_marker": "⚠️",
            "status": receipts.WARNING_STATUS,
            "message": receipts.WARNING_RECEIPT_TEXT,
        },
    }

    diagnostics = receipts.validate_receipt_surface(surface, "$.ce_output")

    assert any(
        diagnostic.code == receipts.DIAGNOSTIC_CE_PASS_WITHOUT_TRACE
        for diagnostic in diagnostics
    )


def test_ce_cannot_emit_success_receipt_for_untraced_repair_or_handoff_item() -> None:
    document = {
        "repair_request": {
            "kernel_decision_receipt": _success_receipt(),
        },
        "handoff": {
            "kernel_decision_receipt": _success_receipt(),
        },
    }

    diagnostics = receipts.validate_receipt_document(document)
    green_paths = [
        diagnostic.path
        for diagnostic in diagnostics
        if diagnostic.code == receipts.DIAGNOSTIC_GREEN_WITHOUT_TRACE
    ]

    assert "$.repair_request.kernel_decision_receipt" in green_paths
    assert "$.handoff.kernel_decision_receipt" in green_paths


def test_recursive_validation_catches_nested_invalid_receipt_and_ce_pass() -> None:
    document = {
        "ce_output": {
            "sections": [
                {
                    "constructability_review": {
                        "constructability_status": "executable_ready",
                        "kernel_decision_receipt": _success_receipt(),
                    }
                }
            ]
        }
    }

    diagnostics = receipts.validate_receipt_document(document)
    diagnostic_pairs = {(diagnostic.code, diagnostic.path) for diagnostic in diagnostics}

    assert (
        receipts.DIAGNOSTIC_GREEN_WITHOUT_TRACE,
        "$.ce_output.sections[0].constructability_review.kernel_decision_receipt",
    ) in diagnostic_pairs
    assert (
        receipts.DIAGNOSTIC_CE_PASS_WITHOUT_TRACE,
        "$.ce_output.sections[0].constructability_review",
    ) in diagnostic_pairs


def test_receipt_fixture_directory_expectations_match() -> None:
    paths = receipt_script.iter_fixture_paths([ROOT / "fixtures/kernel-decision-receipts"])
    assert paths
    results = [receipt_script.validate_file(path) for path in paths]
    assert all(result["matches_expected"] for result in results)
