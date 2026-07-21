# AGENTS.md

## Scope

These instructions apply to the entire repository unless a closer nested `AGENTS.md` or `AGENTS.override.md` provides more specific guidance.

## Repository Role

`EV4-Constructability-Engineer-Repo` is the implementation-strategy gate between Architect and Builder.

It receives an approved architecture handoff, identifies hidden execution dependencies, proves or blocks implementation strategy, preserves locked architecture identity, and emits a Builder-ready package only when Builder has no remaining strategy decision.

For Project Gate-produced Architect-to-CE transitions, its canonical Architect-facing intake is `ev4-ce-architect-stage-intake@1.1.0`.

## Read First

1. `README.md`
2. `STATUS.md`, when present
3. `contracts/CE_ARCHITECT_STAGE_INTAKE_V1_1.md`
4. `contracts/ARCHITECT_STAGE_TO_CE_INTAKE_MAPPING_V1_1.md`
5. `schemas/ce_architect_stage_intake.v1_1.schema.json`
6. `contracts/CE_ARCHITECT_STAGE_INTAKE_V1.md`
7. `contracts/ARCHITECT_STAGE_TO_CE_INTAKE_MAPPING_V1.md`
8. `scripts/validate-ce-architect-stage-intake.py`
9. `docs/PROTOCOL.md`
10. `docs/ROLE_BOUNDARIES.md`
11. the relevant schema, validator, rule, fixture, and test files

Follow the current owning contract and validated fixtures over proposals or historical notes.

## Manual Advisory Policy Attachment

`policies/EV4_CE_CONSTRUCTABILITY_DECISION_POLICY_r001.md` is not part of the canonical `Read First` sequence and is not automatically loaded. An operator may attach it manually as advisory reference only.

When attached:

- current contracts, schemas, validators, fixtures, accepted Architect identity, and machine-readable Kernel lineage remain higher authority;
- the policy must not create or replace a Kernel-governed decision;
- a governed option requires complete lineage fields and must match upstream `selected_option`;
- external EV4 Domain artifacts remain untrusted advisory evidence unless an active repository contract validates their exact provenance and compatibility;
- prose-only guidance must not be reported as schema, validator, CI, runtime, or downstream enforcement.

Focused policy-governance validation:

```bash
python scripts/validate-ce-policy-governance.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_policy_governance.py
```

## Project Gate Position

```text
Architect package
→ Project Gate transition
→ CE Architect Stage Intake
→ CE review and output
→ EV4 Project Gate
→ accepted: Builder Input Package
→ not accepted: CE repair or evidenced upstream amendment
```

Project Gate may execute this repository's official validators and the documented downstream adapter. It must not invent implementation strategy or replace CE contracts.

For the Architect → CE boundary, Project Gate must not create CE-owned conclusions. The CE intake package may preserve Architect evidence, deterministic projections, transition provenance, and unresolved evidence only.

## Canonical Architect Intake

Canonical Project Gate-produced intake:

```text
ev4-ce-architect-stage-intake@1.1.0
```

Accepted source:

```text
ev4-architect-stage-payload@1.0.0
```

Mapping contract:

```text
ev4-architect-stage-to-ce-intake-mapping@1.1.0
```

Historical compatibility-only Architect Stage intake:

```text
ev4-ce-architect-stage-intake@1.0.0
ev4-architect-stage-to-ce-intake-mapping@1.0.0
```

Legacy compatibility-only files:

```text
contracts/ARCHITECT_TO_CE_INPUT_MAPPING_V1.md
schemas/architect_ce_input_package.v1.schema.json
```

Do not reinterpret `ev4-ce-architect-stage-intake@1.0.0`; its `project_gate_transition_implemented: false` meaning is frozen.

## Hard Boundaries

Do not:

- redesign or rescore the approved architecture;
- change `selected_candidate_id` or approved class intent;
- act as Builder;
- emit Builder instructions while Builder decisions remain;
- treat transition execution as CE review execution;
- treat transition execution as Builder authorization;
- treat silence as proof of geometry, asset, overlay, interaction, responsive, Dynamic Loop, accessibility, or UI-control readiness;
- claim production readiness;
- claim real Elementor validation without real evidence;
- copy CE schemas into Project Gate as competing canonical contracts;
- require Project Gate to invent `ce_review_units[].action_proposed`, proof-state conclusions, identity consistency verdicts, pre-ingestion verdicts, implementation strategy, or Builder authorization at intake.

Default behavior is fail-closed:

```text
not proven executable → not builder-ready
```

## Change Rules

For changes affecting Builder intake:

- preserve public contract behavior unless a breaking change is explicitly approved;
- update schemas, validators, rules, fixtures, tests, and docs together;
- preserve locked architecture identity and valid evidence;
- add malformed, boundary, and regression cases for changed behavior;
- document compatibility and versioning impact;
- avoid unrelated refactoring;
- do not weaken a confirmed regression fixture without an explicit decision record.

## Wave 5 Kernel Decision Receipts

Wave 5 is presentation-layer only. A human-readable receipt may explain CE handling of a Kernel decision only when the machine-readable decision lineage remains the source of truth.

Success receipt text:

```text
✅ تصمیم به decision card کرنل وصل است؛ CE فقط constructability آن را بررسی کرده و lineage تصمیم حفظ شده است.
```

Insufficient-evidence receipt text:

```text
⚠️ این آیتم هنوز رسید معتبر کرنل ندارد؛ CE نمی‌تواند بدون machine-readable trace کامل آن را قابل‌عبور اعلام کند.
```

A success receipt requires complete machine trace fields:

```text
decision_family
decision_card_ref
selected_option
rejected_options
evidence_refs
evidence_state
consumer_stage
```

Do not:

- emit a green-check receipt without complete `decision_lineage`;
- use receipt text as a replacement for machine-readable trace;
- claim CE constructability pass, Builder readiness, downstream enforcement, runtime enforcement, or production readiness from receipt text alone;
- invent `decision_card_ref`, `decision_family`, `evidence_refs`, `resolved`, or `production_ready`.

## Validation

Use the repository's current validation sequence:

```bash
python -m pip install -e '.[dev]'
pytest -q
python scripts/validate-behavioral-rule-coverage.py
python scripts/validate-role-alignment-fixtures.py
npm run test:reference-paradigm-lock
```

For Architect Stage Intake changes, also run:

```bash
python scripts/validate-ce-architect-stage-intake.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_architect_stage_intake.py
```

For Kernel decision receipt changes, also run:

```bash
python scripts/validate-ce-kernel-decision-receipts.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_kernel_decision_receipts.py
```

Run the checks relevant to the change and report exactly which commands passed. Do not claim full validation if only a subset ran.

## Evidence and Determinism

Use explicit evidence states and retain source paths, fixture IDs, validator outputs, and rule IDs.

Synthetic fixtures must be labelled synthetic. A shape check is not equivalent to passing the official schema and behavioral validator.

When repair ownership cannot be established, use:

```yaml
status: insufficient_evidence
repair_owner: unresolved
```

## Decision Escape Route Review

Before opening or completing any PR that changes schemas, validators, prompts, fixtures, pipeline docs, handoff artifacts, fallback behavior, or decision-bearing outputs, review `planning/DECISION_ESCAPE_ROUTES.yml`. Do not mark an escape route as resolved unless its `enforcement_status` meets the required threshold for its risk and `session_scope`; do not mark a Critical cross-turn rule as resolved with single-artifact `ci_enforced`. Do not add authored `resolved` or `production_ready` fields; those are derived audit conclusions.

## Pull Requests

A PR should state:

- the constructability problem or contract change;
- affected schemas, rules, fixtures, and downstream handoffs;
- compatibility impact;
- validation commands actually executed;
- remaining unverified behavior or missing evidence.

---

## CE Conversation Bootstrap v1

Canonical machine-readable startup contract:

```text
manifests/ce-conversation-bootstrap.v1.json
```

This section governs user-facing CE startup authorization. It does not replace repository-maintenance instructions.

### Exact bare-start response

When the normalized message is exactly `شروع`, no authorized CE run is active, and the request is not repository maintenance, return exactly:

<!-- EV4_CE_BOOTSTRAP_RESPONSE_START -->
```text
EV4 Constructability Engineer آماده است.

برای شروع بررسی Constructability، فایل `ce-input.json` و source bundle دقیق آن را که توسط مسیر `EV4-Project-Gate / architect-to-ce` استفاده شده است ارسال کن.

ورودی باید با قرارداد `ev4-ce-architect-stage-intake@1.1.0` معتبر باشد و binding آن با bytes واقعی source bundle تأیید شود.
فایل `project-gate-a2c-receipt.json` تا اعتبارسنجی رسمی فقط evidence تشخیصیِ غیرقابل‌اعتماد است و جایگزین ورودی CE نیست.

پس از اعتبارسنجی ورودی و source binding، بررسی فقط از مرحله `architect_intake_validation` آغاز می‌شود.
تا پیش از آن، هیچ نتیجه Constructability، استراتژی اجرا یا آمادگی Builder اعلام نمی‌شود.
```
<!-- EV4_CE_BOOTSTRAP_RESPONSE_END -->

### Controlled routing

<!-- EV4_CE_BOOTSTRAP_ROUTING_START -->
```text
trigger_policy:
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
- Before integrated authorization, official intake validation, and source binding all succeed, no Constructability review, hidden-dependency inference, implementation-strategy selection, Builder package or readiness claim, CE Project Gate export, or downstream readiness claim is allowed.
```
<!-- EV4_CE_BOOTSTRAP_ROUTING_END -->

The executable request contract contains `message`, `operating_mode`, `active_ce_run`, and `attachments`. A valid attachment alone cannot create a CE run. Repository-maintenance intent has precedence over the token `شروع` and never enters the CE pipeline.

The canonical startup input is `ev4-ce-architect-stage-intake@1.1.0`. The filename `ce-input.json` is only an operator hint. Bootstrap must call the official `validate_source_bundle_binding()` path with the exact source bundle bytes before routing to `architect_intake_validation`.

Receipt-like files remain `receipt_validation_status: unverified` and `receipt_role: diagnostic_untrusted` until an official external Receipt validator succeeds. They never become semantic CE input. Any Receipt-like or malformed Receipt mixed with a valid CE input blocks as conflicting evidence.

Before successful integrated authorization, intake validation, and source binding, these operations remain forbidden:

- `run_constructability_review`
- `generate_ce_review_units`
- `infer_hidden_dependencies`
- `select_implementation_strategy`
- `emit_builder_executable_package`
- `claim_builder_readiness`
- `emit_ce_project_gate_export`
- `invent_missing_architecture_or_evidence`
- `treat_receipt_as_semantic_input`
- `claim_project_gate_acceptance`
- `claim_real_elementor_validation`
- `claim_responsive_or_production_readiness`

For bootstrap changes, run:

```bash
python scripts/check-ce-bootstrap.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_bootstrap_semantics.py
python scripts/validate-ce-architect-stage-intake.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_architect_stage_intake.py
python scripts/validate-behavioral-rule-coverage.py
python scripts/validate-role-alignment-fixtures.py
python scripts/validate-project-gate-producer-adoption.py
```

Repository inspection, audit, code, documentation, test, CI, PR, status, and governance work remains `repository_maintenance` and is not a CE project run.
