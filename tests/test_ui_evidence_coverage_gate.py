from pathlib import Path

from test_architect_contract import _doc
from validator.engine import validate_document

ROOT = Path(__file__).resolve().parents[1]


def _result(document: dict) -> dict:
    return validate_document(document, repo_root=ROOT, mode="package")


def _interrogation(document: dict) -> dict:
    return document["constructability_review"]["reviewed_nodes"][0]["interrogation_result"]


def test_exact_ui_control_path_without_evidence_fails() -> None:
    document = _doc()
    interrogation = _interrogation(document)
    interrogation["exact_ui_control_path_used"] = True
    interrogation["ui_control_evidence_present"] = False

    result = _result(document)

    assert result["passed"] is False
    assert "R10_UI_CONTROL_PATH_REQUIRES_EVIDENCE" in result["rules_violated"]


def test_ui_control_evidence_present_requires_object() -> None:
    document = _doc()
    interrogation = _interrogation(document)
    interrogation["exact_ui_control_path_used"] = True
    interrogation["ui_control_evidence_present"] = True

    result = _result(document)

    assert result["passed"] is False
    assert "R27_UI_CONTROL_EVIDENCE_OBJECT_REQUIRED" in result["rules_violated"]


def test_ui_control_evidence_object_passes_gate() -> None:
    document = _doc()
    interrogation = _interrogation(document)
    interrogation["exact_ui_control_path_used"] = True
    interrogation["ui_control_evidence_present"] = True
    interrogation["ui_control_evidence"] = {"source": "official_docs", "confidence": "documented"}

    assert _result(document)["passed"] is True
