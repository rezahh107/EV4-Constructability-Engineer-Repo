from pathlib import Path

from test_architect_contract import _doc
from validator.engine import validate_document

ROOT = Path(__file__).resolve().parents[1]


def _rule_ids(document: dict) -> list[str]:
    return validate_document(document, repo_root=ROOT, mode="package")["rules_violated"]


def _strategy_map(builder_decisions_required: int = 0, architect_amendment_required: bool = False) -> dict:
    return {
        "strategy_map_id": "ISM-TEST",
        "review_ref": "CRR-LOCK",
        "selected_candidate_id": "ARCH-FAM-C",
        "strategies": [
            {
                "strategy_id": "STR-TEST",
                "node_id": "root",
                "strategy_selected": "approved_structure",
                "builder_decisions_required": builder_decisions_required,
                "architect_amendment_required": architect_amendment_required,
                "class_names_affected": [],
            }
        ],
    }


def test_strategy_map_ref_requires_strategy_map() -> None:
    document = _doc()
    document["builder_executable_package"]["strategy_map_ref"] = "ISM-TEST"

    assert "R33_IMPLEMENTATION_STRATEGY_MAP_REQUIRED" in _rule_ids(document)


def test_strategy_map_builder_decision_fails() -> None:
    document = _doc()
    document["implementation_strategy_map"] = _strategy_map(builder_decisions_required=1)
    document["builder_executable_package"]["strategy_map_ref"] = "ISM-TEST"

    assert "R33_IMPLEMENTATION_STRATEGY_ZERO_BUILDER_DECISIONS" in _rule_ids(document)


def test_strategy_map_architect_amendment_fails() -> None:
    document = _doc()
    document["implementation_strategy_map"] = _strategy_map(architect_amendment_required=True)
    document["builder_executable_package"]["strategy_map_ref"] = "ISM-TEST"

    assert "R33_IMPLEMENTATION_STRATEGY_NO_ARCHITECT_AMENDMENT" in _rule_ids(document)


def test_first_batch_requires_decision_true_fails() -> None:
    document = _doc()
    action = document["builder_executable_package"]["first_safe_builder_batch"]["actions"][0]
    action["requires_decision"] = True

    assert "R34_FIRST_BATCH_ACTION_REQUIRES_DECISION_FALSE" in _rule_ids(document)


def test_first_batch_parameters_with_unresolved_decision_fail() -> None:
    document = _doc()
    action = document["builder_executable_package"]["first_safe_builder_batch"]["actions"][0]
    action["parameters"] = {"choose_between": ["left", "right"]}

    assert "R34_FIRST_BATCH_PARAMETERS_NO_UNRESOLVED_DECISIONS" in _rule_ids(document)
