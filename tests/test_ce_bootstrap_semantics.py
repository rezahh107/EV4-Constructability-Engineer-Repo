from __future__ import annotations

import copy
import json
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Any, Callable

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ce_bootstrap_test_support import *


def test_canonical_repository_contract_passes() -> None:
    result = validator.validate_repository(REPO_ROOT)
    assert result == {
        "contract": "ev4-ce-conversation-bootstrap@1.1.0",
        "trigger": "optional_conversation_shortcut",
        "routing_cases": 10,
        "forbidden_operations": 12,
        "first_stage": "architect_intake_validation",
        "source_binding": "conditional_correctness_evidence",
        "receipt_validation": "diagnostic_nonsemantic",
        "runtime_states": [
            "INTAKE_VALIDATING",
            "REVIEW_ACTIVE",
            "EVIDENCE_REQUIRED",
            "STRATEGY_READY",
            "EXPORT_VALIDATING",
            "COMPLETED",
        ],
    }


@pytest.mark.parametrize(
    "message",
    [
        "شروع",
        "  \nشروع\t",
        unicodedata.normalize("NFD", "شروع"),
        "فایل CE را بررسی کن",
        "START",
        "",
    ],
)
def test_exact_phrase_is_not_an_authorization_gate(message: str) -> None:
    result = route(message)
    assert_explicit_result(result)
    assert result["activation_authorized"] is True
    assert result["authorization_reason"] == "content_driven_runtime_intake"
    assert result["route"] == "waiting_for_ce_input"
    assert result["runtime_state"] == "INTAKE_VALIDATING"


def test_valid_input_without_startup_context_executes_first_stage(
    tmp_path: Path,
) -> None:
    intake = write_json(tmp_path, "ce-input.json", valid_input_value())
    result = route("این فایل را بررسی کن", [intake])

    assert result["activation_authorized"] is True
    assert result["route"] == "architect_intake_validation"
    assert result["runtime_state"] == "REVIEW_ACTIVE"
    assert result["pipeline_execution"] == "first_stage_only"
    assert result["source_bundle_required"] is False
    assert result["source_binding_verified"] is False
    assert (
        result["source_provenance_verification"]
        == "not_required_for_complete_input"
    )


def test_valid_input_with_verified_source_routes_first_stage(
    tmp_path: Path,
) -> None:
    intake, source = valid_pair(tmp_path)
    result = route("ورودی CE", [intake, source])

    assert result["route"] == "architect_intake_validation"
    assert result["runtime_state"] == "REVIEW_ACTIVE"
    assert result["source_binding_verified"] is True
    assert result["source_provenance_verification"] == "verified"
    assert set(result["source_binding_evidence"]) == {
        "bundle_id_match",
        "canonical_sha256_match",
        "transition_identity_match",
        "project_gate_producer_match",
        "upstream_producer_match",
    }


def test_multiple_valid_inputs_block_automatic_selection(tmp_path: Path) -> None:
    first = write_json(tmp_path, "first.json", valid_input_value())
    second = write_json(tmp_path, "second.json", valid_input_value())

    result = route("بررسی کن", [first, second])

    assert result["route"] == "blocked_ambiguous_input"
    assert result["runtime_state"] == "EVIDENCE_REQUIRED"
    assert result["pipeline_execution"] == "forbidden"
    assert result["automatic_selection"] is False
    assert len(result["candidate_paths"]) == 2


@pytest.mark.parametrize(
    "message",
    [
        "PR #40 را بررسی کن",
        "repository را audit کن",
        "کد و تست ریپو را اصلاح کن",
        "شروع؛ CI را بررسی کن",
    ],
)
def test_repository_maintenance_never_enters_ce_runtime(
    message: str,
    tmp_path: Path,
) -> None:
    intake = write_json(tmp_path, "ce-input.json", valid_input_value())
    result = route(message, [intake])

    assert result["activation_authorized"] is False
    assert result["operating_mode"] == "repository_maintenance"
    assert result["route"] == "repository_maintenance"
    assert result["pipeline_execution"] == "not_a_ce_project_run"
    assert result["runtime_state"] == "NOT_APPLICABLE"


def test_explicit_repository_maintenance_mode_wins(tmp_path: Path) -> None:
    intake = write_json(tmp_path, "ce-input.json", valid_input_value())
    result = route(
        "فایل را بررسی کن",
        [intake],
        operating_mode="repository_maintenance",
    )
    assert result["route"] == "repository_maintenance"


def test_active_ce_run_is_accepted_but_not_required(tmp_path: Path) -> None:
    intake = write_json(tmp_path, "ce-input.json", valid_input_value())

    inactive = route(
        "فایل",
        [intake],
        operating_mode="active_ce_run",
        active_ce_run=False,
    )
    active = route(
        "فایل",
        [intake],
        operating_mode="active_ce_run",
        active_ce_run=True,
    )

    assert inactive["route"] == "architect_intake_validation"
    assert active["route"] == "architect_intake_validation"
    assert inactive["authorization_reason"] == active["authorization_reason"]


@pytest.mark.parametrize(
    ("name", "value", "warning_code"),
    [
        (
            "receipt.json",
            receipt_value(handoff_allowed=False),
            "CE_RUNTIME_EXTRA_RECEIPT_IGNORED",
        ),
        (
            "legacy.json",
            legacy_input_value(),
            "CE_RUNTIME_EXTRA_LEGACY_INPUT_IGNORED",
        ),
        (
            "wrong-stage.json",
            {"schema_id": "ev4-architect-stage-payload@1.0.0"},
            "CE_RUNTIME_EXTRA_WRONG_STAGE_ARTIFACT_IGNORED",
        ),
        (
            "unrelated.json",
            {"notes": ["not CE input"]},
            "CE_RUNTIME_EXTRA_IRRELEVANT_FILE_IGNORED",
        ),
    ],
)
def test_extra_noncanonical_files_warn_without_blocking_valid_input(
    tmp_path: Path,
    name: str,
    value: dict[str, Any],
    warning_code: str,
) -> None:
    intake = write_json(tmp_path, "ce-input.json", valid_input_value())
    extra = write_json(tmp_path, name, value)

    result = route("بررسی کن", [intake, extra])

    assert result["route"] == "architect_intake_validation"
    assert result["runtime_state"] == "REVIEW_ACTIVE"
    assert warning_code in {item["code"] for item in result["warnings"]}
    assert str(extra) in result["ignored_attachment_paths"]


def test_malformed_extra_file_warns_without_blocking_valid_input(
    tmp_path: Path,
) -> None:
    intake = write_json(tmp_path, "ce-input.json", valid_input_value())
    malformed = tmp_path / "notes.json"
    malformed.write_text("{not-json", encoding="utf-8")

    result = route("بررسی کن", [intake, malformed])

    assert result["route"] == "architect_intake_validation"
    assert "CE_RUNTIME_EXTRA_UNREADABLE_FILE_IGNORED" in {
        item["code"] for item in result["warnings"]
    }


def test_invalid_schema_input_is_rejected(tmp_path: Path) -> None:
    invalid = valid_input_value()
    invalid["schema_id"] = "ev4-ce-architect-stage-intake@9.9.9"
    path = write_json(tmp_path, "invalid.json", invalid)

    result = route("بررسی کن", [path])

    assert result["route"] == "blocked_invalid_input"
    assert result["runtime_state"] == "INTAKE_VALIDATING"
    assert result["pipeline_execution"] == "forbidden"


def test_invalid_canonical_semantics_are_rejected(tmp_path: Path) -> None:
    invalid = valid_input_value()
    invalid["project_gate_transition"]["transition_id"] = (
        "ev4-wrong-transition@1.0.0"
    )
    path = write_json(tmp_path, "invalid-canonical.json", invalid)

    result = route("بررسی کن", [path])

    assert result["route"] == "blocked_invalid_input"
    assert result["runtime_state"] == "INTAKE_VALIDATING"
    assert result["pipeline_execution"] == "forbidden"


def test_insufficient_evidence_requests_only_blocking_evidence(
    tmp_path: Path,
) -> None:
    path = write_json(tmp_path, "insufficient.json", insufficient_input_value())

    result = route("بررسی کن", [path])

    assert result["route"] == "evidence_required"
    assert result["runtime_state"] == "EVIDENCE_REQUIRED"
    assert result["pipeline_execution"] == "paused"
    assert result["ask_only_for_blocking_evidence"] is True
    assert result["requested_evidence"] == result["diagnostics"]
    assert isinstance(result["source_bundle_required"], bool)


def test_source_bundle_is_not_required_for_complete_valid_input(
    tmp_path: Path,
) -> None:
    intake = write_json(tmp_path, "ce-input.json", valid_input_value())
    result = route("بررسی کن", [intake])

    assert result["route"] == "architect_intake_validation"
    assert result["source_bundle_required"] is False
    assert result["source_provenance_verification"] == (
        "not_required_for_complete_input"
    )


def test_contradictory_supplied_source_evidence_blocks_reliance(
    tmp_path: Path,
) -> None:
    intake_value = valid_input_value()
    intake_value["project_gate_transition"]["source_bundle_hash"]["value"] = "b" * 64
    intake = write_json(tmp_path, "ce-input.json", intake_value)
    source = write_json(tmp_path, "source.json", source_bundle_wrapper())

    result = route("بررسی کن", [intake, source])

    assert result["route"] == "blocked_source_binding_invalid"
    assert result["runtime_state"] == "EVIDENCE_REQUIRED"
    assert result["source_bundle_required"] is True
    assert result["source_provenance_verification"] == "failed"


def test_receipt_only_remains_nonsemantic(tmp_path: Path) -> None:
    receipt = write_json(tmp_path, "receipt.json", receipt_value())
    result = route("بررسی کن", [receipt])

    assert result["route"] == "waiting_for_ce_input"
    assert result["semantic_input_source"] == "none"
    assert result["receipt_evidence"][0]["receipt_role"] == (
        "diagnostic_nonsemantic"
    )


def test_source_bundle_only_waits_for_ce_input(tmp_path: Path) -> None:
    source = write_json(tmp_path, "source.json", source_bundle_wrapper())
    result = route("بررسی کن", [source])

    assert result["route"] == "waiting_for_ce_input"
    assert result["source_bundle_present_without_ce_input"] is True


def test_request_object_accepts_missing_legacy_active_run_field() -> None:
    request = validator.RoutingRequest.from_value(
        {
            "message": "فایل",
            "operating_mode": "auto",
            "attachments": [],
        }
    )
    assert request.active_ce_run is False


def test_pipeline_contract_preserves_strategy_builder_and_export_guards() -> None:
    manifest = load_json(REPO_ROOT / "manifests/ce_pipeline_manifest.v1.json")
    validator.validate_pipeline(
        load_json(REPO_ROOT / MANIFEST_PATH),
        manifest,
    )


def copy_repository_contract(tmp_path: Path) -> Path:
    for relative in CONTROLLED_PATHS:
        source = REPO_ROOT / relative
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return tmp_path


def write_contract_json(root: Path, relative: Path, value: dict[str, Any]) -> None:
    (root / relative).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def mutate_manifest_and_schema(
    root: Path,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    manifest = load_json(root / MANIFEST_PATH)
    mutation(manifest)
    write_contract_json(root, MANIFEST_PATH, manifest)


@pytest.mark.parametrize(
    ("mutation", "expected_reason"),
    [
        (
            lambda value: value["trigger_policy"].__setitem__(
                "attachment_without_prior_trigger",
                "forbidden",
            ),
            "valid CE input still depends on prior trigger",
        ),
        (
            lambda value: value["canonical_input"].__setitem__(
                "source_binding_required_for_complete_valid_input",
                True,
            ),
            "complete valid CE input still requires a source bundle",
        ),
        (
            lambda value: value["input_precedence"].__setitem__(
                "valid_plus_noncanonical_extras",
                "blocked_conflicting_evidence",
            ),
            "irrelevant extras still block valid CE input",
        ),
        (
            lambda value: value["runtime_state_model"].__setitem__(
                "external_governance_prerequisites",
                ["PR Inspector"],
            ),
            "runtime state machine still depends on external governance",
        ),
    ],
)
def test_lean_runtime_invariant_weakening_is_rejected(
    tmp_path: Path,
    mutation: Callable[[dict[str, Any]], None],
    expected_reason: str,
) -> None:
    root = copy_repository_contract(tmp_path)
    mutate_manifest_and_schema(root, mutation)
    with pytest.raises(validator.ValidationError, match=expected_reason):
        validator.validate_repository(root)
