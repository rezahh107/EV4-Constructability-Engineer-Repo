from pathlib import Path

from test_architect_contract import _doc
from validator.engine import validate_document

ROOT = Path(__file__).resolve().parents[1]


def _result(document: dict) -> dict:
    return validate_document(document, repo_root=ROOT, mode="package")


def test_ready_claim_requires_full_qa_evidence() -> None:
    document = _doc()
    document["builder_executable_package"]["qa_status"] = {
        "production_ready": True,
        "full_qa_evidence_present": False,
        "qa_matrix": {"frontend": "confirmed"},
    }

    result = _result(document)

    assert result["passed"] is False
    assert "R12_PRODUCTION_READY_REQUIRES_QA_EVIDENCE" in result["rules_violated"]


def test_ready_claim_requires_qa_matrix() -> None:
    document = _doc()
    document["builder_executable_package"]["qa_status"] = {
        "production_ready": True,
        "full_qa_evidence_present": True,
    }

    result = _result(document)

    assert result["passed"] is False
    assert "R28_QA_MATRIX_REQUIRED" in result["rules_violated"]


def test_ready_claim_with_full_qa_matrix_passes_gate() -> None:
    document = _doc()
    document["builder_executable_package"]["qa_status"] = {
        "production_ready": True,
        "full_qa_evidence_present": True,
        "qa_matrix": {"frontend": "confirmed", "responsive": "confirmed", "accessibility": "confirmed"},
    }

    assert _result(document)["passed"] is True
