from pathlib import Path

from test_architect_contract import _doc
from validator.engine import validate_document

ROOT = Path(__file__).resolve().parents[1]


def _result(document: dict) -> dict:
    return validate_document(document, repo_root=ROOT, mode="package")


def _interrogation(document: dict) -> dict:
    return document["constructability_review"]["reviewed_nodes"][0]["interrogation_result"]


def test_dynamic_loop_implied_without_approval_fails() -> None:
    document = _doc()
    interrogation = _interrogation(document)
    interrogation["dynamic_loop_implied"] = True
    interrogation["dynamic_loop_approved"] = False

    result = _result(document)

    assert result["passed"] is False
    assert "R08_DYNAMIC_LOOP_REQUIRES_APPROVAL" in result["rules_violated"]


def test_dynamic_loop_approval_requires_binding_map() -> None:
    document = _doc()
    interrogation = _interrogation(document)
    interrogation["dynamic_loop_implied"] = True
    interrogation["dynamic_loop_approved"] = True

    result = _result(document)

    assert result["passed"] is False
    assert "R26_DYNAMIC_LOOP_BINDING_MAP_REQUIRED" in result["rules_violated"]


def test_dynamic_loop_binding_map_passes_gate() -> None:
    document = _doc()
    interrogation = _interrogation(document)
    interrogation["dynamic_loop_implied"] = True
    interrogation["dynamic_loop_approved"] = True
    interrogation["dynamic_loop_binding_map"] = {"source": "architect_contract", "bindings": []}

    assert _result(document)["passed"] is True
