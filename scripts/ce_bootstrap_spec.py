#!/usr/bin/env python3
"""Lean, correctness-first CE runtime intake contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

BOOTSTRAP_REL = Path("manifests/ce-conversation-bootstrap.v1.json")
SCHEMA_REL = Path("schemas/ce-conversation-bootstrap.v1.schema.json")
PIPELINE_REL = Path("manifests/ce_pipeline_manifest.v1.json")
INTAKE_SCHEMA_REL = Path("schemas/ce_architect_stage_intake.v1_1.schema.json")
INTAKE_VALIDATOR_REL = Path("scripts/validate-ce-architect-stage-intake.py")
AGENTS_REL = Path("AGENTS.md")
README_REL = Path("README.md")
STATUS_REL = Path("STATUS.md")
PROJECT_INSTRUCTIONS_REL = Path("release/EV4_CE_PROJECT_RELEASE_PACK_v1/PROJECT_INSTRUCTIONS.md")
FIRST_RUN_REL = Path("release/EV4_CE_PROJECT_RELEASE_PACK_v1/EV4_FIRST_RUN_GUIDE.md")

CANONICAL_SCHEMA_ID = "ev4-ce-architect-stage-intake@1.1.0"
RECEIPT_SCHEMA_ID = "project-gate-a2c-receipt.v1"
SOURCE_TRANSITION_ID = "ev4-architect-to-ce-transition@1.0.0"
SOURCE_TRANSITION_VERSION = "1.0.0"
PROJECT_GATE_PRODUCER = "rezahh107/EV4-Project-Gate"

LEGACY_SCHEMA_IDS = {
    "ev4-ce-architect-stage-intake@1.0.0",
    "architect_ce_input_package.v1",
}
WRONG_STAGE_SCHEMA_IDS = {
    "ev4-architect-stage-payload@1.0.0",
    "producer-gate-export.v1",
    "stage-evidence-bundle.v1",
}
OPERATING_MODES = {
    "auto",
    "user_facing_new_ce_run",
    "active_ce_run",
    "repository_maintenance",
}
MAINTENANCE_TERMS = (
    "repository", "repo", "pull request", "pr #", "issue", "commit", "branch",
    "workflow", "github", "ci", "code", "schema", "test", "documentation",
    "ریپو", "مخزن", "پول ریکوئست", "گیت‌هاب", "کامیت", "برنچ", "ورک‌فلو",
    "کد", "تست", "مستندات", "اصلاح فایل", "بررسی ریپو",
)

RUNTIME_STATES = (
    "INTAKE_VALIDATING",
    "REVIEW_ACTIVE",
    "EVIDENCE_REQUIRED",
    "STRATEGY_READY",
    "EXPORT_VALIDATING",
    "COMPLETED",
)

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

DECISION_FIELDS = (
    "case_id",
    "runtime_state",
    "input_state",
    "receipt_state",
    "route",
    "pipeline_execution",
    "automatic_selection",
    "semantic_input_source",
    "receipt_required",
    "receipt_role",
    "diagnostic_code",
    "manual_extraction_allowed",
    "trigger_not_authorization",
    "ask_only_for_blocking_evidence",
    "explicit_compatibility_authorization_required",
)

BOOTSTRAP_RESPONSE = """EV4 Constructability Engineer آماده است.

فایل CE input معتبر با قرارداد `ev4-ce-architect-stage-intake@1.1.0` را ارسال کن.
عبارت `شروع` فقط یک میان‌بر گفتگو است و مجوز امنیتی محسوب نمی‌شود.
source bundle و Receipt فقط زمانی درخواست می‌شوند که برای رفع ابهام یا اثبات یک تصمیم لازم باشند.
تا پیش از اعتبارسنجی schema و semantic، هیچ نتیجه Constructability یا Builder-ready اعلام نمی‌شود."""

ROUTING_TEXT = """runtime_mode:
- Repository-maintenance intent always routes to `repository_maintenance`.
- Outside maintenance mode, a supplied CE input is inspected directly; exact phrases and `active_ce_run` are not authorization gates.
- Artifact identity is derived from parsed content, never from filename alone.

input_policy:
- Exactly one schema-valid and semantically valid `ev4-ce-architect-stage-intake@1.1.0` may enter `architect_intake_validation`.
- Multiple valid CE inputs block automatic selection.
- Invalid, legacy, Receipt-like, wrong-stage, malformed, or unrelated extra files do not block an otherwise valid CE input; they are reported as warnings.
- Invalid or insufficient CE input remains fail-closed.

evidence_policy:
- A source bundle is optional for a complete valid CE input.
- When a source bundle is supplied and relied upon, exact bytes, identity, hash, transition, and provenance are verified.
- Missing evidence routes to `EVIDENCE_REQUIRED` only when official semantic diagnostics show that correctness cannot be established.
- Receipt-like objects remain non-semantic diagnostic material.

correctness_policy:
- Candidate identity, architecture intent, unknowns, blocking dependencies, implementation strategy, Builder eligibility, schema validity, deterministic export, atomic writes, and publication guards remain enforced.
- Repository PR state, independent review, receipts, exact-head artifacts, and governance bundles are not CE runtime prerequisites."""

QUICK_START_TEXT = """1. Load `release/EV4_CE_PROJECT_RELEASE_PACK_v1/PROJECT_INSTRUCTIONS.md`.
2. Send the valid `ce-input.json`; sending `شروع` first is optional.
3. Add a source bundle only when CE reports a concrete evidence requirement.
4. Extra unrelated files are warnings, not runtime blockers.
5. CE blocks only invalid/insufficient CE input, multiple valid CE inputs, or relevant evidence that contradicts the selected input.
6. Builder-ready remains impossible while dependencies, strategy decisions, required fields, or validation errors remain."""

def _case(
    case_id: str,
    runtime_state: str,
    input_state: str,
    receipt_state: str,
    route: str,
    pipeline_execution: str,
    *,
    semantic_input_source: str = "none",
    receipt_required: bool = False,
    receipt_role: str = "absent",
    diagnostic_code: str | None = None,
    manual_extraction_allowed: bool = False,
    trigger_not_authorization: bool = True,
    ask_only_for_blocking_evidence: bool = False,
    explicit_compatibility_authorization_required: bool = False,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "runtime_state": runtime_state,
        "input_state": input_state,
        "receipt_state": receipt_state,
        "route": route,
        "pipeline_execution": pipeline_execution,
        "automatic_selection": False,
        "semantic_input_source": semantic_input_source,
        "receipt_required": receipt_required,
        "receipt_role": receipt_role,
        "diagnostic_code": diagnostic_code,
        "manual_extraction_allowed": manual_extraction_allowed,
        "trigger_not_authorization": trigger_not_authorization,
        "ask_only_for_blocking_evidence": ask_only_for_blocking_evidence,
        "explicit_compatibility_authorization_required": explicit_compatibility_authorization_required,
    }

EXPECTED_ROUTING_CASES = {
    item["case_id"]: item
    for item in (
        _case(
            "CE-RUNTIME-WAITING-FOR-INPUT",
            "INTAKE_VALIDATING",
            "no_valid_ce_input",
            "absent_or_diagnostic",
            "waiting_for_ce_input",
            "not_started",
            diagnostic_code="CE_RUNTIME_INPUT_REQUIRED",
        ),
        _case(
            "CE-RUNTIME-VALID-INPUT",
            "REVIEW_ACTIVE",
            "one_valid_canonical_ce_input_without_required_source_evidence",
            "optional",
            "architect_intake_validation",
            "first_stage_only",
            semantic_input_source="ce_input_only",
        ),
        _case(
            "CE-RUNTIME-VALID-BOUND-INPUT",
            "REVIEW_ACTIVE",
            "one_valid_canonical_ce_input_with_verified_source_bundle",
            "optional",
            "architect_intake_validation",
            "first_stage_only",
            semantic_input_source="ce_input_only",
        ),
        _case(
            "CE-RUNTIME-EVIDENCE-REQUIRED",
            "EVIDENCE_REQUIRED",
            "canonical_ce_input_insufficient_evidence",
            "optional",
            "evidence_required",
            "paused",
            diagnostic_code="CE_RUNTIME_BLOCKING_EVIDENCE_REQUIRED",
            ask_only_for_blocking_evidence=True,
        ),
        _case(
            "CE-RUNTIME-SOURCE-EVIDENCE-CONFLICT",
            "EVIDENCE_REQUIRED",
            "valid_ce_input_with_contradictory_relevant_source_evidence",
            "optional",
            "blocked_source_binding_invalid",
            "forbidden",
            diagnostic_code="CE_RUNTIME_SOURCE_EVIDENCE_CONFLICT",
            ask_only_for_blocking_evidence=True,
        ),
        _case(
            "CE-RUNTIME-INVALID-INPUT",
            "INTAKE_VALIDATING",
            "invalid_canonical_ce_input",
            "any",
            "blocked_invalid_input",
            "forbidden",
            diagnostic_code="CE_RUNTIME_INVALID_INPUT",
        ),
        _case(
            "CE-RUNTIME-AMBIGUOUS-INPUT",
            "EVIDENCE_REQUIRED",
            "multiple_valid_canonical_ce_inputs",
            "any",
            "blocked_ambiguous_input",
            "forbidden",
            diagnostic_code="CE_RUNTIME_AMBIGUOUS_INPUT",
        ),
        _case(
            "CE-RUNTIME-LEGACY-INPUT",
            "INTAKE_VALIDATING",
            "legacy_compatibility_input_without_valid_canonical_input",
            "any",
            "blocked_require_canonical_v1_1",
            "forbidden",
            diagnostic_code="CE_RUNTIME_LEGACY_INPUT_NOT_CANONICAL",
            explicit_compatibility_authorization_required=True,
        ),
        _case(
            "CE-RUNTIME-WRONG-ARTIFACT",
            "INTAKE_VALIDATING",
            "wrong_stage_artifact_without_valid_canonical_input",
            "any",
            "blocked_require_official_ce_input",
            "forbidden",
            diagnostic_code="CE_RUNTIME_OFFICIAL_CE_INPUT_REQUIRED",
        ),
        _case(
            "CE-RUNTIME-REPOSITORY-MAINTENANCE",
            "NOT_APPLICABLE",
            "explicit_repository_maintenance_request",
            "not_applicable",
            "repository_maintenance",
            "not_a_ce_project_run",
            receipt_role="not_applicable",
        ),
    )
}
