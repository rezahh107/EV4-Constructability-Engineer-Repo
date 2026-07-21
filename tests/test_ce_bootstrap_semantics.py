from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Callable
import pytest
import sys
SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from ce_bootstrap_test_support import *

def test_canonical_repository_contract_passes() -> None:
    result = validator.validate_repository(REPO_ROOT)
    assert result == {
        "contract": "ev4-ce-conversation-bootstrap@1.0.0",
        "trigger": "شروع",
        "routing_cases": 13,
        "forbidden_operations": 12,
        "first_stage": "architect_intake_validation",
        "source_binding": "required_and_verified_from_supplied_bytes",
        "receipt_validation": "unverified_diagnostic_untrusted",
    }


@pytest.mark.parametrize(
    ("message", "expected_authorized", "expected_route"),
    [
        ("شروع", True, "waiting_for_ce_input"),
        ("  \nشروع\t", True, "waiting_for_ce_input"),
        (unicodedata.normalize("NFD", "شروع"), True, "waiting_for_ce_input"),
        ("شروع کن", False, "no_bootstrap_authorization"),
        ("START", False, "no_bootstrap_authorization"),
    ],
)
def test_integrated_trigger_authorization(
    message: str, expected_authorized: bool, expected_route: str
) -> None:
    result = route(message)
    assert_explicit_result(result)
    assert result["activation_authorized"] is expected_authorized
    assert result["route"] == expected_route
    assert result["pipeline_execution"] == "forbidden"


def test_start_with_one_valid_input_and_bound_source_routes_first_stage(
    tmp_path: Path,
) -> None:
    intake, source = valid_pair(tmp_path)
    result = route("شروع", [intake, source])
    assert_explicit_result(result)
    assert result["activation_authorized"] is True
    assert result["operating_mode"] == "user_facing_new_ce_run"
    assert result["route"] == "architect_intake_validation"
    assert result["pipeline_execution"] == "first_stage_only"
    assert result["semantic_input_source"] == "ce_input_only"
    assert result["source_binding_verified"] is True
    assert set(result["source_binding_evidence"]) == {
        "bundle_id_match",
        "canonical_sha256_match",
        "transition_identity_match",
        "project_gate_producer_match",
        "upstream_producer_match",
    }


def test_start_with_multiple_valid_inputs_blocks_automatic_selection(
    tmp_path: Path,
) -> None:
    first = write_json(tmp_path, "first.json", valid_input_value())
    second = write_json(tmp_path, "second.json", valid_input_value())
    source = write_json(tmp_path, "source.json", source_bundle_wrapper())
    result = route("شروع", [first, second, source])
    assert result["route"] == "blocked_ambiguous_input"
    assert result["pipeline_execution"] == "forbidden"
    assert result["automatic_selection"] is False
    assert len(result["candidate_paths"]) == 2


def test_valid_input_without_startup_context_is_not_authorized(tmp_path: Path) -> None:
    intake, source = valid_pair(tmp_path)
    result = route("این فایل را بررسی کن", [intake, source])
    assert_explicit_result(result)
    assert result["activation_authorized"] is False
    assert result["route"] == "no_bootstrap_authorization"
    assert result["pipeline_execution"] == "forbidden"


@pytest.mark.parametrize(
    "message",
    [
        "شروع؛ PR #40 را اصلاح کن",
        "شروع و repository را audit کن",
        "شروع، کد و تست ریپو را بررسی کن",
    ],
)
def test_repository_maintenance_containing_start_never_enters_ce_pipeline(
    message: str, tmp_path: Path
) -> None:
    intake, source = valid_pair(tmp_path)
    result = route(message, [intake, source])
    assert_explicit_result(result)
    assert result["activation_authorized"] is False
    assert result["operating_mode"] == "repository_maintenance"
    assert result["route"] == "repository_maintenance"
    assert result["pipeline_execution"] == "not_a_ce_project_run"
    assert result["trigger_not_authorization"] is True


def test_explicit_repository_maintenance_mode_wins_even_without_keyword(
    tmp_path: Path,
) -> None:
    intake, source = valid_pair(tmp_path)
    result = route(
        "شروع",
        [intake, source],
        operating_mode="repository_maintenance",
    )
    assert result["route"] == "repository_maintenance"
    assert result["pipeline_execution"] == "not_a_ce_project_run"


def test_authorized_active_ce_run_may_receive_later_attachment(tmp_path: Path) -> None:
    intake, source = valid_pair(tmp_path)
    result = route(
        "فایل‌های بعدی",
        [intake, source],
        operating_mode="active_ce_run",
        active_ce_run=True,
    )
    assert result["activation_authorized"] is True
    assert result["authorization_reason"] == "authorized_active_ce_run"
    assert result["route"] == "architect_intake_validation"


def test_active_mode_flag_without_active_run_is_not_authorization(tmp_path: Path) -> None:
    intake, source = valid_pair(tmp_path)
    result = route(
        "فایل‌های بعدی",
        [intake, source],
        operating_mode="active_ce_run",
        active_ce_run=False,
    )
    assert result["activation_authorized"] is False
    assert result["route"] == "no_bootstrap_authorization"


def test_missing_source_bundle_blocks_valid_intake(tmp_path: Path) -> None:
    intake = write_json(tmp_path, "ce-input.json", valid_input_value())
    result = route("شروع", [intake])
    assert result["route"] == "blocked_source_binding_required"
    assert result["pipeline_execution"] == "forbidden"
    assert result["source_provenance_verification"] == (
        "unavailable_missing_source_bundle_bytes"
    )


def test_fabricated_source_bundle_hash_is_rejected(tmp_path: Path) -> None:
    intake_value = valid_input_value()
    intake_value["project_gate_transition"]["source_bundle_hash"]["value"] = "b" * 64
    intake = write_json(tmp_path, "ce-input.json", intake_value)
    source = write_json(tmp_path, "source.json", source_bundle_wrapper())
    result = route("شروع", [intake, source])
    assert result["route"] == "blocked_source_binding_invalid"
    assert "CE_I21_SOURCE_BUNDLE_HASH_MISMATCH" in {
        item["code"] for item in result["diagnostics"]
    }


def test_correct_bundle_id_with_wrong_bytes_is_rejected(tmp_path: Path) -> None:
    source_value = source_bundle_wrapper()
    source_value["source_bundle"]["payload"]["stage"] = "tampered"
    intake = write_json(tmp_path, "ce-input.json", valid_input_value())
    source = write_json(tmp_path, "source.json", source_value)
    result = route("شروع", [intake, source])
    assert result["route"] == "blocked_source_binding_invalid"
    assert "CE_I21_SOURCE_BUNDLE_HASH_MISMATCH" in {
        item["code"] for item in result["diagnostics"]
    }


def test_correct_bytes_shape_with_wrong_bundle_id_is_rejected(tmp_path: Path) -> None:
    source_value = source_bundle_wrapper()
    source_value["source_bundle"]["bundle_id"] = "wrong-bundle"
    intake = write_json(tmp_path, "ce-input.json", valid_input_value())
    source = write_json(tmp_path, "source.json", source_value)
    result = route("شروع", [intake, source])
    assert result["route"] == "blocked_source_binding_invalid"
    assert "CE_I21_SOURCE_BUNDLE_ID_MISMATCH" in {
        item["code"] for item in result["diagnostics"]
    }


def test_mismatched_transition_identity_never_reaches_first_stage(
    tmp_path: Path,
) -> None:
    intake_value = valid_input_value()
    intake_value["project_gate_transition"]["transition_id"] = (
        "ev4-wrong-transition@1.0.0"
    )
    intake = write_json(tmp_path, "ce-input.json", intake_value)
    source = write_json(tmp_path, "source.json", source_bundle_wrapper())
    result = route("شروع", [intake, source])
    assert result["route"] == "blocked_invalid_input"
    assert result["pipeline_execution"] == "forbidden"


def test_upstream_source_producer_mismatch_is_rejected(tmp_path: Path) -> None:
    source_value = source_bundle_wrapper()
    source_value["source_bundle"]["produced_by"]["repository"] = "wrong/repo"
    intake_value = valid_input_value()
    source = source_value["source_bundle"]
    canonical = json.dumps(
        source, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    import hashlib

    intake_value["project_gate_transition"]["source_bundle_hash"]["value"] = (
        hashlib.sha256(canonical).hexdigest()
    )
    intake = write_json(tmp_path, "ce-input.json", intake_value)
    source_path = write_json(tmp_path, "source.json", source_value)
    result = route("شروع", [intake, source_path])
    assert result["route"] == "blocked_source_binding_invalid"
    assert "CE_BOOTSTRAP_SOURCE_PRODUCER_MISMATCH" in {
        item["code"] for item in result["diagnostics"]
    }


def test_project_gate_bundle_payload_data_owner_path_is_accepted(
    tmp_path: Path,
) -> None:
    source_value = source_bundle_wrapper()
    source_bundle = source_value["source_bundle"]
    architect_payload = source_bundle["payload"]
    source_bundle["payload"] = {
        "schema_id": architect_payload["schema_id"],
        "data": architect_payload,
    }

    intake_value = valid_input_value()
    canonical = json.dumps(
        source_bundle,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    import hashlib

    intake_value["project_gate_transition"]["source_bundle_hash"]["value"] = (
        hashlib.sha256(canonical).hexdigest()
    )

    intake = write_json(tmp_path, "ce-input.json", intake_value)
    source = write_json(tmp_path, "architect-source-bundle.json", source_value)
    result = route("شروع", [intake, source])

    assert result["route"] == "architect_intake_validation"
    assert result["pipeline_execution"] == "first_stage_only"
    assert result["source_binding_verified"] is True
    assert result["source_provenance_verification"] == "verified"


@pytest.mark.parametrize(
    ("name", "value", "expected_issue"),
    [
        ("well-shaped.json", receipt_value(), None),
        (
            "schema-version-only.json",
            {"schema_version": "project-gate-a2c-receipt.v1"},
            "missing_transition",
        ),
        (
            "wrong-transition.json",
            receipt_value(
                transition={"id": "wrong-transition", "version": "1.0.0"}
            ),
            "wrong_transition",
        ),
        (
            "handoff-false.json",
            receipt_value(handoff_allowed=False),
            "handoff_not_allowed",
        ),
        (
            "other-bundle.json",
            receipt_value(source_bundle_id="another-source-bundle"),
            None,
        ),
    ],
)
def test_receipt_like_objects_remain_unverified_and_untrusted(
    tmp_path: Path, name: str, value: dict[str, Any], expected_issue: str | None
) -> None:
    receipt = write_json(tmp_path, name, value)
    result = route("شروع", [receipt])
    assert result["route"] == "waiting_for_ce_input"
    assert result["receipt_role"] == "diagnostic_untrusted"
    evidence = result["receipt_evidence"][0]
    assert evidence["receipt_like_attachment"] is True
    assert evidence["receipt_validation_status"] == "unverified"
    assert evidence["receipt_role"] == "diagnostic_untrusted"
    if expected_issue:
        assert expected_issue in evidence["observed_issues"]


def test_malformed_receipt_is_invalid_not_audit_evidence(tmp_path: Path) -> None:
    receipt = tmp_path / "project-gate-a2c-receipt.json"
    receipt.write_text("{not-json", encoding="utf-8")
    result = route("شروع", [receipt])
    assert result["route"] == "blocked_invalid_input"
    assert result["pipeline_execution"] == "forbidden"
    assert result["receipt_role"] != "optional_audit_evidence"


def test_receipt_only_never_becomes_semantic_input(tmp_path: Path) -> None:
    receipt = write_json(tmp_path, "receipt.json", receipt_value())
    result = route("شروع", [receipt])
    assert result["route"] == "waiting_for_ce_input"
    assert result["semantic_input_source"] == "none"
    assert result["pipeline_execution"] == "forbidden"


def test_valid_pair_plus_invalid_receipt_blocks_as_conflicting_evidence(
    tmp_path: Path,
) -> None:
    intake, source = valid_pair(tmp_path)
    receipt = write_json(
        tmp_path,
        "receipt.json",
        receipt_value(handoff_allowed=False),
    )
    result = route("شروع", [intake, source, receipt])
    assert result["route"] == "blocked_conflicting_evidence"
    assert result["pipeline_execution"] == "forbidden"
    assert result["receipt_role"] == "diagnostic_untrusted"
    assert "handoff_not_allowed" in result["receipt_evidence"][0]["observed_issues"]


def mixed_candidate(tmp_path: Path, kind: str) -> Path:
    if kind == "invalid_canonical":
        value = valid_input_value()
        value["project_gate_transition"]["transition_id"] = "ev4-wrong-transition@1.0.0"
        return write_json(tmp_path, "invalid-canonical.json", value)
    if kind == "insufficient":
        return write_json(tmp_path, "insufficient.json", insufficient_input_value())
    if kind == "legacy":
        return write_json(tmp_path, "legacy.json", legacy_input_value())
    if kind == "wrong_stage":
        return write_json(
            tmp_path,
            "wrong-stage.json",
            {"schema_id": "ev4-architect-stage-payload@1.0.0"},
        )
    if kind == "receipt":
        return write_json(tmp_path, "receipt.json", receipt_value())
    raise AssertionError(kind)


@pytest.mark.parametrize(
    "kind",
    ["invalid_canonical", "insufficient", "legacy", "wrong_stage", "receipt"],
)
def test_valid_pair_mixed_with_any_candidate_conflict_blocks(
    tmp_path: Path, kind: str
) -> None:
    intake, source = valid_pair(tmp_path)
    conflict = mixed_candidate(tmp_path, kind)
    result = route("شروع", [intake, source, conflict])
    assert result["route"] == "blocked_conflicting_evidence"
    assert result["pipeline_execution"] == "forbidden"
    assert result["automatic_selection"] is False


def test_multiple_receipt_like_objects_block(tmp_path: Path) -> None:
    first = write_json(tmp_path, "receipt-1.json", receipt_value())
    second = write_json(tmp_path, "receipt-2.json", receipt_value())
    result = route("شروع", [first, second])
    assert result["route"] == "blocked_conflicting_evidence"
    assert len(result["receipt_evidence"]) == 2


def test_source_bundle_alone_does_not_create_a_ce_run(tmp_path: Path) -> None:
    source = write_json(tmp_path, "source.json", source_bundle_wrapper())
    unauthorized = route("فایل", [source])
    assert unauthorized["route"] == "no_bootstrap_authorization"
    authorized = route("شروع", [source])
    assert authorized["route"] == "waiting_for_ce_input"
    assert authorized["source_bundle_present_without_ce_input"] is True


def test_request_object_requires_all_integrated_fields() -> None:
    with pytest.raises(validator.ValidationError, match="missing field: active_ce_run"):
        validator.RoutingRequest.from_value(
            {"message": "شروع", "operating_mode": "auto", "attachments": []}
        )


def test_executable_results_match_manifest_invariant_matrix(tmp_path: Path) -> None:
    manifest = load_json(REPO_ROOT / MANIFEST_PATH)
    intake, source = valid_pair(tmp_path)
    scenarios = {
        "CE-BOOT-ROUTE-BARE-START": route("شروع"),
        "CE-BOOT-ROUTE-UNAUTHORIZED": route("START", [intake, source]),
        "CE-BOOT-ROUTE-VALID-BOUND-INPUT": route("شروع", [intake, source]),
        "CE-BOOT-ROUTE-SOURCE-BINDING-MISSING": route("شروع", [intake]),
        "CE-BOOT-ROUTE-REPOSITORY-MAINTENANCE": route("شروع PR #40", [intake, source]),
    }
    by_id = {item["case_id"]: item for item in manifest["routing_cases"]}
    for case_id, result in scenarios.items():
        assert result["case_id"] == case_id
        for field in validator.DECISION_FIELDS:
            assert result[field] == by_id[case_id][field]


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


def route_by_id(value: dict[str, Any], case_id: str) -> dict[str, Any]:
    return next(item for item in value["routing_cases"] if item["case_id"] == case_id)


def mutate_both_manifest_and_schema(
    root: Path, mutation: Callable[[dict[str, Any]], None]
) -> None:
    manifest = load_json(root / MANIFEST_PATH)
    mutation(manifest)
    write_contract_json(root, MANIFEST_PATH, manifest)
    schema = load_json(root / SCHEMA_PATH)
    schema["const"] = copy.deepcopy(manifest)
    write_contract_json(root, SCHEMA_PATH, schema)


COORDINATED_DRIFT_MUTATIONS: tuple[
    tuple[str, Callable[[dict[str, Any]], None], str], ...
] = (
    (
        "first_stage_only_to_full_pipeline",
        lambda value: route_by_id(
            value, "CE-BOOT-ROUTE-VALID-BOUND-INPUT"
        ).__setitem__("pipeline_execution", "full_pipeline"),
        "pipeline_execution",
    ),
    (
        "forbidden_to_allowed",
        lambda value: route_by_id(value, "CE-BOOT-ROUTE-UNAUTHORIZED").__setitem__(
            "pipeline_execution", "allowed"
        ),
        "pipeline_execution",
    ),
    (
        "receipt_required_false_to_true",
        lambda value: route_by_id(
            value, "CE-BOOT-ROUTE-VALID-BOUND-INPUT"
        ).__setitem__("receipt_required", True),
        "receipt_required",
    ),
    (
        "semantic_input_source_to_receipt",
        lambda value: route_by_id(
            value, "CE-BOOT-ROUTE-VALID-BOUND-INPUT"
        ).__setitem__("semantic_input_source", "receipt"),
        "semantic_input_source",
    ),
    (
        "automatic_selection_false_to_true",
        lambda value: route_by_id(
            value, "CE-BOOT-ROUTE-AMBIGUOUS-INPUT"
        ).__setitem__("automatic_selection", True),
        "automatic_selection",
    ),
    (
        "maintenance_route_to_ce_execution",
        lambda value: route_by_id(
            value, "CE-BOOT-ROUTE-REPOSITORY-MAINTENANCE"
        ).update(
            route="architect_intake_validation",
            pipeline_execution="first_stage_only",
        ),
        "CE-BOOT-ROUTE-REPOSITORY-MAINTENANCE",
    ),
    (
        "invalid_input_to_first_stage",
        lambda value: route_by_id(
            value, "CE-BOOT-ROUTE-INVALID-INPUT"
        ).update(
            route="architect_intake_validation",
            pipeline_execution="first_stage_only",
        ),
        "CE-BOOT-ROUTE-INVALID-INPUT",
    ),
    (
        "wrong_artifact_extraction_enabled",
        lambda value: route_by_id(
            value, "CE-BOOT-ROUTE-WRONG-ARTIFACT"
        ).__setitem__("manual_extraction_allowed", True),
        "manual_extraction_allowed",
    ),
    (
        "legacy_silently_canonicalized",
        lambda value: value["compatibility"].update(
            canonical_input_schema="ev4-ce-architect-stage-intake@1.0.0",
            silent_promotion_forbidden=False,
        ),
        "legacy schema silently made canonical",
    ),
)


@pytest.mark.parametrize(
    ("mutation_name", "mutation", "expected_reason"),
    COORDINATED_DRIFT_MUTATIONS,
    ids=[name for name, _, _ in COORDINATED_DRIFT_MUTATIONS],
)
def test_coordinated_manifest_and_schema_weakening_is_rejected_semantically(
    tmp_path: Path,
    mutation_name: str,
    mutation: Callable[[dict[str, Any]], None],
    expected_reason: str,
) -> None:
    root = copy_repository_contract(tmp_path)
    mutate_both_manifest_and_schema(root, mutation)
    with pytest.raises(validator.ValidationError, match=expected_reason):
        validator.validate_repository(root)


def test_controlled_routing_text_is_independently_bound(tmp_path: Path) -> None:
    root = copy_repository_contract(tmp_path)

    def weaken(value: dict[str, Any]) -> None:
        value["controlled_routing_text"] = value["controlled_routing_text"].replace(
            "Missing or mismatched source bundle bytes block CE execution.",
            "Missing source bundle bytes may be ignored.",
        )

    mutate_both_manifest_and_schema(root, weaken)
    with pytest.raises(validator.ValidationError, match="controlled routing text drifted"):
        validator.validate_repository(root)
