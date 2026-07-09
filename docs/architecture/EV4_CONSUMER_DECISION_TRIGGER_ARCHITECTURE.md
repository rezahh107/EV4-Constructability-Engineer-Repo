# EV4 Consumer Decision Trigger Architecture

**Document status:** proposed normative architecture
**Version:** 0.4.1
**Canonical language:** English
**Companion language:** Persian explanatory appendix may exist separately
**BRC alignment:** Behavioral Rule Coverage v0.4.1 domain profile
**Method name:** Consumer Decision Escape Route + Enforcement Proof Audit
**Primary operational artifact per consumer repo:** `planning/DECISION_ESCAPE_ROUTES.yml`
**Schema artifact per consumer repo:** `planning/decision-escape-routes.schema.json`
**State schema version:** 3

---

## 0. Adoption Status Note

This document may be present in a repository before full enforcement is implemented.

Presence of this document means the repository adopts the EV4 Consumer Decision Trigger Architecture as an upstream decision-gate contract. It does **not** prove that the repository has completed audit, schema enforcement, validator implementation, fixtures, CI, sequence enforcement, runtime monitoring, OS/harness enforcement, or downstream contract enforcement.

Repository-specific enforcement status must be read from `planning/DECISION_ESCAPE_ROUTES.yml` and verified by inspected schema, validator, fixture, CI, runtime, or downstream evidence.

Allowed claim from adding this document:

```yaml
claim_allowed: architecture_adopted
claim_forbidden:
  - enforcement_complete
  - escape_routes_audited
  - ci_enforced
  - downstream_contract_enforced
  - production_ready
```

---

## 1. Version 0.4.1 Hardening Summary

Version `0.4.1` is a minor hardening release over `0.4.0`.

```yaml
v0_4_1_hardening:
  - keep os_harness_enforced as a recognized BRC enforcement status
  - make resolved and production_ready derived claims, not authored fields
  - remove authored resolved and production_ready from DECISION_ESCAPE_ROUTES.yml records
  - add conditional schema rules for mapping_status
  - clarify that fixture_tested is not enough for Critical per_artifact rules
  - clarify that ci_enforced is not enough for Critical cross_turn rules
  - mark latest_frozen_cross_product_contract as active_if_exists
  - require insufficient_evidence when the cross-product contract is missing
  - add carrier-status consistency checks for ci_enforced, sequence_ci_enforced, runtime_monitor_enforced, os_harness_enforced, and downstream_contract_enforced
  - require non-empty required_decision_card_ref_pattern when mapping_status is mapped
```

Core rule:

```text
resolved and production_ready are not authored facts.
They are derived conclusions computed from risk, session_scope, enforcement_status,
carriers, downstream evidence, and inspected proof.
```

---

## 2. Purpose

This document defines how EV4 downstream consumer repositories must detect, record, close, and prove closure of Kernel-governed decision escape routes.

This document is not a guide for models to remember Kernel usage. It is a consumer-side enforcement contract proving that Kernel-governed decisions cannot pass silently without structured, testable, downstream-aware evidence.

```text
This document is not model memory.
It is the boundary lock for EV4 consumer repositories.
```

A decision escape route is any path where a model, prompt, schema, validator, handoff artifact, fixture, example, fallback rule, free-form field, implementation default, runtime path, or downstream intake path can carry a Kernel-governed decision without a valid reference to EV4-Decision-Kernel.

Required Kernel decision structure:

```yaml
required_kernel_decision_fields:
  - decision_family
  - decision_card_ref
  - selected_option
  - rejected_options
  - evidence_refs
  - evidence_state
```

A decision escape route is not closed by documentation, prompt instruction, patch claims, schema presence, fixture presence, advisory audit output, or model assertion. It is closed only when its required Behavioral Rule Coverage threshold is met and the conclusion is derived from inspected evidence.

---

## 3. Relationship to Behavioral Rule Coverage v0.4.1

This document is an EV4-specific implementation profile of Behavioral Rule Coverage v0.4.1.

```yaml
brc_alignment:
  behavioral_rule_coverage_version: "0.4.1"
  interpretation:
    decision_gate: domain_specific_behavioral_gate
    decision_escape_route: domain_specific_enforcement_free_or_under_enforced_gate
    decision_enforcement_carrier: domain_specific_enforcement_carrier
    enforcement_proof_record: domain_specific_coverage_record
  rule_status_source:
    use_brc_status_ladder: true
    do_not_invent_stronger_status: true
```

Relationship:

```text
Behavioral Rule Coverage v0.4.1
        ↓
meta-governance standard for LLM workflow enforcement
        ↓
EV4 Consumer Decision Trigger Architecture
        ↓
domain-specific enforcement architecture for Kernel-governed EV4 decisions
```

This document specializes BRC for EV4 decision gates. It must not replace the active Kernel taxonomy, decision cards, schemas, registries, or cross-product contracts.

---

## 4. Source of Truth and Source Precedence

```yaml
normative_source:
  path: docs/architecture/EV4_CONSUMER_DECISION_TRIGGER_ARCHITECTURE.md
  language: English
  role: canonical_engineering_specification

conflict_rule:
  english_normative_version_wins: true
```

Use this source precedence when auditing or implementing this architecture:

```yaml
source_precedence:
  - rank: 1
    source: latest_frozen_EV4_cross_product_contract
    status: active_if_exists
    if_missing: mark_cross_product_contract_as_insufficient_evidence
  - rank: 2
    source: active_Kernel_taxonomy_decision_cards_schemas_registries_architecture_specs
  - rank: 3
    source: validated_fixtures_and_deterministic_test_assertions
  - rank: 4
    source: CI_results_and_workflow_logs
  - rank: 5
    source: current_implementation
  - rank: 6
    source: downstream_consumer_intake_contracts
  - rank: 7
    source: runtime_traces_or_execution_logs
  - rank: 8
    source: prompt_protocol_prose
  - rank: 9
    source: proposals_chat_notes_or_model_claims
```

If the latest frozen EV4 cross-product contract does not exist or was not inspected, do not invent it. Record:

```yaml
cross_product_contract:
  evidence_state: insufficient_evidence
  fallback_source: active_Kernel_architecture_schema_registry_evidence
```

---

## 5. Evidence States

```yaml
evidence_states:
  - observed
  - exported
  - validated
  - resolved
  - derived
  - proposed
  - unverified
  - insufficient_evidence
  - not_applicable
```

Rules:

```yaml
evidence_rules:
  - never_convert_missing_evidence_into_a_guessed_value
  - never_turn_prompt_level_guidance_into_system_level_enforcement
  - never_claim_production_readiness_without_required_evidence
  - never_claim_CI_enforcement_without_inspected_CI_evidence
  - never_claim_downstream_enforcement_without_downstream_contract_evidence
  - never_claim_runtime_proof_without_runtime_trace_or_monitor_evidence
  - never_claim_real_E2E_from_synthetic_fixtures
```

---

## 6. EV4 Decision Gate

An EV4 Decision Gate is a domain-specific Behavioral Gate.

```yaml
EV4_Decision_Gate:
  definition: >
    A behavioral gate that determines whether an EV4 consumer repo may emit,
    accept, execute, validate, reopen, or pass downstream a Kernel-governed decision.
```

Examples:

```text
Architect may not emit a container_type decision without Kernel decision structure.
CE may not silently replace an Architect decision with a new design choice.
Builder may not invent architecture when a locked decision is missing.
Responsive may not convert runtime mismatch into redesign.
Project Gate may not accept a package with incomplete decision lineage.
```

---

## 7. Decision Escape Route

A Decision Escape Route exists when a Kernel-governed decision can be made, implied, accepted, repaired, resolved, defaulted, executed, or passed downstream without a valid Kernel decision record.

Examples:

```json
{ "layout_strategy": "Use flexbox because it is simpler." }
```

This carries a `container_type` decision without `decision_family`, `decision_card_ref`, `selected_option`, `rejected_options`, and `evidence_refs`.

```json
{ "asset_strategy": "Use SVG for this connector." }
```

This carries an `asset_representation` decision without Kernel enforcement.

```json
{ "css_strategy": "Use custom CSS for this layout detail." }
```

This carries an `implementation_method` decision without proving that native Elementor controls were insufficient.

---

## 8. Enforcement-Free Decision Gate

An Enforcement-Free Decision Gate, or EFDG, is an EV4 Decision Gate that exists only as prose, role instruction, examples, comments, prompt text, informal guidance, AGENTS.md instruction, or README instruction without a schema field, typed contract, validator rule, failing invalid fixture, passing valid fixture, CI check, sequence-aware test, downstream rejection, runtime monitor, or OS/harness policy.

A prompt instruction is not an enforcement carrier.

Example:

```text
AGENTS.md says Architect must consult Kernel before choosing Div/Flex/Grid,
but section-plan.schema.json allows layout_strategy as a free string.
```

This is an Enforcement-Free Decision Gate.

---

## 9. Decision Enforcement Carriers

Allowed EV4 carriers:

```yaml
decision_enforcement_carriers:
  - decision_record_schema
  - typed_contract
  - decision_card_ref_pattern
  - validator_rule
  - stable_rule_id
  - validator_diagnostic
  - positive_fixture
  - negative_fixture
  - test_command
  - CI_job
  - sequence_CI
  - runtime_monitor
  - os_harness_policy
  - downstream_consumer_rejection
  - project_gate_rejection
```

A Markdown requirement, example output, or advisory audit is not hard enforcement.

---

## 10. Kernel-Governed Decision Families

The active Kernel taxonomy is authoritative. Consumer repos must not invent undocumented decision families.

Typical Kernel-governed EV4 decision families include:

```yaml
example_decision_families:
  - container_type
  - asset_representation
  - positioning_mode
  - style_scope
  - implementation_method
  - value_source
  - unit_policy
  - responsive_strategy
  - semantic_element_choice
  - interaction_strategy
  - evidence_status
```

If a Kernel decision family is not applicable to a consumer repository, it must be explicitly marked:

```yaml
mapping_status: not_applicable_with_reason
```

Unknown, omitted, or unstated status is not allowed.

---

## 11. Semantic Illusion Warning

Field presence is not semantic enforcement.

Unsafe shallow carrier:

```json
{ "decision_card_ref": "kernel/decision-cards/container-type.v1.json" }
```

Minimum semantic carrier:

```json
{
  "decision_family": "container_type",
  "decision_card_ref": "kernel/decision-cards/container-type.v1.json",
  "selected_option": "flexbox",
  "rejected_options": ["div", "grid"],
  "evidence_refs": ["kernel/source-cards/elementor-flex-layout.v1.json"],
  "evidence_state": "validated",
  "decision_status": "resolved",
  "consumer_stage": "architect.section_structure_planning"
}
```

Critical decision gates require minimum semantic children. A boolean, a single ref string, or a free-text justification is not enough.

---

## 12. Rule Shape

Every validator-backed or stronger decision rule must be expressible as:

```yaml
rule_shape:
  trigger: ""
  predicate: ""
  enforcement: ""
```

Example:

```yaml
rule_shape:
  trigger: on Architect section_plan emit or validation
  predicate: >
    every container_type decision must include decision_family,
    decision_card_ref, selected_option, rejected_options,
    evidence_refs, and evidence_state
  enforcement: reject_output with diagnostic ARCH-KERNEL-DECISION-001
```

A check function that is not attached to a trigger and enforcement action is insufficient.

---

## 13. Risk Levels, Session Scope, and Recovery Action

Only Critical and High EV4 decision rules belong in `DECISION_ESCAPE_ROUTES.yml`.

```yaml
risk_levels:
  Critical:
    violation_can_cause:
      - architecture_drift
      - unsafe_builder_decision
      - invalid_downstream_handoff
      - false_release_readiness
      - decision_lineage_break
      - irreversible_or_expensive_rework
  High:
    violation_can_cause:
      - significant_ambiguity
      - rework
      - layout_drift
      - unsupported_design_assumption
      - wrong_implementation_strategy
```

Every Critical or High rule must declare:

```yaml
session_scope:
  - per_artifact
  - cross_turn

recovery_action:
  - block
  - repair_request
  - rollback
  - flag_for_review
  - reopen_decision
```

A single-fixture CI test is not sufficient for a cross-turn Critical rule.

---

## 14. BRC-Aligned Enforcement Status Ladder

Use this status ladder:

```yaml
enforcement_status:
  - prose_only
  - schema_backed
  - validator_backed
  - fixture_tested
  - advisory_ci_observed
  - ci_enforced
  - sequence_ci_enforced
  - runtime_monitor_enforced
  - os_harness_enforced
  - downstream_contract_enforced
```

Legacy aliases must not be used in new records:

```yaml
legacy_aliases:
  prompt_only: prose_only
  schema_required: schema_backed
  validator_enforced: validator_backed
  fixture_verified: fixture_tested
  ci_verified: ci_enforced
```

`os_harness_enforced` is recognized for BRC compatibility, but it is not required for standard EV4 decision gates unless a rule involves OS/file/network/process/tool side effects.

---

## 15. Minimum Thresholds and Derived Resolution

```yaml
minimum_thresholds:
  Critical_per_artifact:
    minimum: ci_enforced
    target: downstream_contract_enforced
  Critical_cross_turn:
    minimum:
      - sequence_ci_enforced
      - runtime_monitor_enforced
    target: downstream_contract_enforced
  Critical_execution_observable_only:
    minimum: runtime_monitor_enforced
  Critical_OS_file_network_process_side_effect:
    target_where_practical: os_harness_enforced
  High:
    minimum: validator_backed
    preferred:
      - fixture_tested
      - ci_enforced
```

Derived status rules:

```yaml
derived_status_rules:
  resolved:
    Critical_per_artifact:
      true_only_if:
        - enforcement_status in [ci_enforced, sequence_ci_enforced, runtime_monitor_enforced, os_harness_enforced, downstream_contract_enforced]
    Critical_cross_turn:
      true_only_if:
        - enforcement_status in [sequence_ci_enforced, runtime_monitor_enforced, os_harness_enforced, downstream_contract_enforced]
    High:
      true_only_if:
        - enforcement_status in [validator_backed, fixture_tested, ci_enforced, sequence_ci_enforced, runtime_monitor_enforced, os_harness_enforced, downstream_contract_enforced]
  production_ready:
    true_only_if:
      - resolved: true
      - no_missing_required_carriers: true
      - no_open_Critical_escape_routes: true
      - no_false_readiness_claim: true
```

`resolved` and `production_ready` must not be authored fields in `DECISION_ESCAPE_ROUTES.yml`. They are computed audit conclusions.

---

## 16. Detection Method

Each consumer repository must be audited from two directions.

Top-down Kernel coverage:

```text
Kernel decision_family
  → possible consumer repo
  → possible consumer stage
  → output artifact
  → required schema fields
  → required validator diagnostic
  → required positive fixture
  → required negative fixture
  → test command
  → CI evidence
  → downstream rejection
```

Bottom-up repository scan surfaces:

```yaml
scan_surfaces:
  - README
  - AGENTS.md
  - pipeline_docs
  - stage_contracts
  - prompt_templates
  - JSON_schemas
  - handoff_schemas
  - export_schemas
  - validators
  - tests
  - fixtures
  - examples
  - sample_outputs
  - fallback_logic
  - recommended_fields
  - builder_defaults
```

Risky free-form fields:

```yaml
risky_free_form_fields:
  - recommended_element
  - recommended_widget
  - layout_strategy
  - positioning
  - css_strategy
  - unit
  - widget_type
  - class_strategy
  - implementation_notes
  - responsive_strategy
  - asset_strategy
  - semantic_strategy
  - fallback_strategy
  - builder_action
```

---

## 17. Required State File

Every consumer repository should maintain:

```text
planning/DECISION_ESCAPE_ROUTES.yml
```

This file is not merely a task list. It is a BRC-aligned EV4 Decision Gate coverage state file.

Required top-level structure:

```yaml
schema_version: 3
consumer_repo: EV4-Architect-Repo
consumer_repo_evidence_state: expected_unverified

last_updated:
  date: "YYYY-MM-DD"
  pr: null
  commit: null

brc_reference:
  document: Behavioral_Rule_Coverage_v0.4.1
  profile: EV4_CONSUMER_DECISION_TRIGGER_ARCHITECTURE_v0.4.1

kernel_reference:
  repo: EV4-Decision-Kernel
  decision_taxonomy_version: null
  decision_cards_version: null

records: []
```

Each record should include `escape_route_id`, `rule_id`, `concept`, `risk`, `session_scope`, `recovery_action`, `consumer_repo`, `consumer_stage`, `surface_type`, `file_path`, `trigger_type`, `detected_problem`, `kernel_mapping`, `rule_shape`, `carriers`, `status`, and `notes`.

Records must not include authored `resolved` or `production_ready` fields.

---

## 18. Conditional Mapping and Carrier Consistency Rules

```yaml
mapping_status_rules:
  if_mapping_status_mapped:
    decision_family: required_non_null
    required_decision_card_ref_pattern: required_non_empty
    not_applicable_reason: must_be_null
  if_mapping_status_not_applicable_with_reason:
    decision_family: must_be_null
    required_decision_card_ref_pattern: must_be_null
    not_applicable_reason: required_non_empty
```

Carrier-status consistency:

```yaml
carrier_status_rules:
  if_enforcement_status_ci_enforced:
    carriers.CI_step: required_non_null
  if_enforcement_status_sequence_ci_enforced:
    carriers.sequence_CI_step: required_non_null
  if_enforcement_status_runtime_monitor_enforced:
    carriers.runtime_monitor: required_non_null
  if_enforcement_status_os_harness_enforced:
    carriers.os_harness_policy: required_non_null
  if_enforcement_status_downstream_contract_enforced:
    carriers.downstream_contract: required_non_null
```

---

## 19. Stable ID Naming

Expected prefixes:

```yaml
id_prefixes:
  EV4-Architect-Repo: ARCH
  EV4-Constructability-Engineer-Repo: CE
  EV4-Builder-Assistant-Repo: BLD
  EV4-Responsive-Architect: RSP
  EV4-Project-Gate: GATE
```

Patterns:

```text
{PREFIX}-ESC-{NUMBER}
EV4-{PREFIX}-DECISION-{NUMBER}
```

IDs are stable, must not be reused, and must remain in history unless a separate archival process is defined.

---

## 20. Fixture Requirements

Every enforced gate must have both negative and positive fixtures.

Negative fixture proves bypass fails.

```json
{ "section_plan": { "layout_strategy": "Use flexbox because it is simpler." } }
```

Expected result:

```yaml
expected:
  pass: false
  diagnostic_id: ARCH-KERNEL-DECISION-001
  reason: missing decision_card_ref for container_type decision
```

Positive fixture proves valid Kernel-governed path still passes.

```json
{
  "section_plan": {
    "decision_family": "container_type",
    "decision_card_ref": "kernel/decision-cards/container-type.v1.json",
    "selected_option": "flexbox",
    "rejected_options": ["div", "grid"],
    "evidence_refs": ["kernel/source-cards/elementor-flex-layout.v1.json"],
    "evidence_state": "validated"
  }
}
```

Negative fixture alone is insufficient because it may prove that the validator rejects bypasses while also over-rejecting valid outputs.

---

## 21. Diagnostic ID Rules

Pattern:

```text
{CONSUMER}-{DOMAIN}-{CATEGORY}-{NUMBER}
```

Examples:

```text
ARCH-KERNEL-DECISION-001 = missing decision_card_ref
ARCH-KERNEL-DECISION-002 = undeclared decision_family
ARCH-KERNEL-DECISION-003 = selected_option not allowed by decision card
ARCH-KERNEL-DECISION-004 = evidence_refs missing
ARCH-KERNEL-DECISION-005 = free-text decision field without structured decision record
CE-KERNEL-DECISION-001 = constructability proof missing for resolved decision
BLD-KERNEL-DECISION-001 = builder attempted unapproved fallback
RSP-KERNEL-DECISION-001 = runtime evidence contradicts locked decision
GATE-KERNEL-DECISION-001 = decision lineage incomplete
```

Every validator failure must have a stable diagnostic ID.

---

## 22. Consumer Responsibilities

Architect owns design decision records and selected design choices. It must not emit free-form decisions without Kernel references.

CE proves or rejects constructability. It must not invent replacement designs or silently choose substitutes.

Builder executes locked decisions. It must not create new design decisions.

Responsive Validator validates runtime behavior. It must not redesign.

Project Gate validates lineage, schema, evidence completeness, and release readiness. It must not repair decisions.

---

## 23. Human Override, Provisional Decisions, Reopen Loop, and Versioning

Human override must not become a backdoor. A human override must include `override_reason`, `rejected_automated_paths`, `evidence_refs`, `approver`, `risk_acceptance`, and `downstream_constraints`.

A provisional decision is not final proof. If P0 provisional count is greater than zero, release must not be marked production-ready.

A decision record must be reopenable when downstream evidence contradicts or invalidates it.

```yaml
reopen_trigger_source:
  - downstream_failure
  - runtime_evidence_conflict
  - rule_revision
  - evidence_change
  - missing_constructability_proof
  - builder_fallback_attempt
```

Decision records must not be overwritten. Rule and decision card version metadata must be preserved in decision-bearing outputs.

---

## 24. Overclaim Rules

Forbidden unless inspected evidence proves the claim:

```yaml
overclaim_rules:
  - field_exists_therefore_meaning_is_preserved
  - prompt_instruction_exists_therefore_system_level_enforcement_exists
  - model_said_it_followed_the_rule_therefore_compliant
  - fixture_exists_therefore_CI_enforces_it
  - advisory_audit_exists_therefore_Critical_rules_are_ci_enforced
  - synthetic_fixture_passed_therefore_real_E2E_is_proven
  - repository_CI_passed_therefore_production_ready_is_true
  - official_docs_prove_project_availability
  - WordPress_export_evidence_equals_runtime_DOM_evidence
  - decision_card_exists_therefore_builder_execution_is_proven
  - runtime_snapshot_exists_therefore_production_ready_is_true
```

Correction policy:

```yaml
correction_policy:
  - state actual enforcement_status
  - list missing carriers
  - use insufficient_evidence when evidence was not inspected
  - do not upgrade status from model claim
```

---

## 25. Anti-Overengineering Guard

Good enforcement is small, specific, testable, fail-closed, fixture-backed, CI-connected where needed, downstream-aware, and honest about evidence.

Bad enforcement is large, vague, untested, not connected to CI, not connected to downstream rejection, hard to maintain, tracking low-risk style guidance, or claiming more than evidence proves.

Do not create validators for every instruction. Prefer the smallest mechanism that blocks the real failure mode.

---

## 26. Coverage Matrix

Audit output must include this matrix for applicable Critical/High rules:

| rule_id | concept | risk | prose_source | schema_carrier | validator_rule | valid_fixture | invalid_fixture | CI_step | downstream_contract | session_scope | recovery_action | status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

Status must be the strongest proven enforcement status, not the intended target.

---

## 27. Execution Waves

Do not implement all consumer repositories in one PR.

```yaml
execution_waves:
  wave_0:
    name: Architecture baseline
    scope:
      - add canonical architecture document
      - add Persian companion document if needed
      - add DECISION_ESCAPE_ROUTES.yml template
      - add decision-escape-routes.schema.json
      - add PR template checkbox
      - add AGENTS.md update instruction
    no_heavy_repair: true
  wave_1:
    name: Architect first-pass audit
    scope:
      - EV4-Architect-Repo only
      - P0 decision families only
      - discover escape routes
      - populate DECISION_ESCAPE_ROUTES.yml
    patch_allowed: false
  wave_2:
    name: Architect P0 per-artifact enforcement
    status_target: fixture_tested
  wave_3:
    name: Architect P0 CI enforcement
    status_target: ci_enforced
  wave_4:
    name: Cross-turn lineage enforcement
    status_target:
      - sequence_ci_enforced
      - downstream_contract_enforced
```

---

## 28. PR Discipline and AGENTS.md Instruction

PR checklist should include:

```markdown
## Decision Escape Route / Behavioral Rule Coverage Check

- [ ] I reviewed `planning/DECISION_ESCAPE_ROUTES.yml`.
- [ ] I updated affected BRC-aligned records, statuses, carriers, fixtures, diagnostics, or CI evidence.
- [ ] I did not claim a stronger `enforcement_status` than inspected evidence proves.
- [ ] I did not add authored `resolved` or `production_ready` fields.
- [ ] If no update was needed, I explain why below.
```

AGENTS.md should state:

```text
Before opening or completing any PR that changes schemas, validators, prompts, fixtures, pipeline docs, handoff artifacts, fallback behavior, or decision-bearing outputs, review `planning/DECISION_ESCAPE_ROUTES.yml`.

Do not mark an escape route as resolved unless its enforcement_status meets the required threshold for its risk and session_scope.

Do not mark a Critical cross-turn rule as resolved with single-artifact ci_enforced.

Do not add authored resolved or production_ready fields; those are derived audit conclusions.
```

---

## 29. Required Audit Output

A model running this protocol must output:

```markdown
# EV4 Consumer Decision Trigger / BRC Coverage Audit

## 1. Scope Checked
## 2. Evidence Inspected
## 3. Kernel Taxonomy Coverage
## 4. Applicable Critical/High Decision Gates
## 5. Detected Decision Escape Routes
## 6. Coverage Matrix
## 7. Open Enforcement Gaps
## 8. Derived Resolution Check
## 9. Semantic Illusion Risks
## 10. Overclaim / False-Status Risks
## 11. Required Fixtures
## 12. CI / Sequence / Runtime / OS Harness / Downstream Evidence
## 13. Insufficient Evidence
## 14. Adoption vs Enforcement Status
## 15. Minimum Safe Repair Plan
## 16. Final Decision
```

Allowed final decisions:

```yaml
final_decisions:
  PASS: All applicable Critical/High rules meet their required thresholds.
  PASS_WITH_GAPS: Work may continue, but specific non-blocking High gaps remain.
  BLOCKED_OPEN_ENFORCEMENT_GAPS: One or more Critical rules fail their required threshold.
  INSUFFICIENT_EVIDENCE: Evidence is missing, inaccessible, or not inspected.
```

---

## 30. Wave 0 Implementation Boundary

Wave 0 may add this architecture document to a repository without performing a full audit.

Wave 0 must not claim:

```yaml
forbidden_wave_0_claims:
  - escape_routes_audited
  - schema_enforced
  - validator_backed
  - fixture_tested
  - ci_enforced
  - sequence_ci_enforced
  - runtime_monitor_enforced
  - os_harness_enforced
  - downstream_contract_enforced
  - production_ready
```

Wave 0 may claim only:

```yaml
allowed_wave_0_claims:
  - architecture_document_added
  - upstream_contract_adopted
```

---

## Appendix A — Persian Companion Summary

هدف این سند فقط پیدا کردن نقاط واضح تصمیم‌گیری نیست. هدف اصلی این است که مسیرهایی را پیدا کند که در آن‌ها مدل می‌تواند یک تصمیم مهم Elementor V4 را بدون ارجاع معتبر به EV4-Decision-Kernel از pipeline عبور دهد.

این سند نسخهٔ تخصصی EV4 از Behavioral Rule Coverage v0.4.1 است. BRC می‌گوید rule متنی با rule enforce‌شده یکی نیست. این سند همان اصل را برای decision gateهای EV4 اعمال می‌کند.

این سند حافظهٔ مدل نیست؛ قفل مرزی ریپوهای مصرف‌کننده است.

مدل قرار نیست یادش بماند. سیستم باید اجازه ندهد فراموشی مدل از pipeline عبور کند.

صرف وجود یک field مثل `decision_card_ref` کافی نیست. برای تصمیم‌های Critical باید حداقل semantic children وجود داشته باشد:

```yaml
minimum_semantic_children:
  - decision_family
  - decision_card_ref
  - selected_option
  - rejected_options
  - evidence_refs
  - evidence_state
  - consumer_stage
```

در v0.4.1، این دو مقدار نباید داخل `DECISION_ESCAPE_ROUTES.yml` به‌صورت دستی نوشته شوند:

```yaml
forbidden_authored_claims:
  - resolved
  - production_ready
```

این‌ها باید در audit output محاسبه شوند.

قاعدهٔ نهایی: خروجی‌ای که به Kernel رجوع نکرده باشد، نباید بتواند valid عبور کند. حضور این سند در یک ریپو فقط به معنی adoption معماری است، نه enforcement کامل.
