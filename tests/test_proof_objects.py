from pathlib import Path

from test_architect_contract import _doc
from validator.engine import validate_document

ROOT = Path(__file__).resolve().parents[1]


def _i(document: dict) -> dict:
    return document["constructability_review"]["reviewed_nodes"][0]["interrogation_result"]


def _rule_ids(document: dict) -> list[str]:
    return validate_document(document, repo_root=ROOT, mode="package")["rules_violated"]


def test_geometry_proof_object_rule() -> None:
    document = _doc()
    _i(document)["geometry_required"] = True
    _i(document)["geometry_proven"] = True
    assert "R24_GEOMETRY_PROOF_OBJECT_REQUIRED" in _rule_ids(document)


def test_overlay_strategy_object_rule() -> None:
    document = _doc()
    _i(document)["overlay_strategy_required"] = True
    _i(document)["overlay_strategy_proven"] = True
    assert "R25_OVERLAY_STRATEGY_OBJECT_REQUIRED" in _rule_ids(document)


def test_dynamic_loop_map_rule() -> None:
    document = _doc()
    _i(document)["dynamic_loop_implied"] = True
    _i(document)["dynamic_loop_approved"] = True
    assert "R26_DYNAMIC_LOOP_BINDING_MAP_REQUIRED" in _rule_ids(document)


def test_ui_evidence_object_rule() -> None:
    document = _doc()
    _i(document)["exact_ui_control_path_used"] = True
    _i(document)["ui_control_evidence_present"] = True
    assert "R27_UI_CONTROL_EVIDENCE_OBJECT_REQUIRED" in _rule_ids(document)


def test_qa_matrix_rule() -> None:
    document = _doc()
    document["builder_executable_package"]["qa_status"] = {
        "production_ready": True,
        "full_qa_evidence_present": True,
    }
    assert "R28_QA_MATRIX_REQUIRED" in _rule_ids(document)
