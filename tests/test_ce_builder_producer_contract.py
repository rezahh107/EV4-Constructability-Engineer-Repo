from copy import deepcopy
from pathlib import Path

from test_architect_contract import _doc
from validator.engine import load_json, validate_document

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "tests/valid/center_anchored_symmetric_pill_cards.json"


def _visual_package_doc() -> dict:
    document = _doc()
    document["builder_executable_package"]["visual_parity_build"] = True
    carriers = load_json(REFERENCE)
    document["builder_executable_package"]["reference_paradigm_lock"] = deepcopy(carriers["reference_paradigm_lock"])
    document["builder_executable_package"]["paradigm_to_structure_map"] = deepcopy(carriers["paradigm_to_structure_map"])
    return document


def test_ce_producer_keeps_connector_layer_structured_for_downstream_transform() -> None:
    document = _visual_package_doc()

    result = validate_document(document, repo_root=ROOT, mode="package")

    assert result["passed"] is True


def test_ce_producer_must_not_emit_builder_compact_connector_string() -> None:
    document = _visual_package_doc()
    structure_map = document["builder_executable_package"]["paradigm_to_structure_map"]
    structure_map["connector_layer"] = "Smart Home Section / Decorative Connector Layer:card-edge-to-house-edge"

    result = validate_document(document, repo_root=ROOT, mode="package")

    assert result["passed"] is False
    assert any(
        "paradigm_to_structure_map.connector_layer" in error and "is not of type 'object'" in error
        for error in result["schema_errors"]
    )
