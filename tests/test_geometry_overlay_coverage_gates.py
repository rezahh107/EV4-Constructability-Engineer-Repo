from pathlib import Path

from test_architect_contract import _doc
from validator.engine import validate_document

ROOT = Path(__file__).resolve().parents[1]


def _result(document: dict) -> dict:
    return validate_document(document, repo_root=ROOT, mode="package")


def _interrogation(document: dict) -> dict:
    return document["constructability_review"]["reviewed_nodes"][0]["interrogation_result"]


def test_geometry_required_without_proof_fails() -> None:
    document = _doc()
    interrogation = _interrogation(document)
    interrogation["geometry_required"] = True
    interrogation["geometry_proven"] = False

    result = _result(document)

    assert result["passed"] is False
    assert "R03_GEOMETRY_MUST_BE_PROVEN" in result["rules_violated"]


def test_geometry_proven_requires_proof_object() -> None:
    document = _doc()
    interrogation = _interrogation(document)
    interrogation["geometry_required"] = True
    interrogation["geometry_proven"] = True

    result = _result(document)

    assert result["passed"] is False
    assert "R24_GEOMETRY_PROOF_OBJECT_REQUIRED" in result["rules_violated"]


def test_geometry_proof_object_passes_gate() -> None:
    document = _doc()
    interrogation = _interrogation(document)
    interrogation["geometry_required"] = True
    interrogation["geometry_proven"] = True
    interrogation["geometry_proof"] = {"source": "fixture", "anchors": ["root"]}

    assert _result(document)["passed"] is True


def test_overlay_required_without_strategy_fails() -> None:
    document = _doc()
    interrogation = _interrogation(document)
    interrogation["overlay_strategy_required"] = True
    interrogation["overlay_strategy_proven"] = False

    result = _result(document)

    assert result["passed"] is False
    assert "R05_OVERLAY_STRATEGY_MUST_BE_PROVEN" in result["rules_violated"]


def test_overlay_strategy_proven_requires_object() -> None:
    document = _doc()
    interrogation = _interrogation(document)
    interrogation["overlay_strategy_required"] = True
    interrogation["overlay_strategy_proven"] = True

    result = _result(document)

    assert result["passed"] is False
    assert "R25_OVERLAY_STRATEGY_OBJECT_REQUIRED" in result["rules_violated"]


def test_overlay_strategy_object_passes_gate() -> None:
    document = _doc()
    interrogation = _interrogation(document)
    interrogation["overlay_strategy_required"] = True
    interrogation["overlay_strategy_proven"] = True
    interrogation["overlay_strategy"] = {"containment": "section-local", "positioning": "absolute", "z_index_policy": "documented"}

    assert _result(document)["passed"] is True
