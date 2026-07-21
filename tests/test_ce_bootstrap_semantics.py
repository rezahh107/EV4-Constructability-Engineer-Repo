from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Callable

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "check-ce-bootstrap.py"

spec = importlib.util.spec_from_file_location("check_ce_bootstrap", VALIDATOR_PATH)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
sys.modules["check_ce_bootstrap"] = validator
spec.loader.exec_module(validator)

MANIFEST_PATH = Path("manifests/ce-conversation-bootstrap.v1.json")
PROJECT_INSTRUCTIONS_PATH = Path(
    "release/EV4_CE_PROJECT_RELEASE_PACK_v1/PROJECT_INSTRUCTIONS.md"
)
FIRST_RUN_PATH = Path(
    "release/EV4_CE_PROJECT_RELEASE_PACK_v1/EV4_FIRST_RUN_GUIDE.md"
)
VALID_INPUT = REPO_ROOT / (
    "fixtures/architect-stage-intake-v1-1/valid/"
    "project-gate-transition-complete.v1_1.json"
)
INSUFFICIENT_INPUT = REPO_ROOT / (
    "fixtures/architect-stage-intake-v1-1/insufficient-evidence/"
    "project-gate-transition-insufficient.v1_1.json"
)
LEGACY_INPUT = REPO_ROOT / (
    "fixtures/architect-stage-intake/valid/minimal-canonical-intake.v1.json"
)

CONTROLLED_PATHS = (
    Path("AGENTS.md"),
    Path("README.md"),
    Path("STATUS.md"),
    MANIFEST_PATH,
    Path("manifests/ce_pipeline_manifest.v1.json"),
    Path("schemas/ce-conversation-bootstrap.v1.schema.json"),
    Path("schemas/ce_architect_stage_intake.v1.schema.json"),
    Path("schemas/ce_architect_stage_intake.v1_1.schema.json"),
    Path("scripts/validate-ce-architect-stage-intake.py"),
    PROJECT_INSTRUCTIONS_PATH,
    FIRST_RUN_PATH,
)


def copy_repository_contract(tmp_path: Path) -> Path:
    for relative in CONTROLLED_PATHS:
        source = REPO_ROOT / relative
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return tmp_path


def load_json(root: Path, relative: Path = MANIFEST_PATH) -> dict:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def write_json(root: Path, value: dict, relative: Path = MANIFEST_PATH) -> None:
    (root / relative).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def mutate_manifest(root: Path, mutation: Callable[[dict], None]) -> None:
    value = load_json(root)
    mutation(value)
    write_json(root, value)


def replace_text(root: Path, relative: Path, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_text(root: Path, relative: Path, text: str) -> None:
    path = root / relative
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


def route_by_id(value: dict, route_id: str) -> dict:
    return next(item for item in value["routing_cases"] if item["case_id"] == route_id)


def operation_by_name(value: dict, operation: str) -> dict:
    return next(
        item
        for item in value["forbidden_pre_validation_operations"]
        if item["operation"] == operation
    )


def write_attachment(tmp_path: Path, name: str, value: dict) -> Path:
    path = tmp_path / name
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    return path


def valid_input_value() -> dict:
    return json.loads(VALID_INPUT.read_text(encoding="utf-8"))


def receipt_value() -> dict:
    return {
        "schema_version": "project-gate-a2c-receipt.v1",
        "transition": {
            "id": "ev4-architect-to-ce-transition",
            "version": "1.0.0",
        },
        "handoff_allowed": True,
    }


def test_canonical_repository_contract_passes() -> None:
    result = validator.validate_repository(REPO_ROOT)
    assert result == {
        "contract": "ev4-ce-conversation-bootstrap@1.0.0",
        "trigger": "شروع",
        "routing_cases": 10,
        "forbidden_operations": 12,
        "first_stage": "architect_intake_validation",
    }


def test_trigger_normalization_is_exact_and_unicode_safe() -> None:
    assert validator.normalize_trigger(" \nشروع\t") == "شروع"
    assert validator.is_bare_start(" شروع ")
    assert not validator.is_bare_start("شروع کن")
    assert not validator.is_bare_start("START")


def test_valid_ce_input_routes_by_content_even_with_wrong_filename(tmp_path: Path) -> None:
    ce_input = write_attachment(
        tmp_path,
        "project-gate-a2c-receipt.json",
        valid_input_value(),
    )
    result = validator.route_attachments(REPO_ROOT, [ce_input])
    assert result["route"] == "architect_intake_validation"
    assert result["semantic_input_source"] == "ce_input_only"
    assert result["receipt_required"] is False


def test_valid_ce_input_plus_receipt_uses_ce_input_only(tmp_path: Path) -> None:
    ce_input = write_attachment(tmp_path, "renamed-input.json", valid_input_value())
    receipt = write_attachment(tmp_path, "ce-input.json", receipt_value())
    result = validator.route_attachments(REPO_ROOT, [receipt, ce_input])
    assert result["route"] == "architect_intake_validation"
    assert result["semantic_input_source"] == "ce_input_only"
    assert result["receipt_present"] is True
    assert result["receipt_role"] == "optional_audit_evidence"


def test_receipt_only_waits_for_standalone_ce_input(tmp_path: Path) -> None:
    receipt = write_attachment(
        tmp_path,
        "project-gate-a2c-receipt.json",
        receipt_value(),
    )
    result = validator.route_attachments(REPO_ROOT, [receipt])
    assert result["route"] == "waiting_for_ce_input"
    assert result["diagnostic_code"] == "CE_BOOTSTRAP_RECEIPT_NOT_SEMANTIC_INPUT"
    assert result["receipt_must_not_be_promoted"] is True


def test_multiple_valid_candidates_fail_ambiguous(tmp_path: Path) -> None:
    first = write_attachment(tmp_path, "first.json", valid_input_value())
    second = write_attachment(tmp_path, "second.json", valid_input_value())
    result = validator.route_attachments(REPO_ROOT, [first, second])
    assert result["route"] == "blocked_ambiguous_input"
    assert result["automatic_selection"] is False
    assert len(result["candidate_paths"]) == 2


def test_legacy_and_raw_architect_inputs_are_not_promoted(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy.json"
    shutil.copy2(LEGACY_INPUT, legacy)
    raw_architect = write_attachment(
        tmp_path,
        "architect-project-gate.json",
        {"schema_id": "ev4-architect-stage-payload@1.0.0"},
    )
    legacy_result = validator.route_attachments(REPO_ROOT, [legacy])
    raw_result = validator.route_attachments(REPO_ROOT, [raw_architect])
    assert legacy_result["route"] == "blocked_require_canonical_v1_1"
    assert raw_result["route"] == "blocked_require_official_project_gate_output"


def test_insufficient_and_invalid_inputs_block_pipeline(tmp_path: Path) -> None:
    insufficient = tmp_path / "insufficient.json"
    shutil.copy2(INSUFFICIENT_INPUT, insufficient)
    invalid = write_attachment(
        tmp_path,
        "ce-input.json",
        {"schema_id": "ev4-ce-architect-stage-intake@9.9.9"},
    )
    insufficient_result = validator.route_attachments(REPO_ROOT, [insufficient])
    invalid_result = validator.route_attachments(REPO_ROOT, [invalid])
    assert insufficient_result["route"] == "blocked_invalid_input"
    assert insufficient_result["ask_only_for_blocking_evidence"] is True
    assert invalid_result["route"] == "blocked_invalid_input"
    assert invalid_result["pipeline_execution"] == "forbidden"


def wrong_contract_id(root: Path) -> None:
    mutate_manifest(root, lambda value: value.__setitem__("contract_id", "wrong"))


def wrong_contract_version(root: Path) -> None:
    mutate_manifest(root, lambda value: value.__setitem__("contract_version", "9.9.9"))


def wrong_owner(root: Path) -> None:
    mutate_manifest(root, lambda value: value.__setitem__("owner_repository", "other/repo"))


def wrong_activation(root: Path) -> None:
    mutate_manifest(root, lambda value: value.__setitem__("activation_mode", "maintenance"))


def missing_trigger(root: Path) -> None:
    mutate_manifest(root, lambda value: value["trigger_policy"].pop("canonical_trigger"))


def wrong_trigger_type(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: value["trigger_policy"].__setitem__("trigger_type", "substring"),
    )


def wrong_normalization(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: value["trigger_policy"]["normalization_policy"].__setitem__(
            "unicode_normalization", "NFKC"
        ),
    )


def changed_exact_response(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: value.__setitem__(
            "bootstrap_response", value["bootstrap_response"] + "\nاضافه"
        ),
    )


def wrong_input_schema(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: value["canonical_input"].__setitem__(
            "schema_id", "ev4-ce-architect-stage-intake@1.0.0"
        ),
    )


def wrong_source_transition(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: value["canonical_input"].__setitem__(
            "source_transition", "ev4-architect-to-ce-transition@9.9.9"
        ),
    )


def wrong_first_stage(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: value["first_stage_routing"].__setitem__(
            "stage_id", "constructability_review"
        ),
    )


def receipt_promoted(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: value["receipt"].__setitem__("semantic_input", True),
    )


def filename_only_acceptance(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: value["canonical_input"].__setitem__(
            "filename_is_authority", True
        ),
    )


def raw_envelope_extraction(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: route_by_id(
            value, "CE-BOOT-ROUTE-WRONG-ARTIFACT"
        ).__setitem__("manual_extraction_allowed", True),
    )


def pre_validation_review_enabled(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: operation_by_name(
            value, "run_constructability_review"
        ).__setitem__("operation", "run_constructability_review_before_validation"),
    )


def builder_readiness_enabled(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: operation_by_name(
            value, "claim_builder_readiness"
        ).__setitem__("operation", "allow_builder_readiness_claim"),
    )


def project_instructions_omit_start(root: Path) -> None:
    replace_text(
        root,
        PROJECT_INSTRUCTIONS_PATH,
        "Only the exact normalized message `شروع` is the canonical trigger.",
        "No canonical trigger is documented here.",
    )


def project_instructions_contradict_receipt(root: Path) -> None:
    append_text(
        root,
        PROJECT_INSTRUCTIONS_PATH,
        "\nReceipt is semantic CE input.\n",
    )


def agents_routing_drift(root: Path) -> None:
    replace_text(
        root,
        Path("AGENTS.md"),
        "One valid `ev4-ce-architect-stage-intake@1.1.0` routes to `architect_intake_validation`.",
        "One valid input routes directly to `constructability_review`.",
    )


def readme_wrong_artifact(root: Path) -> None:
    append_text(
        root,
        Path("README.md"),
        "\nExtract nested `result.output` and save it as CE input.\n",
    )


def ambiguous_auto_selection(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: value["input_precedence"].__setitem__(
            "automatic_selection", True
        ),
    )


def repository_maintenance_removed(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: value["repository_maintenance_exception"].__setitem__(
            "route", "architect_intake_validation"
        ),
    )


def legacy_silently_canonical(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: value["compatibility"].__setitem__(
            "canonical_input_schema", "ev4-ce-architect-stage-intake@1.0.0"
        ),
    )


def receipt_reconstruction_enabled(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: value["receipt"].__setitem__(
            "reconstruction_source_forbidden", False
        ),
    )


def attachments_questions_first(root: Path) -> None:
    mutate_manifest(
        root,
        lambda value: value["input_precedence"].__setitem__(
            "inspect_attachments_before_questions", False
        ),
    )


MUTATIONS: tuple[tuple[str, Callable[[Path], None], str], ...] = (
    ("changed_contract_id", wrong_contract_id, "wrong contract_id"),
    ("changed_contract_version", wrong_contract_version, "wrong contract_version"),
    ("changed_owner_repository", wrong_owner, "wrong owner_repository"),
    ("changed_activation_mode", wrong_activation, "wrong activation_mode"),
    ("missing_canonical_trigger", missing_trigger, "missing canonical trigger"),
    ("changed_trigger_type", wrong_trigger_type, "wrong trigger type"),
    ("changed_normalization_rule", wrong_normalization, "wrong normalization policy"),
    ("changed_exact_response", changed_exact_response, "wrong exact response text"),
    ("changed_canonical_input_schema", wrong_input_schema, "wrong canonical input schema"),
    ("changed_source_transition", wrong_source_transition, "wrong source transition"),
    ("changed_first_pipeline_stage", wrong_first_stage, "wrong first stage"),
    (
        "receipt_promoted_to_semantic_input",
        receipt_promoted,
        "receipt promoted to semantic input",
    ),
    (
        "filename_only_acceptance_enabled",
        filename_only_acceptance,
        "filename-only acceptance enabled",
    ),
    (
        "raw_envelope_extraction_enabled",
        raw_envelope_extraction,
        "manual_extraction_allowed",
    ),
    (
        "pre_validation_review_enabled",
        pre_validation_review_enabled,
        "forbidden operation set",
    ),
    (
        "builder_readiness_claim_enabled",
        builder_readiness_enabled,
        "forbidden operation set",
    ),
    (
        "project_instructions_omit_start",
        project_instructions_omit_start,
        "Project Instructions omit شروع",
    ),
    (
        "project_instructions_contradict_receipt",
        project_instructions_contradict_receipt,
        "Project Instructions contradict Receipt separation",
    ),
    ("agents_routing_drift", agents_routing_drift, "AGENTS.md controlled routing drifted"),
    (
        "readme_wrong_artifact",
        readme_wrong_artifact,
        "README tells operator to use the wrong artifact path",
    ),
    (
        "ambiguous_auto_selection_enabled",
        ambiguous_auto_selection,
        "ambiguous auto-selection enabled",
    ),
    (
        "repository_maintenance_exception_removed",
        repository_maintenance_removed,
        "repository-maintenance route removed",
    ),
    (
        "legacy_v1_silently_canonical",
        legacy_silently_canonical,
        "legacy schema silently made canonical",
    ),
    (
        "receipt_reconstruction_enabled",
        receipt_reconstruction_enabled,
        "receipt reconstruction route is not forbidden",
    ),
    (
        "attachments_questions_first",
        attachments_questions_first,
        "attachments are not inspected before questions",
    ),
)


@pytest.mark.parametrize(
    ("mutation_name", "mutate", "expected_reason"),
    MUTATIONS,
    ids=[name for name, _, _ in MUTATIONS],
)
def test_semantic_mutations_fail_closed(
    tmp_path: Path,
    mutation_name: str,
    mutate: Callable[[Path], None],
    expected_reason: str,
) -> None:
    fixture_root = copy_repository_contract(tmp_path)
    mutate(fixture_root)
    with pytest.raises(validator.ValidationError, match=expected_reason):
        validator.validate_repository(fixture_root)
