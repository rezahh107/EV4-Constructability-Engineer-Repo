from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-ce-decision-lineage-sequence.py"
spec = importlib.util.spec_from_file_location("ce_decision_lineage_sequence", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["ce_decision_lineage_sequence"] = mod
assert spec.loader is not None
spec.loader.exec_module(mod)


def test_valid_sequence_preserves_kernel_lineage_while_adding_ce_proof() -> None:
    result = mod.validate_file(ROOT / "fixtures/decision-lineage/valid/ce-intake-output-preserves-kernel-lineage.json")
    assert result["passed"] is True
    assert result["matches_expected"] is True
    assert result["diagnostics"] == []


def test_missing_intake_lineage_fails_closed() -> None:
    result = mod.validate_file(ROOT / "fixtures/decision-lineage/invalid/ce-intake-missing-kernel-lineage.json")
    assert result["passed"] is False
    assert result["matches_expected"] is True
    assert any(diagnostic["code"] == mod.DIAGNOSTIC_MISSING_LINEAGE for diagnostic in result["diagnostics"])


def test_output_cannot_replace_or_weaken_upstream_lineage() -> None:
    result = mod.validate_file(ROOT / "fixtures/decision-lineage/invalid/ce-output-replaces-kernel-lineage.json")
    assert result["passed"] is False
    assert result["matches_expected"] is True
    assert any(diagnostic["code"] == mod.DIAGNOSTIC_LINEAGE_REPLACED for diagnostic in result["diagnostics"])


def _lineage(family: str, card: str, option: str) -> dict:
    return {
        "decision_family": family,
        "decision_card_ref": card,
        "selected_option": option,
        "rejected_options": [],
        "evidence_refs": [f"evidence-{card}"],
        "evidence_state": "validated",
        "consumer_stage": "ce_intake",
    }


def test_replaced_lineage_diagnostic_uses_actual_output_index_when_reordered() -> None:
    first = _lineage("layout_structure", "DK-CARD-layout-001", "approved_layout")
    second = _lineage("interaction_model", "DK-CARD-interaction-001", "approved_interaction")
    replaced_second = {**second, "selected_option": "ce_replacement"}

    diagnostics = mod.validate_sequence(
        {
            "ce_intake": {"decision_lineage": [first, second]},
            "ce_output": {"decision_lineage": [replaced_second, first]},
        }
    )

    replaced_paths = [diagnostic.path for diagnostic in diagnostics if diagnostic.code == mod.DIAGNOSTIC_LINEAGE_REPLACED]
    assert "$.ce_output.decision_lineage[0].selected_option" in replaced_paths
    assert "$.ce_output.decision_lineage[1].selected_option" not in replaced_paths


def test_dropped_lineage_diagnostic_points_to_missing_intake_entry() -> None:
    first = _lineage("layout_structure", "DK-CARD-layout-001", "approved_layout")
    second = _lineage("interaction_model", "DK-CARD-interaction-001", "approved_interaction")

    diagnostics = mod.validate_sequence(
        {
            "ce_intake": {"decision_lineage": [first, second]},
            "ce_output": {"decision_lineage": [first]},
        }
    )

    dropped_paths = [diagnostic.path for diagnostic in diagnostics if diagnostic.code == mod.DIAGNOSTIC_LINEAGE_DROPPED]
    assert dropped_paths == ["$.ce_intake.decision_lineage[1]"]


def test_fixture_directory_expectations_match() -> None:
    paths = mod.iter_fixture_paths([ROOT / "fixtures/decision-lineage"])
    assert paths
    results = [mod.validate_file(path) for path in paths]
    assert all(result["matches_expected"] for result in results)
