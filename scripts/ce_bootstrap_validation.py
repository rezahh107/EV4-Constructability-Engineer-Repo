from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator
from ce_bootstrap_spec import *

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
        value = json.loads(text, parse_constant=_reject_constant, object_pairs_hook=_reject_duplicates)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}") from exc
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


def extract_marked_fenced_text(document: str, start_marker: str, end_marker: str, source: Path) -> str:
    require(document.count(start_marker) == 1 and document.count(end_marker) == 1, f"{source.as_posix()} controlled markers missing or duplicated")
    start = document.index(start_marker) + len(start_marker)
    end = document.index(end_marker, start)
    region = normalize_text(document[start:end])
    lines = region.splitlines()
    require(len(lines) >= 3 and lines[0].strip() == "```text" and lines[-1].strip() == "```", f"{source.as_posix()} controlled region must use one text fence")
    return normalize_text("\n".join(lines[1:-1]))


def schema_error_message(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path) or "<root>"
    return f"bootstrap schema violation at {path}: {error.message}"


def validate_schema(manifest: dict[str, Any], schema: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(manifest), key=lambda item: list(item.absolute_path))
    require(not errors, schema_error_message(errors[0]) if errors else "schema failure")


def route_by_id(manifest: dict[str, Any], route_id: str) -> dict[str, Any]:
    routes = manifest.get("routing_cases")
    require(isinstance(routes, list), "routing_cases must be an array")
    matches = [item for item in routes if isinstance(item, dict) and item.get("case_id") == route_id]
    require(len(matches) == 1, f"routing case identity missing: {route_id}")
    return matches[0]


def validate_manifest_semantics(manifest: dict[str, Any]) -> None:
    require(manifest.get("contract_id") == "ev4-ce-conversation-bootstrap", "wrong contract_id")
    require(manifest.get("contract_version") == "1.0.0", "wrong contract_version")
    require(manifest.get("owner_repository") == "rezahh107/EV4-Constructability-Engineer-Repo", "wrong owner_repository")
    require(manifest.get("activation_mode") == "integrated_authorized_ce_startup", "wrong activation_mode")

    trigger = manifest.get("trigger_policy")
    require(isinstance(trigger, dict), "trigger_policy must be an object")
    require(trigger.get("canonical_trigger") == "شروع", "missing canonical trigger")
    require(trigger.get("trigger_type") == "exact_message_after_normalization", "wrong trigger type")
    require(trigger.get("normalization_policy") == {
        "policy_id": "ce-bootstrap-normalization-policy-v1",
        "unicode_normalization": "NFC",
        "trim_surrounding_whitespace": True,
        "case_folding": False,
        "aliases": [],
    }, "wrong normalization policy")
    require(trigger.get("attachment_without_authorized_context") == "forbidden", "attachment authorization boundary weakened")
    require(trigger.get("repository_maintenance_precedence") == "always", "maintenance precedence weakened")
    require(manifest.get("bootstrap_response") == BOOTSTRAP_RESPONSE, "wrong exact response text")

    canonical = manifest.get("canonical_input")
    require(isinstance(canonical, dict), "canonical_input must be an object")
    require(canonical.get("schema_id") == CANONICAL_SCHEMA_ID, "wrong canonical input schema")
    require(canonical.get("source_transition") == SOURCE_TRANSITION_ID, "wrong source transition")
    require(canonical.get("filename_is_authority") is False, "filename-only acceptance enabled")
    require(canonical.get("source_binding_required") is True, "source binding requirement removed")
    require(canonical.get("source_bundle_bytes_verified_at_bootstrap") is True, "source bundle bytes are not verified at bootstrap")

    receipt = manifest.get("receipt")
    require(isinstance(receipt, dict), "receipt must be an object")
    require(receipt.get("semantic_input") is False, "receipt promoted to semantic input")
    require(receipt.get("validation_status_without_official_validator") == "unverified", "receipt validation overstated")
    require(receipt.get("role_without_official_validator") == "diagnostic_untrusted", "receipt role overstated")
    require(receipt.get("invalid_with_valid_input_policy") == "block_conflicting_evidence", "invalid Receipt precedence ambiguous")
    require(receipt.get("reconstruction_source_forbidden") is True, "receipt reconstruction route is not forbidden")

    precedence = manifest.get("input_precedence")
    require(isinstance(precedence, dict), "input_precedence must be an object")
    require(precedence.get("inspect_attachments_after_authorization") is True, "attachments can bypass authorization")
    require(precedence.get("automatic_selection") is False, "ambiguous auto-selection enabled")
    require(precedence.get("valid_plus_any_conflict") == "blocked_conflicting_evidence", "mixed-attachment conflict policy weakened")
    require(precedence.get("multiple_receipt_like_objects") == "blocked_conflicting_evidence", "multiple Receipt precedence weakened")

    routes = manifest.get("routing_cases")
    require(isinstance(routes, list), "routing_cases must be an array")
    observed_ids = [item.get("case_id") for item in routes if isinstance(item, dict)]
    require(observed_ids == list(EXPECTED_ROUTING_CASES), "routing case set or order drifted")
    for case_id, expected in EXPECTED_ROUTING_CASES.items():
        observed = route_by_id(manifest, case_id)
        for field in DECISION_FIELDS:
            require(field in observed, f"routing case {case_id} omits decision field {field}")
            require(observed[field] == expected[field], f"wrong {case_id}.{field}")

    first = manifest.get("first_stage_routing")
    require(isinstance(first, dict), "first_stage_routing must be an object")
    require(first == {
        "policy_id": "ce-bootstrap-first-stage-routing-v1",
        "stage_id": "architect_intake_validation",
        "pipeline_manifest_path": "manifests/ce_pipeline_manifest.v1.json",
        "ordinal": 1,
        "mandatory": True,
        "required_input": CANONICAL_SCHEMA_ID,
        "authorization_prerequisites": ["activation_authorized", "intake_valid", "source_binding_valid"],
    }, "wrong first stage routing contract")

    compatibility = manifest.get("compatibility")
    require(isinstance(compatibility, dict), "compatibility must be an object")
    require(compatibility.get("canonical_input_schema") == CANONICAL_SCHEMA_ID, "legacy schema silently made canonical")
    require(compatibility.get("silent_promotion_forbidden") is True, "legacy silent promotion enabled")

    maintenance = manifest.get("repository_maintenance_exception")
    require(isinstance(maintenance, dict), "repository_maintenance_exception must be an object")
    require(maintenance.get("route") == "repository_maintenance", "repository-maintenance route removed")
    require(maintenance.get("pipeline_execution") == "not_a_ce_project_run", "maintenance CE execution enabled")
    require(maintenance.get("canonical_trigger_not_authorization") is True, "maintenance trigger became authorization")

    operations = manifest.get("forbidden_pre_validation_operations")
    require(isinstance(operations, list), "forbidden operations must be an array")
    require([item.get("operation") for item in operations if isinstance(item, dict)] == list(EXPECTED_FORBIDDEN_OPERATIONS), "forbidden operation set or order drifted")
    require([item.get("operation_id") for item in operations if isinstance(item, dict)] == [f"CE-BOOT-PRE-{index:03d}" for index in range(1, 13)], "forbidden operation stable IDs drifted")
    require(manifest.get("controlled_routing_text") == ROUTING_TEXT, "controlled routing text drifted")
    require(manifest.get("controlled_quick_start_text") == QUICK_START_TEXT, "controlled Quick Start text drifted")


def validate_pipeline(manifest: dict[str, Any], pipeline: dict[str, Any]) -> None:
    stages = pipeline.get("project_execution_stages")
    require(isinstance(stages, list) and stages, "pipeline manifest has no stages")
    first = stages[0]
    expected = manifest["first_stage_routing"]
    require(isinstance(first, dict), "pipeline first stage is not an object")
    require(first.get("stage_id") == expected["stage_id"], "pipeline first stage drifted")
    require(first.get("ordinal") == 1, "pipeline first-stage ordinal drifted")
    require(first.get("mandatory") is True, "pipeline first stage is not mandatory")
    require(first.get("required_inputs") == [CANONICAL_SCHEMA_ID], "pipeline first-stage input drifted")


def validate_documents(manifest: dict[str, Any], agents: str, readme: str, project_instructions: str, first_run: str) -> None:
    response = normalize_text(manifest["bootstrap_response"])
    routing = normalize_text(manifest["controlled_routing_text"])
    quick = normalize_text(manifest["controlled_quick_start_text"])
    for source, document in ((AGENTS_REL, agents), (PROJECT_INSTRUCTIONS_REL, project_instructions), (FIRST_RUN_REL, first_run)):
        require(extract_marked_fenced_text(document, RESPONSE_START, RESPONSE_END, source) == response, f"{source.as_posix()} exact response drifted")
    for source, document in ((AGENTS_REL, agents), (PROJECT_INSTRUCTIONS_REL, project_instructions)):
        require(extract_marked_fenced_text(document, ROUTING_START, ROUTING_END, source) == routing, f"{source.as_posix()} controlled routing drifted")
    for source, document in ((README_REL, readme), (FIRST_RUN_REL, first_run)):
        require(extract_marked_fenced_text(document, QUICK_START_START, QUICK_START_END, source) == quick, f"{source.as_posix()} Quick Start drifted")
    for source, document in ((AGENTS_REL, agents), (README_REL, readme), (PROJECT_INSTRUCTIONS_REL, project_instructions), (FIRST_RUN_REL, first_run)):
        require(BOOTSTRAP_REL.as_posix() in document, f"{source.as_posix()} omits canonical manifest reference")
    for token in (
        "source_bundle_bytes_verified_at_bootstrap",
        "diagnostic_untrusted",
        "blocked_conflicting_evidence",
        "active_ce_run",
        "repository_maintenance",
    ):
        require(token in project_instructions, f"Project Instructions omit {token}")
    require("Never extract nested `result.output`" in readme and "Extract nested `result.output`" not in readme, "README tells operator to use the wrong artifact path")
    for operation in EXPECTED_FORBIDDEN_OPERATIONS:
        require(f"`{operation}`" in project_instructions, f"Project Instructions omit forbidden operation {operation}")
        require(f"`{operation}`" in agents, f"AGENTS.md omits forbidden operation {operation}")


def validate_status(status: str) -> None:
    required = (
        "CE_CONVERSATION_BOOTSTRAP_V1:",
        "implementation_state: repaired_in_pr_pending_exact_head_ci_and_independent_review",
        "contract: ev4-ce-conversation-bootstrap@1.0.0",
        "canonical_trigger: شروع",
        f"canonical_input: {CANONICAL_SCHEMA_ID}",
        "source_bundle_bytes_verified_at_bootstrap: true",
        "integrated_routing_authorization: implemented",
        "receipt_validation_status: unverified",
        "receipt_role: diagnostic_untrusted",
        "mixed_attachment_precedence: fail_closed_conflict_blocking",
        "coordinated_manifest_schema_drift_detection: semantic_invariant_matrix",
        "external_model_host_loading: unverified",
        "real_non_synthetic_ce_run: insufficient_evidence",
        "production_readiness_claim: not_made",
    )
    for item in required:
        require(item in status, f"STATUS.md missing bootstrap truth: {item}")
    require("project_status:" in status and "  production_ready: false" in status, "STATUS.md must preserve production_ready false")
    require("CE_02_POST_MERGE_EXPORTER_AUDIT:" in status and "CE_02_POST_MERGE_STATUS_RECONCILIATION:" in status, "STATUS.md historical PR #37/#38 evidence was not preserved")


def validate_repository(root: Path) -> dict[str, Any]:
    root = root.resolve()
    manifest = load_json(root, BOOTSTRAP_REL)
    schema = load_json(root, SCHEMA_REL)
    pipeline = load_json(root, PIPELINE_REL)
    require((root / INTAKE_SCHEMA_REL).is_file(), "official CE intake schema is missing")
    require((root / INTAKE_VALIDATOR_REL).is_file(), "official CE intake validator is missing")
    validate_manifest_semantics(manifest)
    validate_schema(manifest, schema)
    validate_pipeline(manifest, pipeline)
    validate_documents(manifest, read_text(root, AGENTS_REL), read_text(root, README_REL), read_text(root, PROJECT_INSTRUCTIONS_REL), read_text(root, FIRST_RUN_REL))
    validate_status(read_text(root, STATUS_REL))
    return {
        "contract": "ev4-ce-conversation-bootstrap@1.0.0",
        "trigger": "شروع",
        "routing_cases": len(manifest["routing_cases"]),
        "forbidden_operations": len(manifest["forbidden_pre_validation_operations"]),
        "first_stage": manifest["first_stage_routing"]["stage_id"],
        "source_binding": "required_and_verified_from_supplied_bytes",
        "receipt_validation": "unverified_diagnostic_untrusted",
    }
