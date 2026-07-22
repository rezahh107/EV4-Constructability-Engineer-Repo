from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from ce_bootstrap_spec import *


class ValidationError(RuntimeError):
    """Raised when CE runtime contract validation fails."""


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


def has_repository_maintenance_intent(value: str) -> bool:
    normalized = normalize_trigger(value).casefold()
    return any(term in normalized for term in MAINTENANCE_TERMS)


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
    require(manifest.get("contract_version") == "1.1.0", "wrong contract_version")
    require(
        manifest.get("owner_repository")
        == "rezahh107/EV4-Constructability-Engineer-Repo",
        "wrong owner_repository",
    )
    require(
        manifest.get("activation_mode") == "content_driven_ce_runtime",
        "wrong activation_mode",
    )

    trigger = manifest.get("trigger_policy")
    require(isinstance(trigger, dict), "trigger_policy must be an object")
    require(trigger.get("canonical_trigger") == "شروع", "missing convenience trigger")
    require(
        trigger.get("trigger_type") == "optional_conversation_shortcut",
        "exact start remains an authorization gate",
    )
    require(
        trigger.get("attachment_without_prior_trigger")
        == "inspect_for_valid_ce_input",
        "valid CE input still depends on prior trigger",
    )
    require(
        trigger.get("active_ce_run_is_authorization_gate") is False,
        "active_ce_run remains an authorization gate",
    )
    require(
        trigger.get("repository_maintenance_precedence") == "always",
        "maintenance precedence weakened",
    )
    require(manifest.get("bootstrap_response") == BOOTSTRAP_RESPONSE, "wrong response")

    canonical = manifest.get("canonical_input")
    require(isinstance(canonical, dict), "canonical_input must be an object")
    require(canonical.get("schema_id") == CANONICAL_SCHEMA_ID, "wrong canonical schema")
    require(
        canonical.get("filename_is_authority") is False,
        "filename-only acceptance enabled",
    )
    require(
        canonical.get("source_bundle_policy") == "conditional_correctness_evidence",
        "source bundle policy is not conditional",
    )
    require(
        canonical.get("source_binding_required_for_complete_valid_input") is False,
        "complete valid CE input still requires a source bundle",
    )
    require(
        canonical.get("verify_supplied_relevant_source_bytes") is True,
        "supplied relevant source evidence is not verified",
    )

    receipt = manifest.get("receipt")
    require(isinstance(receipt, dict), "receipt must be an object")
    require(receipt.get("semantic_input") is False, "receipt promoted to semantic input")
    require(receipt.get("required") is False, "receipt became required")
    require(
        receipt.get("with_valid_input_policy") == "warning_only",
        "Receipt-like extras still block valid CE input",
    )

    precedence = manifest.get("input_precedence")
    require(isinstance(precedence, dict), "input_precedence must be an object")
    require(
        precedence.get("multiple_valid_ce_inputs") == "blocked_ambiguous_input",
        "multiple valid CE inputs are not fail-closed",
    )
    require(
        precedence.get("valid_plus_noncanonical_extras") == "continue_with_warnings",
        "irrelevant extras still block valid CE input",
    )
    require(
        precedence.get("automatic_selection") is False,
        "ambiguous auto-selection enabled",
    )

    runtime = manifest.get("runtime_state_model")
    require(isinstance(runtime, dict), "runtime_state_model must be an object")
    require(
        runtime.get("states") == list(RUNTIME_STATES),
        "runtime state model drifted",
    )
    require(
        runtime.get("external_governance_prerequisites") == [],
        "runtime state machine still depends on external governance",
    )

    routes = manifest.get("routing_cases")
    require(isinstance(routes, list), "routing_cases must be an array")
    observed_ids = [
        item.get("case_id") for item in routes if isinstance(item, dict)
    ]
    require(
        observed_ids == list(EXPECTED_ROUTING_CASES),
        "routing case set or order drifted",
    )
    for case_id, expected in EXPECTED_ROUTING_CASES.items():
        observed = route_by_id(manifest, case_id)
        for field in DECISION_FIELDS:
            require(
                field in observed,
                f"routing case {case_id} omits decision field {field}",
            )
            require(
                observed[field] == expected[field],
                f"wrong {case_id}.{field}",
            )

    first = manifest.get("first_stage_routing")
    require(isinstance(first, dict), "first_stage_routing must be an object")
    require(
        first
        == {
            "policy_id": "ce-runtime-first-stage-routing-v1_1",
            "stage_id": "architect_intake_validation",
            "pipeline_manifest_path": "manifests/ce_pipeline_manifest.v1.json",
            "ordinal": 1,
            "mandatory": True,
            "required_input": CANONICAL_SCHEMA_ID,
            "authorization_prerequisites": ["intake_schema_valid", "intake_semantic_valid"],
        },
        "wrong first stage routing contract",
    )

    maintenance = manifest.get("repository_maintenance_exception")
    require(isinstance(maintenance, dict), "repository_maintenance_exception missing")
    require(
        maintenance.get("route") == "repository_maintenance",
        "repository-maintenance route removed",
    )
    require(
        maintenance.get("runtime_pipeline_execution") == "forbidden",
        "maintenance request can enter CE runtime",
    )

    operations = manifest.get("forbidden_pre_validation_operations")
    require(isinstance(operations, list), "forbidden operations must be an array")
    require(
        [item.get("operation") for item in operations if isinstance(item, dict)]
        == list(EXPECTED_FORBIDDEN_OPERATIONS),
        "forbidden operation set or order drifted",
    )
    require(
        manifest.get("controlled_routing_text") == ROUTING_TEXT,
        "controlled routing text drifted",
    )
    require(
        manifest.get("controlled_quick_start_text") == QUICK_START_TEXT,
        "controlled Quick Start text drifted",
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

    by_id = {
        item.get("stage_id"): item
        for item in stages
        if isinstance(item, dict) and isinstance(item.get("stage_id"), str)
    }
    strategy = by_id.get("implementation_strategy_determination") or {}
    require(
        {
            "strategy_unproven",
            "builder_decision_remaining",
            "architect_amendment_required",
        }.issubset(set(strategy.get("blocked_statuses") or [])),
        "strategy completeness gates weakened",
    )
    builder = by_id.get("builder_package_gate") or {}
    require(
        {
            "non_executable_review",
            "blocking_dependencies_present",
            "builder_decision_remaining",
            "unsupported_builder_package_schema",
        }.issubset(set(builder.get("blocked_statuses") or [])),
        "Builder eligibility gates weakened",
    )
    export = by_id.get("project_gate_export") or {}
    require(
        {
            "invalid_artifact",
            "silent_fallback_true",
            "missing_machine_artifact",
        }.issubset(set(export.get("blocked_statuses") or [])),
        "export publication gates weakened",
    )


def validate_documents(
    manifest: dict[str, Any],
    agents: str,
    readme: str,
    project_instructions: str,
    first_run: str,
) -> None:
    documents = {
        "AGENTS.md": agents,
        "README.md": readme,
        "PROJECT_INSTRUCTIONS.md": project_instructions,
        "EV4_FIRST_RUN_GUIDE.md": first_run,
    }
    required_concepts = (
        CANONICAL_SCHEMA_ID,
        "repository_maintenance",
        "source bundle",
        "warning",
        "Builder-ready",
    )
    for name, document in documents.items():
        for concept in required_concepts:
            require(concept in document, f"{name} omits lean runtime concept: {concept}")

    lowered = project_instructions.casefold()
    require(
        "exact phrase is required" not in lowered
        and "must send the exact" not in lowered
        and "only the exact normalized" not in lowered,
        "Project Instructions still require an exact phrase",
    )
    require(
        "optional shortcut" in lowered and "active_ce_run" in project_instructions,
        "Project Instructions do not explain content-driven runtime activation",
    )
    require(
        "source bundle is required for every" not in project_instructions.casefold(),
        "Project Instructions still require source bundle for every run",
    )
    require(
        "multiple valid" in project_instructions,
        "Project Instructions omit ambiguous valid-input blocking",
    )
    require(
        "blocking dependencies" in project_instructions
        and "implementation strategy" in project_instructions,
        "Project Instructions weaken Builder readiness",
    )
    require(
        manifest["controlled_quick_start_text"] in first_run,
        "first-run guide is not bound to quick start",
    )


def validate_status(status: str) -> None:
    required = (
        "CE_LEAN_PERSONAL_RUNTIME:",
        "contract: ev4-ce-conversation-bootstrap@1.1.0",
        "exact_start_authorization_gate: removed",
        "active_run_ticket_gate: removed",
        "source_bundle_policy: conditional_correctness_evidence",
        "extra_irrelevant_files: warning_only",
        "multiple_valid_inputs: blocked_ambiguous_input",
        "builder_readiness_guards: preserved",
        "deterministic_export_guards: preserved",
        "production_ready: false",
    )
    for item in required:
        require(item in status, f"STATUS.md missing lean runtime truth: {item}")


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
        "contract": "ev4-ce-conversation-bootstrap@1.1.0",
        "trigger": "optional_conversation_shortcut",
        "routing_cases": len(manifest["routing_cases"]),
        "forbidden_operations": len(manifest["forbidden_pre_validation_operations"]),
        "first_stage": manifest["first_stage_routing"]["stage_id"],
        "source_binding": "conditional_correctness_evidence",
        "receipt_validation": "diagnostic_nonsemantic",
        "runtime_states": list(RUNTIME_STATES),
    }
