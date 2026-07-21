#!/usr/bin/env python3
"""Fail-closed validation and integrated request routing for CE bootstrap v1."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import unicodedata
from dataclasses import dataclass
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
PROJECT_INSTRUCTIONS_REL = Path("release/EV4_CE_PROJECT_RELEASE_PACK_v1/PROJECT_INSTRUCTIONS.md")
FIRST_RUN_REL = Path("release/EV4_CE_PROJECT_RELEASE_PACK_v1/EV4_FIRST_RUN_GUIDE.md")

RESPONSE_START = "<!-- EV4_CE_BOOTSTRAP_RESPONSE_START -->"
RESPONSE_END = "<!-- EV4_CE_BOOTSTRAP_RESPONSE_END -->"
ROUTING_START = "<!-- EV4_CE_BOOTSTRAP_ROUTING_START -->"
ROUTING_END = "<!-- EV4_CE_BOOTSTRAP_ROUTING_END -->"
QUICK_START_START = "<!-- EV4_CE_BOOTSTRAP_QUICK_START_START -->"
QUICK_START_END = "<!-- EV4_CE_BOOTSTRAP_QUICK_START_END -->"

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

برای شروع بررسی Constructability، فایل `ce-input.json` و source bundle دقیق آن را که توسط مسیر `EV4-Project-Gate / architect-to-ce` استفاده شده است ارسال کن.

ورودی باید با قرارداد `ev4-ce-architect-stage-intake@1.1.0` معتبر باشد و binding آن با bytes واقعی source bundle تأیید شود.
فایل `project-gate-a2c-receipt.json` تا اعتبارسنجی رسمی فقط evidence تشخیصیِ غیرقابل‌اعتماد است و جایگزین ورودی CE نیست.

پس از اعتبارسنجی ورودی و source binding، بررسی فقط از مرحله `architect_intake_validation` آغاز می‌شود.
تا پیش از آن، هیچ نتیجه Constructability، استراتژی اجرا یا آمادگی Builder اعلام نمی‌شود."""

ROUTING_TEXT = """trigger_policy:
- Normalize the user message with Unicode NFC and trim surrounding whitespace.
- Only the exact normalized message `شروع` authorizes a new CE bootstrap context.
- A later attachment is authorized only when `active_ce_run: true` is already established.
- Repository-maintenance intent always routes to `repository_maintenance`; the word `شروع` is not authorization there.
- A non-trigger message with no authorized active CE run cannot create a CE run, even when a valid attachment is present.

attachment_first:
- Inspect every supplied attachment only after startup authorization is established.
- Determine artifact identity from parsed content, never from filename alone.
- Exactly one valid `ev4-ce-architect-stage-intake@1.1.0` plus exactly one matching source bundle is required for `architect_intake_validation`.
- Source binding verifies bundle ID, canonical SHA-256, transition identity, Project Gate producer identity, and upstream producer provenance.
- Missing or mismatched source bundle bytes block CE execution.
- Any valid CE input mixed with invalid, insufficient-evidence, legacy, wrong-stage, Receipt-like, or additional source candidates blocks as conflicting evidence.
- Multiple valid CE inputs block as ambiguous; automatic selection is forbidden.

receipt_policy:
- Receipt-like objects are never classified as validated audit evidence from `schema_version` alone.
- Until official external Receipt validation succeeds, use `receipt_validation_status: unverified` and `receipt_role: diagnostic_untrusted`.
- Receipt-only input waits for CE input and never becomes semantic input.
- A Receipt-like or malformed Receipt accompanying a valid CE input blocks as conflicting evidence.

repository_maintenance:
- Explicit repository inspection, audit, code, documentation, test, CI, PR, status, or governance work uses repository-maintenance mode and forbids CE pipeline execution.

pre_validation:
- Before integrated authorization, official intake validation, and source binding all succeed, no Constructability review, hidden-dependency inference, implementation-strategy selection, Builder package or readiness claim, CE Project Gate export, or downstream readiness claim is allowed."""

QUICK_START_TEXT = """1. Create or open the CE ChatGPT Project and load `release/EV4_CE_PROJECT_RELEASE_PACK_v1/PROJECT_INSTRUCTIONS.md` as the Project Instructions.
2. Send the exact normalized message `شروع`.
3. Upload the standalone `ce-input.json` produced by `EV4-Project-Gate / architect-to-ce`.
4. Upload the exact Architect source bundle whose canonical SHA-256 is declared by that CE input.
5. Treat any Receipt-like attachment as `diagnostic_untrusted` until official external Receipt validation succeeds.
6. Never extract nested `result.output`, rebuild CE input manually, or continue on mixed/conflicting attachments.
7. Only successful integrated authorization + intake validation + source binding may route to `architect_intake_validation`."""


def _case(
    case_id: str,
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
    trigger_not_authorization: bool = False,
    ask_only_for_blocking_evidence: bool = False,
    explicit_compatibility_authorization_required: bool = False,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
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
        _case("CE-BOOT-ROUTE-BARE-START", "no_attachments", "absent", "waiting_for_ce_input", "forbidden", diagnostic_code="CE_BOOTSTRAP_INPUT_REQUIRED"),
        _case("CE-BOOT-ROUTE-UNAUTHORIZED", "attachment_or_message_without_authorized_context", "any", "no_bootstrap_authorization", "forbidden", diagnostic_code="CE_BOOTSTRAP_AUTHORIZATION_REQUIRED", trigger_not_authorization=True),
        _case("CE-BOOT-ROUTE-VALID-BOUND-INPUT", "one_valid_canonical_ce_input_and_one_matching_source_bundle", "absent", "architect_intake_validation", "first_stage_only", semantic_input_source="ce_input_only"),
        _case("CE-BOOT-ROUTE-SOURCE-BINDING-MISSING", "valid_canonical_ce_input_without_source_bundle", "absent", "blocked_source_binding_required", "forbidden", diagnostic_code="CE_BOOTSTRAP_SOURCE_BUNDLE_REQUIRED"),
        _case("CE-BOOT-ROUTE-SOURCE-BINDING-INVALID", "valid_canonical_ce_input_with_mismatched_source_bundle", "absent", "blocked_source_binding_invalid", "forbidden", diagnostic_code="CE_BOOTSTRAP_SOURCE_BINDING_INVALID"),
        _case("CE-BOOT-ROUTE-RECEIPT-ONLY", "no_usable_ce_input", "unverified", "waiting_for_ce_input", "forbidden", receipt_role="diagnostic_untrusted", diagnostic_code="CE_BOOTSTRAP_RECEIPT_UNVERIFIED"),
        _case("CE-BOOT-ROUTE-INVALID-INPUT", "invalid_or_wrong_schema_input", "any", "blocked_invalid_input", "forbidden", diagnostic_code="CE_BOOTSTRAP_INVALID_INPUT"),
        _case("CE-BOOT-ROUTE-INSUFFICIENT-EVIDENCE", "canonical_ce_input_insufficient_evidence", "any", "blocked_invalid_input", "forbidden", diagnostic_code="CE_BOOTSTRAP_INTAKE_INSUFFICIENT_EVIDENCE", ask_only_for_blocking_evidence=True),
        _case("CE-BOOT-ROUTE-AMBIGUOUS-INPUT", "multiple_valid_canonical_ce_inputs", "any", "blocked_ambiguous_input", "forbidden", diagnostic_code="CE_BOOTSTRAP_AMBIGUOUS_INPUT"),
        _case("CE-BOOT-ROUTE-LEGACY-INPUT", "legacy_compatibility_input", "any", "blocked_require_canonical_v1_1", "forbidden", diagnostic_code="CE_BOOTSTRAP_LEGACY_INPUT_NOT_CANONICAL", explicit_compatibility_authorization_required=True),
        _case("CE-BOOT-ROUTE-WRONG-ARTIFACT", "raw_architect_or_transition_envelope", "any", "blocked_require_official_project_gate_output", "forbidden", diagnostic_code="CE_BOOTSTRAP_OFFICIAL_CE_INPUT_REQUIRED"),
        _case("CE-BOOT-ROUTE-CONFLICTING-ATTACHMENTS", "valid_candidate_mixed_with_conflicting_candidate", "present_or_invalid", "blocked_conflicting_evidence", "forbidden", receipt_role="diagnostic_untrusted", diagnostic_code="CE_BOOTSTRAP_CONFLICTING_ATTACHMENTS"),
        _case("CE-BOOT-ROUTE-REPOSITORY-MAINTENANCE", "explicit_repository_maintenance_request", "not_applicable", "repository_maintenance", "not_a_ce_project_run", receipt_role="not_applicable", trigger_not_authorization=True),
    )
}

