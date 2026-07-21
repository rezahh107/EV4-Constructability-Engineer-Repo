#!/usr/bin/env python3
"""Fail-closed validation and attachment routing for the CE bootstrap contract."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

BOOTSTRAP_REL = Path("manifests/ce-conversation-bootstrap.v1.json")
SCHEMA_REL = Path("schemas/ce-conversation-bootstrap.v1.schema.json")
PIPELINE_REL = Path("manifests/ce_pipeline_manifest.v1.json")
INTAKE_SCHEMA_REL = Path("schemas/ce_architect_stage_intake.v1_1.schema.json")
INTAKE_VALIDATOR_REL = Path("scripts/validate-ce-architect-stage-intake.py")
AGENTS_REL = Path("AGENTS.md")
README_REL = Path("README.md")
STATUS_REL = Path("STATUS.md")
PROJECT_INSTRUCTIONS_REL = Path(
    "release/EV4_CE_PROJECT_RELEASE_PACK_v1/PROJECT_INSTRUCTIONS.md"
)
FIRST_RUN_REL = Path(
    "release/EV4_CE_PROJECT_RELEASE_PACK_v1/EV4_FIRST_RUN_GUIDE.md"
)

RESPONSE_START = "<!-- EV4_CE_BOOTSTRAP_RESPONSE_START -->"
RESPONSE_END = "<!-- EV4_CE_BOOTSTRAP_RESPONSE_END -->"
ROUTING_START = "<!-- EV4_CE_BOOTSTRAP_ROUTING_START -->"
ROUTING_END = "<!-- EV4_CE_BOOTSTRAP_ROUTING_END -->"
QUICK_START_START = "<!-- EV4_CE_BOOTSTRAP_QUICK_START_START -->"
QUICK_START_END = "<!-- EV4_CE_BOOTSTRAP_QUICK_START_END -->"

CANONICAL_SCHEMA_ID = "ev4-ce-architect-stage-intake@1.1.0"
RECEIPT_SCHEMA_ID = "project-gate-a2c-receipt.v1"
LEGACY_SCHEMA_IDS = {
    "ev4-ce-architect-stage-intake@1.0.0",
    "architect_ce_input_package.v1",
}
WRONG_STAGE_SCHEMA_IDS = {
    "ev4-architect-stage-payload@1.0.0",
    "producer-gate-export.v1",
    "stage-evidence-bundle.v1",
}
EXPECTED_FORBIDDEN_OPERATIONS = (
    "run_constructability_review",
    "generate_ce_review_units",
    "infer_hidden_dependencies",
    "select_implementation_strategy",
    "emit_builder_executable_package",
    "claim_builder_readiness",
    "emit_ce_project_gate_export",
    "invent_missing_architecture_or_evidence",
    "treat_receipt_as_semantic_input",
    "claim_project_gate_acceptance",
    "claim_real_elementor_validation",
    "claim_responsive_or_production_readiness",
)


class ValidationError(RuntimeError):
    """Raised when CE bootstrap validation fails closed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _reject_constant(value: str) -> None:
    raise ValidationError(f"non-JSON numeric constant is forbidden: {value}")


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        require(key not in value, f"duplicate JSON object key is forbidden: {key}")
        value[key] = item
    return value


def strict_load_json(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"file could not be read: {path}") from exc
    try:
        value = json.loads(
            text,
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicates,
        )
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}"
        ) from exc
    require(isinstance(value, dict), f"{path} must contain a JSON object")
    return value


def load_json(root: Path, relative: Path) -> dict[str, Any]:
    path = root / relative
    require(path.is_file(), f"missing required file: {relative.as_posix()}")
    return strict_load_json(path)


def read_text(root: Path, relative: Path) -> str:
    path = root / relative
    require(path.is_file(), f"missing required file: {relative.as_posix()}")
    return path.read_text(encoding="utf-8")


def normalize_text(value: str) -> str:
    return value.replace("\r\n", "\n").strip()


def normalize_trigger(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip()


def is_bare_start(value: str) -> bool:
    return normalize_trigger(value) == "شروع"


def extract_marked_fenced_text(
    document: str,
    start_marker: str,
    end_marker: str,
    source: Path,
) -> str:
    require(
        document.count(start_marker) == 1 and document.count(end_marker) == 1,
        f"{source.as_posix()} controlled markers missing or duplicated",
    )
    start = document.index(start_marker) + len(start_marker)
    end = document.index(end_marker, start)
    region = normalize_text(document[start:end])
    lines = region.splitlines()
    require(
        len(lines) >= 3 and lines[0].strip() == "```text" and lines[-1].strip() == "```",
        f"{source.as_posix()} controlled region must use one text fence",
    )
    return normalize_text("\n".join(lines[1:-1]))


def schema_error_message(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path) or "<root>"
    return f"bootstrap schema violation at {path}: {error.message}"


def validate_schema(manifest: dict[str, Any], schema: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(manifest),
        key=lambda item: list(item.absolute_path),
    )
    require(not errors, schema_error_message(errors[0]) if errors else "schema failure")


def route_by_id(manifest: dict[str, Any], route_id: str) -> dict[str, Any]:
    routes = manifest.get("routing_cases")
    require(isinstance(routes, list), "routing_cases must be an array")
    matches = [
        item
        for item in routes
        if isinstance(item, dict) and item.get("case_id") == route_id
    ]
    require(len(matches) == 1, f"routing case identity missing: {route_id}")
    return matches[0]


def validate_manifest_semantics(manifest: dict[str, Any]) -> None:
    require(
        manifest.get("contract_id") == "ev4-ce-conversation-bootstrap",
        "wrong contract_id",
    )
    require(manifest.get("contract_version") == "1.0.0", "wrong contract_version")
    require(
        manifest.get("owner_repository")
        == "rezahh107/EV4-Constructability-Engineer-Repo",
        "wrong owner_repository",
    )
    require(
        manifest.get("activation_mode") == "user_facing_new_ce_run",
        "wrong activation_mode",
    )
    trigger = manifest.get("trigger_policy")
    require(isinstance(trigger, dict), "trigger_policy must be an object")
    require(trigger.get("canonical_trigger") == "شروع", "missing canonical trigger")
    require(
        trigger.get("trigger_type") == "exact_message_after_normalization",
        "wrong trigger type",
    )
    require(
        trigger.get("normalization_policy")
        == {
            "policy_id": "ce-bootstrap-normalization-policy-v1",
            "unicode_normalization": "NFC",
            "trim_surrounding_whitespace": True,
            "case_folding": False,
            "aliases": [],
        },
        "wrong normalization policy",
    )
    require(
        manifest.get("bootstrap_response")
        == """EV4 Constructability Engineer آماده است.

برای شروع بررسی Constructability، فایل `ce-input.json` تولیدشده توسط مسیر `EV4-Project-Gate / architect-to-ce` را ارسال کن.

ورودی باید با قرارداد `ev4-ce-architect-stage-intake@1.1.0` معتبر باشد.
فایل `project-gate-a2c-receipt.json` اختیاری و فقط برای بررسی فنی است؛ جایگزین ورودی CE نیست.

پس از دریافت ورودی معتبر، بررسی از مرحله `architect_intake_validation` آغاز می‌شود.
تا پیش از اعتبارسنجی ورودی، هیچ نتیجه Constructability، استراتژی اجرا یا آمادگی Builder اعلام نمی‌شود.""",
        "wrong exact response text",
    )

    canonical = manifest.get("canonical_input")
    require(isinstance(canonical, dict), "canonical_input must be an object")
    require(
        canonical.get("schema_id") == CANONICAL_SCHEMA_ID,
        "wrong canonical input schema",
    )
    require(
        canonical.get("source_transition")
        == "ev4-architect-to-ce-transition@1.0.0",
        "wrong source transition",
    )
    require(
        canonical.get("filename_is_authority") is False,
        "filename-only acceptance enabled",
    )

    receipt = manifest.get("receipt")
    require(isinstance(receipt, dict), "receipt must be an object")
    require(receipt.get("semantic_input") is False, "receipt promoted to semantic input")
    require(
        receipt.get("reconstruction_source_forbidden") is True,
        "receipt reconstruction route is not forbidden",
    )

    precedence = manifest.get("input_precedence")
    require(isinstance(precedence, dict), "input_precedence must be an object")
    require(
        precedence.get("inspect_attachments_before_questions") is True,
        "attachments are not inspected before questions",
    )
    require(
        precedence.get("automatic_selection") is False,
        "ambiguous auto-selection enabled",
    )

    wrong = route_by_id(manifest, "CE-BOOT-ROUTE-WRONG-ARTIFACT")
    require(
        wrong.get("manual_extraction_allowed") is False,
        "wrong CE-BOOT-ROUTE-WRONG-ARTIFACT.manual_extraction_allowed",
    )

    first = manifest.get("first_stage_routing")
    require(isinstance(first, dict), "first_stage_routing must be an object")
    require(first.get("stage_id") == "architect_intake_validation", "wrong first stage")

    compatibility = manifest.get("compatibility")
    require(isinstance(compatibility, dict), "compatibility must be an object")
    require(
        compatibility.get("canonical_input_schema") == CANONICAL_SCHEMA_ID,
        "legacy schema silently made canonical",
    )

    maintenance = manifest.get("repository_maintenance_exception")
    require(isinstance(maintenance, dict), "repository_maintenance_exception must be an object")
    require(
        maintenance.get("route") == "repository_maintenance",
        "repository-maintenance route removed",
    )

    operations = manifest.get("forbidden_pre_validation_operations")
    require(isinstance(operations, list), "forbidden operations must be an array")
    require(
        [item.get("operation") for item in operations if isinstance(item, dict)]
        == list(EXPECTED_FORBIDDEN_OPERATIONS),
        "forbidden operation set or order drifted",
    )
    require(
        [item.get("operation_id") for item in operations if isinstance(item, dict)]
        == [f"CE-BOOT-PRE-{index:03d}" for index in range(1, 13)],
        "forbidden operation stable IDs drifted",
    )


def validate_pipeline(manifest: dict[str, Any], pipeline: dict[str, Any]) -> None:
    stages = pipeline.get("project_execution_stages")
    require(isinstance(stages, list) and stages, "pipeline manifest has no stages")
    first = stages[0]
    expected = manifest["first_stage_routing"]
    require(isinstance(first, dict), "pipeline first stage is not an object")
    require(first.get("stage_id") == expected["stage_id"], "pipeline first stage drifted")
    require(first.get("ordinal") == 1, "pipeline first-stage ordinal drifted")
    require(first.get("mandatory") is True, "pipeline first stage is not mandatory")
    require(
        first.get("required_inputs") == [CANONICAL_SCHEMA_ID],
        "pipeline first-stage input drifted",
    )


def validate_documents(
    manifest: dict[str, Any],
    agents: str,
    readme: str,
    project_instructions: str,
    first_run: str,
) -> None:
    response = normalize_text(manifest["bootstrap_response"])
    routing = normalize_text(manifest["controlled_routing_text"])
    quick = normalize_text(manifest["controlled_quick_start_text"])

    for source, document in (
        (AGENTS_REL, agents),
        (PROJECT_INSTRUCTIONS_REL, project_instructions),
        (FIRST_RUN_REL, first_run),
    ):
        require(
            extract_marked_fenced_text(document, RESPONSE_START, RESPONSE_END, source)
            == response,
            f"{source.as_posix()} exact response drifted",
        )
    for source, document in (
        (AGENTS_REL, agents),
        (PROJECT_INSTRUCTIONS_REL, project_instructions),
    ):
        require(
            extract_marked_fenced_text(document, ROUTING_START, ROUTING_END, source)
            == routing,
            f"{source.as_posix()} controlled routing drifted",
        )
    for source, document in ((README_REL, readme), (FIRST_RUN_REL, first_run)):
        require(
            extract_marked_fenced_text(
                document, QUICK_START_START, QUICK_START_END, source
            )
            == quick,
            f"{source.as_posix()} Quick Start drifted",
        )

    manifest_ref = BOOTSTRAP_REL.as_posix()
    for source, document in (
        (AGENTS_REL, agents),
        (README_REL, readme),
        (PROJECT_INSTRUCTIONS_REL, project_instructions),
        (FIRST_RUN_REL, first_run),
    ):
        require(
            manifest_ref in document,
            f"{source.as_posix()} omits canonical manifest reference",
        )

    require(
        "Only the exact normalized message `شروع` is the canonical trigger."
        in project_instructions,
        "Project Instructions omit شروع",
    )
    require(
        "project-gate-a2c-receipt.json" in project_instructions
        and "جایگزین ورودی CE نیست" in project_instructions
        and "Receipt is semantic CE input" not in project_instructions,
        "Project Instructions contradict Receipt separation",
    )
    require(
        "repository-maintenance" in project_instructions,
        "Project Instructions omit repository-maintenance separation",
    )
    require(
        "filename" in project_instructions.lower()
        and "content" in project_instructions.lower(),
        "Project Instructions omit content-over-filename rule",
    )
    for operation in EXPECTED_FORBIDDEN_OPERATIONS:
        require(
            f"`{operation}`" in project_instructions,
            f"Project Instructions omit forbidden operation {operation}",
        )
    require(
        "architect_intake_validation" in readme,
        "README omits canonical first stage",
    )
    require(
        "Never extract nested `result.output`" in readme
        and "Extract nested `result.output`" not in readme,
        "README tells operator to use the wrong artifact path",
    )


def validate_status(status: str) -> None:
    required = (
        "CE_CONVERSATION_BOOTSTRAP_V1:",
        "implementation_state: implemented_in_pr_pending_exact_head_ci_and_independent_review",
        "contract: ev4-ce-conversation-bootstrap@1.0.0",
        "canonical_trigger: شروع",
        f"canonical_input: {CANONICAL_SCHEMA_ID}",
        "first_stage: architect_intake_validation",
        "deployable_project_instructions: implemented",
        "semantic_validator: implemented",
        "mutation_suite: implemented",
        "external_model_host_loading: unverified",
        "real_non_synthetic_ce_run: insufficient_evidence",
        "production_readiness_claim: not_made",
    )
    for item in required:
        require(item in status, f"STATUS.md missing bootstrap truth: {item}")
    require(
        "project_status:" in status and "  production_ready: false" in status,
        "STATUS.md must preserve production_ready false",
    )
    require(
        "CE_02_POST_MERGE_EXPORTER_AUDIT:" in status
        and "CE_02_POST_MERGE_STATUS_RECONCILIATION:" in status,
        "STATUS.md historical PR #37/#38 evidence was not preserved",
    )


def validate_repository(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest = load_json(root, BOOTSTRAP_REL)
    schema = load_json(root, SCHEMA_REL)
    pipeline = load_json(root, PIPELINE_REL)
    require((root / INTAKE_SCHEMA_REL).is_file(), "official CE intake schema is missing")
    require(
        (root / INTAKE_VALIDATOR_REL).is_file(),
        "official CE intake validator is missing",
    )
    validate_manifest_semantics(manifest)
    validate_schema(manifest, schema)
    validate_pipeline(manifest, pipeline)
    validate_documents(
        manifest,
        read_text(root, AGENTS_REL),
        read_text(root, README_REL),
        read_text(root, PROJECT_INSTRUCTIONS_REL),
        read_text(root, FIRST_RUN_REL),
    )
    validate_status(read_text(root, STATUS_REL))
    return {
        "contract": "ev4-ce-conversation-bootstrap@1.0.0",
        "trigger": "شروع",
        "routing_cases": len(manifest["routing_cases"]),
        "forbidden_operations": len(manifest["forbidden_pre_validation_operations"]),
        "first_stage": manifest["first_stage_routing"]["stage_id"],
    }


def load_official_validator(root: Path) -> Any:
    path = root / INTAKE_VALIDATOR_REL
    name = "ce_bootstrap_official_intake_validator"
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "official validator load failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module.CEArchitectStageIntakeValidator(root)


def attachment_kind(value: dict[str, Any]) -> str:
    schema_id = value.get("schema_id")
    if schema_id == CANONICAL_SCHEMA_ID:
        return "canonical"
    if schema_id in LEGACY_SCHEMA_IDS:
        return "legacy"
    if schema_id in WRONG_STAGE_SCHEMA_IDS:
        return "wrong"
    if value.get("schema_version") == RECEIPT_SCHEMA_ID:
        return "receipt"
    if {"result", "final_stage_bundle", "transition"} & set(value):
        return "wrong"
    return "invalid"


def route_attachments(root: Path, attachments: Iterable[Path]) -> dict[str, Any]:
    root = root.resolve()
    official = load_official_validator(root)
    buckets: dict[str, list[dict[str, Any]]] = {
        key: []
        for key in ("valid", "insufficient", "invalid", "receipt", "legacy", "wrong")
    }
    for supplied in attachments:
        path = supplied if supplied.is_absolute() else Path.cwd() / supplied
        try:
            value = strict_load_json(path)
        except ValidationError as exc:
            buckets["invalid"].append({"path": str(path), "reason": str(exc)})
            continue
        kind = attachment_kind(value)
        if kind == "canonical":
            result = official.validate_value(value)
            record = {
                "path": str(path),
                "validation_status": result["status"],
                "diagnostics": result["diagnostics"],
            }
            target = (
                "valid"
                if result["status"] == "valid"
                else "insufficient"
                if result["status"] == "insufficient_evidence"
                else "invalid"
            )
            buckets[target].append(record)
        else:
            buckets[kind].append({"path": str(path)})

    if len(buckets["valid"]) > 1:
        return {
            "route": "blocked_ambiguous_input",
            "diagnostic_code": "CE_BOOTSTRAP_AMBIGUOUS_INPUT",
            "pipeline_execution": "forbidden",
            "automatic_selection": False,
            "candidate_paths": [item["path"] for item in buckets["valid"]],
        }
    if len(buckets["valid"]) == 1:
        return {
            "route": "architect_intake_validation",
            "pipeline_execution": "first_stage_only",
            "semantic_input_source": "ce_input_only",
            "ce_input_path": buckets["valid"][0]["path"],
            "receipt_present": bool(buckets["receipt"]),
            "receipt_required": False,
            "receipt_role": (
                "optional_audit_evidence" if buckets["receipt"] else "absent"
            ),
        }
    if buckets["insufficient"]:
        return {
            "route": "blocked_invalid_input",
            "diagnostic_code": "CE_BOOTSTRAP_INTAKE_INSUFFICIENT_EVIDENCE",
            "pipeline_execution": "forbidden",
            "ask_only_for_blocking_evidence": True,
            "diagnostics": buckets["insufficient"][0]["diagnostics"],
        }
    if buckets["invalid"]:
        return {
            "route": "blocked_invalid_input",
            "diagnostic_code": "CE_BOOTSTRAP_INVALID_INPUT",
            "pipeline_execution": "forbidden",
            "diagnostics": buckets["invalid"],
        }
    if buckets["legacy"]:
        return {
            "route": "blocked_require_canonical_v1_1",
            "diagnostic_code": "CE_BOOTSTRAP_LEGACY_INPUT_NOT_CANONICAL",
            "pipeline_execution": "forbidden",
            "explicit_compatibility_authorization_required": True,
        }
    if buckets["wrong"]:
        return {
            "route": "blocked_require_official_project_gate_output",
            "diagnostic_code": "CE_BOOTSTRAP_OFFICIAL_CE_INPUT_REQUIRED",
            "pipeline_execution": "forbidden",
            "manual_extraction_allowed": False,
        }
    if buckets["receipt"]:
        return {
            "route": "waiting_for_ce_input",
            "diagnostic_code": "CE_BOOTSTRAP_RECEIPT_NOT_SEMANTIC_INPUT",
            "pipeline_execution": "forbidden",
            "receipt_retained_for_diagnostics": True,
            "receipt_must_not_be_promoted": True,
        }
    return {
        "route": "waiting_for_ce_input",
        "diagnostic_code": "CE_BOOTSTRAP_INPUT_REQUIRED",
        "pipeline_execution": "forbidden",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--attachment", action="append", type=Path, default=[])
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    if args.attachment:
        result = route_attachments(args.root, args.attachment)
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        else:
            print(f"route: {result['route']}")
            if result.get("diagnostic_code"):
                print(f"diagnostic_code: {result['diagnostic_code']}")
        return 0 if result["route"] == "architect_intake_validation" else 1

    result = validate_repository(args.root)
    print("CE bootstrap semantic validation passed.")
    print(f"Contract: {result['contract']}")
    print(f"Trigger: {result['trigger']}")
    print(f"Routing cases: {result['routing_cases']}")
    print(f"Stable forbidden operations: {result['forbidden_operations']}")
    print(f"First stage: {result['first_stage']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"CE bootstrap semantic validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
