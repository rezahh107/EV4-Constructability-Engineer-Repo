from pathlib import Path
from copy import deepcopy

from test_architect_contract import _doc
from validator.engine import load_json, validate_document

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "tests/valid/center_anchored_symmetric_pill_cards.json"


def _reference_carriers() -> dict:
    return load_json(REFERENCE)


def _visual_package_doc() -> dict:
    document = _doc()
    document["builder_executable_package"]["visual_parity_build"] = True
    return document


def test_visual_parity_package_requires_reference_carriers_inside_package() -> None:
    document = _visual_package_doc()
    carriers = _reference_carriers()
    document["reference_paradigm_lock"] = deepcopy(carriers["reference_paradigm_lock"])
    document["paradigm_to_structure_map"] = deepcopy(carriers["paradigm_to_structure_map"])

    result = validate_document(document, repo_root=ROOT, mode="package")

    assert result["passed"] is False
    assert "R35_REFERENCE_PARADIGM_LOCK_MUST_BE_CARRIED_IN_PACKAGE" in result["rules_violated"]
    assert "R36_REFERENCE_PARADIGM_STRUCTURE_MAP_MUST_BE_CARRIED_IN_PACKAGE" in result["rules_violated"]


def test_visual_parity_package_with_carried_reference_contract_passes() -> None:
    document = _visual_package_doc()
    carriers = _reference_carriers()
    document["builder_executable_package"]["reference_paradigm_lock"] = deepcopy(carriers["reference_paradigm_lock"])
    document["builder_executable_package"]["paradigm_to_structure_map"] = deepcopy(carriers["paradigm_to_structure_map"])

    result = validate_document(document, repo_root=ROOT, mode="package")

    assert result["passed"] is True


def test_unknown_paradigm_carried_inside_package_still_blocks_visual_parity() -> None:
    document = _visual_package_doc()
    carriers = _reference_carriers()
    carriers["reference_paradigm_lock"]["layout_paradigm"] = "unknown"
    document["builder_executable_package"]["reference_paradigm_lock"] = deepcopy(carriers["reference_paradigm_lock"])
    document["builder_executable_package"]["paradigm_to_structure_map"] = deepcopy(carriers["paradigm_to_structure_map"])

    result = validate_document(document, repo_root=ROOT, mode="package")

    assert result["passed"] is False
    assert "R30_REFERENCE_PARADIGM_UNKNOWN_BLOCKS_BUILDER_READY" in result["rules_violated"]
