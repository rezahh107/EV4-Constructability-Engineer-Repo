from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from ce_bootstrap_test_support import (
    route,
    source_bundle_wrapper,
    valid_input_value,
    write_json,
)


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _write_bound_pair(
    tmp_path: Path,
    *,
    intake_mutator=None,
    source_mutator=None,
) -> tuple[Path, Path]:
    intake = copy.deepcopy(valid_input_value())
    wrapper = copy.deepcopy(source_bundle_wrapper())
    source = wrapper["source_bundle"]
    if intake_mutator:
        intake_mutator(intake)
    if source_mutator:
        source_mutator(source)
    intake["project_gate_transition"]["source_bundle_hash"]["value"] = hashlib.sha256(
        _canonical_json_bytes(source)
    ).hexdigest()
    return (
        write_json(tmp_path, "ce-input.json", intake),
        write_json(tmp_path, "architect-source-bundle.json", wrapper),
    )


@pytest.mark.parametrize(
    "message",
    [
        "Review the latest CE input",
        "Review the CE decision",
        "Test the implementation strategy in this CE input",
        "Validate the schema identity of this CE input",
        "کدام فایل CE را بررسی کن",
        "این schema ورودی CE را بررسی کن",
        "کد پیشنهادی داخل ورودی CE را بررسی کن",
    ],
)
def test_incidental_terms_do_not_displace_valid_ce_input(
    tmp_path: Path,
    message: str,
) -> None:
    intake = write_json(tmp_path, "ce-input.json", valid_input_value())
    result = route(message, [intake])
    assert result["operating_mode"] == "ce_runtime"
    assert result["route"] == "architect_intake_validation"
    assert result["source_provenance_verification"] == "not_required_for_complete_input"


@pytest.mark.parametrize(
    "message",
    [
        "Review PR #43",
        "Repair the CI workflow",
        "Modify scripts/ce_bootstrap_routing.py",
        "Audit the repository",
        "فایل routing در مخزن را اصلاح کن",
        "ورک‌فلو CI ریپو را تعمیر کن",
    ],
)
def test_explicit_repository_operations_remain_outside_ce_runtime(
    tmp_path: Path,
    message: str,
) -> None:
    intake = write_json(tmp_path, "ce-input.json", valid_input_value())
    result = route(message, [intake])
    assert result["activation_authorized"] is False
    assert result["operating_mode"] == "repository_maintenance"
    assert result["route"] == "repository_maintenance"


def test_complete_valid_input_without_source_bundle_does_not_claim_verification(
    tmp_path: Path,
) -> None:
    intake = write_json(tmp_path, "ce-input.json", valid_input_value())
    result = route("", [intake])
    assert result["route"] == "architect_intake_validation"
    assert result["source_binding_verified"] is False
    assert result["source_provenance_verification"] == "not_required_for_complete_input"


def test_fully_matching_source_identity_is_verified(tmp_path: Path) -> None:
    intake, source = _write_bound_pair(tmp_path)
    result = route("Review the CE input", [intake, source])
    assert result["route"] == "architect_intake_validation"
    assert result["source_binding_verified"] is True
    assert result["source_provenance_verification"] == "verified"
    assert all(result["source_binding_evidence"].values())


def test_missing_intake_commit_identity_requires_evidence(tmp_path: Path) -> None:
    def remove_commit(intake: dict[str, Any]) -> None:
        intake["source_repository_ref"].pop("commit_sha", None)

    intake, source = _write_bound_pair(tmp_path, intake_mutator=remove_commit)
    result = route("Review the CE input", [intake, source])
    assert result["route"] == "evidence_required"
    assert result["source_binding_verified"] is False
    assert result["source_provenance_verification"] == "incomplete_required_identity"
    assert "CE_RUNTIME_SOURCE_COMMIT_IDENTITY_REQUIRED" in {
        item["code"] for item in result["diagnostics"]
    }
    assert result["source_provenance_verification"] != "verified"


def test_missing_source_producer_commit_requires_evidence(tmp_path: Path) -> None:
    def remove_commit(source: dict[str, Any]) -> None:
        source["produced_by"].pop("commit_sha", None)

    intake, source = _write_bound_pair(tmp_path, source_mutator=remove_commit)
    result = route("Review the CE input", [intake, source])
    assert result["route"] == "evidence_required"
    assert result["source_binding_verified"] is False
    assert result["source_provenance_verification"] == "incomplete_required_identity"
    assert result["source_provenance_verification"] != "verified"


def test_source_commit_mismatch_blocks_without_false_verified_claim(tmp_path: Path) -> None:
    def mismatch_commit(source: dict[str, Any]) -> None:
        source["produced_by"]["commit_sha"] = "c" * 40

    intake, source = _write_bound_pair(tmp_path, source_mutator=mismatch_commit)
    result = route("Review the CE input", [intake, source])
    assert result["route"] == "blocked_source_binding_invalid"
    assert result["source_binding_verified"] is False
    assert result["source_provenance_verification"] == "failed"
    assert "CE_RUNTIME_SOURCE_COMMIT_MISMATCH" in {
        item["code"] for item in result["diagnostics"]
    }


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        (
            lambda source: source.__setitem__("stage", "builder"),
            "CE_RUNTIME_SOURCE_STAGE_MISMATCH",
        ),
        (
            lambda source: source["payload"].__setitem__(
                "schema_id", "ev4-wrong-source@1.0.0"
            ),
            "CE_RUNTIME_SOURCE_PAYLOAD_CONTRACT_MISMATCH",
        ),
    ],
)
def test_wrong_source_stage_or_payload_identity_blocks(
    tmp_path: Path,
    mutation,
    expected_code: str,
) -> None:
    intake, source = _write_bound_pair(tmp_path, source_mutator=mutation)
    result = route("Review the CE input", [intake, source])
    assert result["route"] == "blocked_source_binding_invalid"
    assert result["source_binding_verified"] is False
    assert result["source_provenance_verification"] == "failed"
    assert expected_code in {item["code"] for item in result["diagnostics"]}
