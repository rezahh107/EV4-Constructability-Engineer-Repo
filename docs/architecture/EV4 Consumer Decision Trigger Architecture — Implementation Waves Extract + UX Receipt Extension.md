# EV4 Consumer Decision Trigger Architecture — Implementation Waves Extract + UX Receipt Extension

```yaml
document_title: EV4 Consumer Decision Trigger Architecture — Implementation Waves Extract + UX Receipt Extension
document_type: implementation_waves_extract_with_proposed_extension
language: English-structured / Persian explanatory compatible
status: draft_for_repository_review
canonical_base_source: docs/architecture/EV4_CONSUMER_DECISION_TRIGGER_ARCHITECTURE.md
extension_source: سند مادر — طراحی UX پاسخ‌های مدل زبانی
```

------

## 1. Source Documents

### 1.1 Canonical EV4 Architecture Source

```yaml
source_document:
  repository: EV4-Decision-Kernel
  path: docs/architecture/EV4_CONSUMER_DECISION_TRIGGER_ARCHITECTURE.md
  title: EV4 Consumer Decision Trigger Architecture
  document_status: proposed normative architecture
  version: "0.4.1"
  canonical_language: English
  primary_operational_artifact_per_consumer_repo: planning/DECISION_ESCAPE_ROUTES.yml
  schema_artifact_per_consumer_repo: planning/decision-escape-routes.schema.json
  state_schema_version: 3
  evidence_state: documented
```

The canonical document states that presence of the architecture document means adoption of the upstream decision-gate contract only; it does not prove audit, schema enforcement, validator implementation, fixtures, CI, runtime monitoring, OS/harness enforcement, or downstream contract enforcement.

### 1.2 UX Presentation Source for Wave 5

```yaml
ux_source_document:
  title: سند مادر — طراحی UX پاسخ‌های مدل زبانی
  version: "1.2.1"
  date: "2026-06-28"
  author: رضا
  status: living document
  role_in_this_extract: presentation_layer_reference_for_wave_5
  not_source_of_truth_for_kernel_decision_validity: true
  evidence_state: ux_supported
```

The UX document defines LLM UX as the cognitive load the user must carry to use model output. It also states that UX without enforcement is only a wish, and that each UX principle must become an enforceable rule.

------

## 2. Extraction Boundary

```yaml
extraction_boundary:
  wave_0_to_wave_4:
    source: canonical_EV4_architecture_document_only
    allowed_evidence_states:
      - documented
      - derived_from_document
      - insufficient_evidence
  wave_5:
    source:
      - proposed_extension_from_current_design_discussion
      - UX_master_document_as_presentation_layer_reference
    allowed_evidence_states:
      - proposed_extension
      - ux_supported
      - insufficient_evidence
  forbidden:
    - using_consumer_adoption_summaries_as_source_of_truth
    - inventing_kernel_decision_families
    - inventing_decision_card_refs
    - replacing_machine_trace_with_human_receipt
    - treating_wave_5_as_already_canonical
```

This document separates **decision validity** from **decision presentation**:

```yaml
source_of_truth_split:
  decision_validity:
    source: EV4_Kernel_decision_cards_machine_trace_validators_gate_evidence
  user_facing_presentation:
    source: UX_master_document_and_wave_5_receipt_rules
```

------

## 3. Cross-Wave Rules

### 3.1 Adoption-Only Boundary

```yaml
adoption_boundary:
  allowed_claim_from_adding_document:
    - architecture_adopted
  forbidden_claims:
    - enforcement_complete
    - escape_routes_audited
    - ci_enforced
    - downstream_contract_enforced
    - production_ready
  evidence_state: documented
```

### 3.2 Wave 0 Allowed and Forbidden Claims

```yaml
wave_0_claim_boundary:
  allowed_wave_0_claims:
    - architecture_document_added
    - upstream_contract_adopted
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
  evidence_state: documented
```

Wave 0 may add the architecture document without performing a full audit.

### 3.3 `DECISION_ESCAPE_ROUTES.yml` Requirements

```yaml
decision_escape_routes_yml:
  path: planning/DECISION_ESCAPE_ROUTES.yml
  purpose: BRC-aligned EV4 Decision Gate coverage state file
  required_top_level_structure:
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
  required_record_fields:
    - escape_route_id
    - rule_id
    - concept
    - risk
    - session_scope
    - recovery_action
    - consumer_repo
    - consumer_stage
    - surface_type
    - file_path
    - trigger_type
    - detected_problem
    - kernel_mapping
    - rule_shape
    - carriers
    - status
    - notes
  forbidden_authored_fields:
    - resolved
    - production_ready
  evidence_state: documented
```

The canonical document uses `records: []`; this document must not introduce `routes[]`.

### 3.4 `decision-escape-routes.schema.json` Requirements

```yaml
decision_escape_routes_schema_json:
  path: planning/decision-escape-routes.schema.json
  must_support:
    - state_schema_version_3
    - required_use_of_records_array
    - required_record_fields
    - prohibition_on_authored_resolved
    - prohibition_on_authored_production_ready
    - conditional_mapping_status_rules
    - carrier_status_consistency_rules
  evidence_state: derived_from_document
```

The schema artifact path is explicitly documented; the schema obligations are derived from required state structure, forbidden fields, mapping rules, and carrier-status consistency rules.

### 3.5 Required Use of `records[]`

```yaml
required_array_name:
  required: records[]
  forbidden:
    - routes[]
  evidence_state: documented
```

### 3.6 Forbidden Authored `resolved` and `production_ready`

```yaml
forbidden_authored_status_fields:
  - resolved
  - production_ready
rule: >
  These are derived audit conclusions, not authored state-file facts.
evidence_state: documented
```

The canonical document states that `resolved` and `production_ready` are not authored facts and must not be authored in `DECISION_ESCAPE_ROUTES.yml`.

### 3.7 Enforcement Status Ladder

```yaml
enforcement_status:
  allowed_values:
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
  legacy_aliases_forbidden_in_new_records:
    prompt_only: prose_only
    schema_required: schema_backed
    validator_enforced: validator_backed
    fixture_verified: fixture_tested
    ci_verified: ci_enforced
  evidence_state: documented
```

`os_harness_enforced` is recognized for BRC compatibility, but is not required for standard EV4 decision gates unless OS/file/network/process/tool side effects are involved.

### 3.8 Minimum Thresholds

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
  evidence_state: documented
```

### 3.9 `risk`

```yaml
risk:
  allowed_in_DECISION_ESCAPE_ROUTES_yml:
    - Critical
    - High
  rule: Only Critical and High EV4 decision rules belong in DECISION_ESCAPE_ROUTES.yml.
  evidence_state: documented
```

### 3.10 `session_scope`

```yaml
session_scope:
  allowed_values:
    - per_artifact
    - cross_turn
  required_for:
    - Critical
    - High
  evidence_state: documented
```

### 3.11 `recovery_action`

```yaml
recovery_action:
  allowed_values:
    - block
    - repair_request
    - rollback
    - flag_for_review
    - reopen_decision
  required_for:
    - Critical
    - High
  evidence_state: documented
```

### 3.12 `rule_shape`

```yaml
rule_shape:
  required_for: validator_backed_or_stronger_decision_rules
  required_children:
    - trigger
    - predicate
    - enforcement
  insufficiency_rule: check_function_without_trigger_and_enforcement_action_is_insufficient
  evidence_state: documented
```

### 3.13 Evidence States

```yaml
evidence_states:
  canonical_document_states:
    - observed
    - exported
    - validated
    - resolved
    - derived
    - proposed
    - unverified
    - insufficient_evidence
    - not_applicable
  this_extract_additional_labels:
    - documented
    - derived_from_document
    - proposed_extension
    - ux_supported
  evidence_state: documented
```

The canonical evidence rules forbid converting missing evidence into guessed values, claiming CI/downstream/runtime proof without inspected evidence, and claiming real E2E from synthetic fixtures.

### 3.14 Anti-Overclaim Rules

```yaml
anti_overclaim_rules:
  forbidden_unless_inspected_evidence_proves_claim:
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
  correction_policy:
    - state_actual_enforcement_status
    - list_missing_carriers
    - use_insufficient_evidence_when_evidence_was_not_inspected
    - do_not_upgrade_status_from_model_claim
  evidence_state: documented
```

### 3.15 Audit Output Requirements

```yaml
required_audit_output_sections:
  - Scope Checked
  - Evidence Inspected
  - Kernel Taxonomy Coverage
  - Applicable Critical/High Decision Gates
  - Detected Decision Escape Routes
  - Coverage Matrix
  - Open Enforcement Gaps
  - Derived Resolution Check
  - Semantic Illusion Risks
  - Overclaim / False-Status Risks
  - Required Fixtures
  - CI / Sequence / Runtime / OS Harness / Downstream Evidence
  - Insufficient Evidence
  - Adoption vs Enforcement Status
  - Minimum Safe Repair Plan
  - Final Decision
allowed_final_decisions:
  PASS: All applicable Critical/High rules meet their required thresholds.
  PASS_WITH_GAPS: Work may continue, but specific non-blocking High gaps remain.
  BLOCKED_OPEN_ENFORCEMENT_GAPS: One or more Critical rules fail their required threshold.
  INSUFFICIENT_EVIDENCE: Evidence is missing, inaccessible, or not inspected.
evidence_state: documented
```

### 3.16 PR Discipline Requirements

```yaml
pr_checklist_required_content:
  - reviewed_planning_DECISION_ESCAPE_ROUTES_yml
  - updated_affected_BRC_aligned_records_statuses_carriers_fixtures_diagnostics_or_CI_evidence
  - did_not_claim_stronger_enforcement_status_than_inspected_evidence_proves
  - did_not_add_authored_resolved_or_production_ready_fields
  - explained_why_no_update_was_needed_if_no_update_was_needed
  evidence_state: documented
```

### 3.17 AGENTS.md Instruction Requirements

```yaml
agents_md_should_state:
  - before_opening_or_completing_PRs_that_change_schemas_validators_prompts_fixtures_pipeline_docs_handoff_artifacts_fallback_behavior_or_decision_bearing_outputs_review_DECISION_ESCAPE_ROUTES_yml
  - do_not_mark_escape_route_resolved_unless_enforcement_status_meets_required_threshold_for_risk_and_session_scope
  - do_not_mark_Critical_cross_turn_rule_resolved_with_single_artifact_ci_enforced
  - do_not_add_authored_resolved_or_production_ready_fields
  evidence_state: documented
```

------

## 4. Wave Summary Table

| Wave | Name                                            | Status             | Explicit Scope / Target                                      | Patch Allowed         |
| ---- | ----------------------------------------------- | ------------------ | ------------------------------------------------------------ | --------------------- |
| 0    | Architecture baseline                           | documented         | Add architecture baseline artifacts and instructions; no heavy repair | insufficient_evidence |
| 1    | Architect first-pass audit                      | documented         | EV4-Architect-Repo only; P0 decision families only; discover escape routes; populate state file | false                 |
| 2    | Architect P0 per-artifact enforcement           | documented         | status target: fixture_tested                                | insufficient_evidence |
| 3    | Architect P0 CI enforcement                     | documented         | status target: ci_enforced                                   | insufficient_evidence |
| 4    | Cross-turn lineage enforcement                  | documented         | status target: sequence_ci_enforced and downstream_contract_enforced | insufficient_evidence |
| 5    | UX-Safe Human-Readable Kernel Decision Receipts | proposed_extension | add human-facing receipt backed by machine trace across all decision-bearing outputs | true, within limits   |

The canonical execution-wave list contains Wave 0 through Wave 4. Wave 5 is added by this document as a proposed extension.

------

## 5. Wave 0 — Architecture Baseline / Adoption

```yaml
wave:
  number: 0
  name: Architecture baseline
  canonical_status: documented
  purpose:
    value: establish_architecture_adoption_baseline_without_claiming_enforcement
    evidence_state: derived_from_document
  scope:
    - add canonical architecture document
    - add Persian companion document if needed
    - add DECISION_ESCAPE_ROUTES.yml template
    - add decision-escape-routes.schema.json
    - add PR template checkbox
    - add AGENTS.md update instruction
    evidence_state: documented
  required_files:
    - docs/architecture/EV4_CONSUMER_DECISION_TRIGGER_ARCHITECTURE.md
    - planning/DECISION_ESCAPE_ROUTES.yml
    - planning/decision-escape-routes.schema.json
    evidence_state: derived_from_document
  optional_files:
    - Persian companion document if needed
    evidence_state: documented
  allowed_actions:
    - add_architecture_document
    - adopt_upstream_contract
    - add_baseline_artifacts
    evidence_state: documented
  forbidden_actions:
    - full_audit_claim
    - heavy_repair
    - claim_escape_routes_audited
    - claim_schema_enforced
    - claim_validator_backed
    - claim_fixture_tested
    - claim_ci_enforced
    - claim_sequence_ci_enforced
    - claim_runtime_monitor_enforced
    - claim_os_harness_enforced
    - claim_downstream_contract_enforced
    - claim_production_ready
    evidence_state: documented
  patch_allowed:
    status: insufficient_evidence
  expected_status_target:
    status: insufficient_evidence
  required_evidence:
    - evidence_that_architecture_document_was_added
    - evidence_that_upstream_contract_was_adopted
    evidence_state: derived_from_document
  required_artifacts:
    - canonical_architecture_document
    - DECISION_ESCAPE_ROUTES_yml_template
    - decision_escape_routes_schema_json
    - PR_template_checkbox
    - AGENTS_md_update_instruction
    evidence_state: documented
  deferred_work:
    - full_audit
    - heavy_repair
    - enforcement_claims
    evidence_state: derived_from_document
  overclaim_risks:
    - treating_architecture_presence_as_enforcement_complete
    - treating_adoption_as_audit_completion
    - treating_schema_presence_as_schema_enforced
    - treating_document_addition_as_production_ready
    evidence_state: derived_from_document
  completion_criteria:
    - architecture_document_added
    - upstream_contract_adopted
    evidence_state: documented
  next_wave_dependency:
    value: Wave 1 performs Architect first-pass audit after baseline adoption.
    evidence_state: derived_from_document
```

------

## 6. Wave 1 — Local State / First-Pass Audit Preparation

```yaml
wave:
  number: 1
  name: Architect first-pass audit
  canonical_status: documented
  purpose:
    value: discover_P0_Architect_decision_escape_routes_and_populate_DECISION_ESCAPE_ROUTES_yml
    evidence_state: derived_from_document
  scope:
    - EV4-Architect-Repo only
    - P0 decision families only
    - discover escape routes
    - populate DECISION_ESCAPE_ROUTES.yml
    evidence_state: documented
  required_files:
    - planning/DECISION_ESCAPE_ROUTES.yml
    evidence_state: documented
  optional_files:
    status: insufficient_evidence
  allowed_actions:
    - audit_EV4_Architect_Repo_only
    - audit_P0_decision_families_only
    - discover_escape_routes
    - populate_DECISION_ESCAPE_ROUTES_yml
    evidence_state: documented
  forbidden_actions:
    - patching
    evidence_state: documented
  patch_allowed:
    value: false
    evidence_state: documented
  expected_status_target:
    status: insufficient_evidence
  required_evidence:
    - discovered_escape_routes_recorded_in_DECISION_ESCAPE_ROUTES_yml
    evidence_state: derived_from_document
  required_artifacts:
    - populated_DECISION_ESCAPE_ROUTES_yml
    evidence_state: documented
  deferred_work:
    - per_artifact_enforcement
    - CI_enforcement
    - cross_turn_lineage_enforcement
    evidence_state: derived_from_document
  overclaim_risks:
    - treating_first_pass_audit_as_enforcement
    - treating_populated_state_file_as_resolved_status
    - claiming_patch_or_repair_when_patch_allowed_is_false
    evidence_state: derived_from_document
  completion_criteria:
    - P0_Architect_escape_routes_discovered
    - DECISION_ESCAPE_ROUTES_yml_populated
    evidence_state: derived_from_document
  next_wave_dependency:
    value: Wave 2 depends on Wave 1 discovery/population because Wave 2 targets Architect P0 per-artifact enforcement.
    evidence_state: derived_from_document
```

------

## 7. Wave 2 — Per-Artifact Enforcement

```yaml
wave:
  number: 2
  name: Architect P0 per-artifact enforcement
  canonical_status: documented
  purpose:
    value: move_Architect_P0_per_artifact_rules_toward_fixture_tested_status
    evidence_state: derived_from_document
  scope:
    status: insufficient_evidence
  required_files:
    status: insufficient_evidence
  optional_files:
    status: insufficient_evidence
  allowed_actions:
    status: insufficient_evidence
  forbidden_actions:
    status: insufficient_evidence
  patch_allowed:
    status: insufficient_evidence
  expected_status_target:
    value: fixture_tested
    evidence_state: documented
  required_evidence:
    - positive_fixture
    - negative_fixture
    evidence_state: derived_from_document
  required_artifacts:
    - fixtures_for_enforced_gate
    evidence_state: derived_from_document
  deferred_work:
    - CI_enforcement
    - cross_turn_lineage_enforcement
    evidence_state: derived_from_document
  overclaim_risks:
    - claiming_ci_enforced_from_fixture_tested
    - claiming_fixture_tested_from_negative_fixture_only
    - claiming_Critical_per_artifact_resolved_below_required_threshold
    evidence_state: derived_from_document
  completion_criteria:
    - status_target_fixture_tested_met
    evidence_state: derived_from_document
  next_wave_dependency:
    value: Wave 3 follows Wave 2 and targets CI enforcement.
    evidence_state: derived_from_document
```

Every enforced gate must have both negative and positive fixtures; a negative fixture alone is insufficient.

------

## 8. Wave 3 — CI Enforcement

```yaml
wave:
  number: 3
  name: Architect P0 CI enforcement
  canonical_status: documented
  purpose:
    value: move_Architect_P0_rules_to_ci_enforced_status
    evidence_state: derived_from_document
  scope:
    status: insufficient_evidence
  required_files:
    status: insufficient_evidence
  optional_files:
    status: insufficient_evidence
  allowed_actions:
    status: insufficient_evidence
  forbidden_actions:
    status: insufficient_evidence
  patch_allowed:
    status: insufficient_evidence
  expected_status_target:
    value: ci_enforced
    evidence_state: documented
  required_evidence:
    - inspected_CI_evidence
    evidence_state: derived_from_document
  required_artifacts:
    status: insufficient_evidence
  deferred_work:
    - cross_turn_lineage_enforcement
    - downstream_contract_enforcement
    evidence_state: derived_from_document
  overclaim_risks:
    - claiming_CI_enforcement_without_inspected_CI_evidence
    - claiming_downstream_contract_enforced_from_CI
    - claiming_Critical_cross_turn_resolved_with_single_artifact_ci_enforced
    evidence_state: documented
  completion_criteria:
    - status_target_ci_enforced_met
    evidence_state: derived_from_document
  next_wave_dependency:
    value: Wave 4 follows Wave 3 and targets sequence/downstream enforcement.
    evidence_state: derived_from_document
```

------

## 9. Wave 4 — Cross-Turn / Downstream Enforcement

```yaml
wave:
  number: 4
  name: Cross-turn lineage enforcement
  canonical_status: documented
  purpose:
    value: enforce_cross_turn_lineage_with_sequence_CI_and_downstream_contract_enforcement
    evidence_state: derived_from_document
  scope:
    status: insufficient_evidence
  required_files:
    status: insufficient_evidence
  optional_files:
    status: insufficient_evidence
  allowed_actions:
    status: insufficient_evidence
  forbidden_actions:
    status: insufficient_evidence
  patch_allowed:
    status: insufficient_evidence
  expected_status_target:
    - sequence_ci_enforced
    - downstream_contract_enforced
    evidence_state: documented
  required_evidence:
    - sequence_CI_step_if_sequence_ci_enforced
    - downstream_contract_if_downstream_contract_enforced
    evidence_state: derived_from_document
  required_artifacts:
    status: insufficient_evidence
  deferred_work:
    status: insufficient_evidence
  overclaim_risks:
    - claiming_downstream_enforcement_without_downstream_contract_evidence
    - claiming_Critical_cross_turn_resolved_with_ci_enforced_only
    - claiming_runtime_or_downstream_proof_without_corresponding_carrier
    evidence_state: documented
  completion_criteria:
    - status_target_sequence_ci_enforced_met
    - status_target_downstream_contract_enforced_met
    evidence_state: derived_from_document
  next_wave_dependency:
    value: Wave 5 may safely render human-readable decision receipts only after machine trace and downstream lineage rules are enforceable.
    evidence_state: proposed_extension
```

Wave 4 explicitly targets `sequence_ci_enforced` and `downstream_contract_enforced`. Carrier consistency rules require corresponding carriers for these statuses.

------

## 10. Wave 5 — UX-Safe Human-Readable Kernel Decision Receipts

```yaml
wave:
  number: 5
  name: UX-Safe Human-Readable Kernel Decision Receipts
  canonical_status: not_present_in_current_canonical_document
  classification: proposed_extension
  ux_alignment: سند مادر — طراحی UX پاسخ‌های مدل زبانی
```

### 10.1 Purpose

```yaml
purpose:
  value: >
    Make Kernel-governed decisions visible, understandable, and low-noise in every
    consumer-facing report, handoff, action list, audit output, and Builder instruction,
    while preserving the machine-readable decision trace as the source of truth.
  evidence_state: proposed_extension
```

Wave 5 exists because a user-facing Builder instruction such as:

```text
Select Image element.
Set height to 320px.
```

does not prove that the Builder actually traversed or referenced the Kernel decision card.

Wave 5 requires a short human-readable receipt backed by a machine-readable trace.

Required human-facing pattern:

```text
✅ تصمیم به decision card کرنل وصل شده است؛ <selected_option> انتخاب شد چون <short_reason>.
```

Example:

```text
✅ تصمیم به decision card کرنل وصل شده است؛ برای ارتفاع Image مقدار 320px انتخاب شد چون این بخش نیاز به اندازهٔ ثابت و قابل بازتولید در Builder دارد، نه مقدار نسبی وابسته به والد.
```

### 10.2 UX Rationale

```yaml
ux_rationale:
  cognitive_load:
    rule: show_the_smallest_useful_receipt_not_the_full_trace_by_default
    evidence_state: ux_supported
  enforcement_honesty:
    rule: green_check_requires_machine_trace_and_validator_or_gate_support
    evidence_state: ux_supported
  fixed_format:
    rule: all_repositories_must_render_receipts_with_a_stable_pattern
    evidence_state: ux_supported
  uncertainty:
    rule: if_trace_is_missing_or_unverified_do_not_show_success_receipt
    evidence_state: ux_supported
  no_hidden_state_claim:
    rule: do_not_claim_kernel_connection_without_real_trace_or_storage_evidence
    evidence_state: ux_supported
```

The UX document supports this by requiring reduced noise, stable format, transparency around uncertainty, enforceable UX rules, and no false hidden-state claims.

### 10.3 Scope

```yaml
scope:
  applies_to_repositories:
    - EV4-Architect-Repo
    - EV4-Constructability-Engineer-Repo
    - EV4-Builder-Assistant-Repo
    - EV4-Responsive-Architect
    - EV4-Project-Gate
  applies_to_outputs:
    - architecture_plans
    - section_plans
    - constructability_reports
    - builder_action_reports
    - builder_step_outputs
    - responsive_validation_reports
    - handoff_artifacts
    - project_gate_audit_outputs
    - release_readiness_outputs
    - repair_handoff_outputs
  applies_when:
    - output_contains_kernel_governed_decision
    - output_recommends_kernel_governed_choice
    - output_accepts_or_rejects_kernel_governed_choice
    - output_executes_kernel_governed_choice
    - output_passes_kernel_governed_decision_downstream
  evidence_state: proposed_extension
```

### 10.4 Applicable Decision Families

```yaml
example_applicable_decision_families:
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
rule: >
  Wave 5 must not invent new decision families. It may render receipts only for
  Kernel-governed decision families already supported by the Kernel taxonomy.
evidence_state: proposed_extension
```

### 10.5 Required Files

```yaml
required_files:
  state_tracking:
    - planning/DECISION_ESCAPE_ROUTES.yml
  schemas_or_contracts:
    - relevant_output_schema_files_that_emit_decision_bearing_reports
    - relevant_handoff_schema_files_that_carry_decision_bearing_outputs
  validators:
    - relevant_report_or_handoff_validators
  fixtures:
    - positive_fixture_with_valid_human_receipt_and_valid_machine_trace
    - negative_fixture_with_green_check_but_missing_machine_trace
    - negative_fixture_with_receipt_reason_not_supported_by_trace
    - negative_fixture_with_decision_card_claim_but_missing_decision_card_ref
  documentation_or_templates:
    - report_templates_that_emit_decision_bearing_outputs
    - handoff_templates_that_emit_decision_bearing_outputs
    - AGENTS.md
    - PR_template_or_PR_checklist
  evidence_state: proposed_extension
```

### 10.6 Optional Files

```yaml
optional_files:
  - docs/reporting/KERNEL_DECISION_RECEIPT_STYLE_GUIDE.md
  - docs/examples/kernel-decision-receipts.valid.md
  - docs/examples/kernel-decision-receipts.invalid.md
  - shared_snippets_or_templates_for_consistent_receipt_language
  evidence_state: proposed_extension
```

Optional files may standardize receipt wording, but they must not become the source of truth. The source of truth remains the machine-readable trace and its validation evidence.

### 10.7 Allowed Actions

```yaml
allowed_actions:
  - add_short_human_readable_kernel_decision_receipts_to_reports
  - add_receipt_sections_to_builder_action_outputs
  - add_receipt_sections_to_architect_CE_responsive_and_gate_reports
  - add_schema_fields_or_template_slots_for_human_receipts
  - add_validator_rules_that_require_receipt_when_kernel_governed_decision_is_present
  - add_validator_rules_that_require_receipt_to_reference_existing_machine_trace
  - add_positive_and_negative_fixtures
  - add_CI_checks_for_receipt_trace_consistency
  - update_AGENTS_md_with_receipt_requirements
  - update_PR_checklist_with_receipt_verification
  evidence_state: proposed_extension
```

### 10.8 Forbidden Actions

```yaml
forbidden_actions:
  - adding_green_check_without_machine_readable_decision_trace
  - claiming_decision_card_connection_without_decision_card_ref
  - claiming_kernel_validation_without_validator_or_gate_evidence
  - inventing_decision_family
  - inventing_decision_card_ref
  - inventing_evidence_refs
  - writing_resolved_as_authored_field
  - writing_production_ready_as_authored_field
  - using_human_receipt_as_substitute_for_machine_trace
  - hiding_insufficient_evidence_behind_friendly_language
  - using_generic_reason_that_is_not_supported_by_selected_option_rejected_options_and_evidence_refs
  - adding_receipts_for_low_risk_style_preferences_as_if_they_are_kernel_governed_decisions
  - exposing_raw_internal_evidence_fields_by_default
  evidence_state: proposed_extension
```

### 10.9 Patch Allowed

```yaml
patch_allowed:
  value: true
  limits:
    - patch_report_templates
    - patch_handoff_templates
    - patch_output_schemas
    - patch_validators
    - patch_fixtures
    - patch_CI_checks_for_receipt_trace_consistency
    - patch_AGENTS_md
    - patch_PR_checklist
  forbidden_patch_scope:
    - do_not_change_kernel_decision_semantics
    - do_not_create_new_decision_families
    - do_not_create_new_decision_cards_without_kernel_process
    - do_not_rewrite_cross_repo_architecture
    - do_not_claim_full_enforcement_from_receipt_presence
  evidence_state: proposed_extension
```

### 10.10 Expected Status Target

```yaml
expected_status_target:
  minimum:
    - ci_enforced
  target:
    - downstream_contract_enforced
  explanation: >
    A receipt requirement is reliable only when CI can fail outputs that claim a
    Kernel-linked decision without a valid machine-readable trace. The downstream
    target is reached when Project Gate or the next consumer can reject outputs
    whose human receipt and machine trace are missing or inconsistent.
  evidence_state: proposed_extension
```

### 10.11 Required Evidence

```yaml
required_evidence:
  per_repository:
    - report_or_handoff_surface_inventory
    - list_of_decision_bearing_outputs
    - updated_schema_or_template_showing_receipt_slot
    - validator_rule_rejecting_receipt_without_trace
    - validator_rule_rejecting_trace_without_required_human_receipt_where_applicable
    - positive_fixture_receipt_with_valid_trace
    - negative_fixture_green_check_without_trace
    - negative_fixture_reason_not_supported_by_trace
    - CI_log_showing_receipt_trace_validation
  downstream:
    - downstream_consumer_rejects_missing_or_inconsistent_receipt_when_required
    - Project_Gate_reports_receipt_trace_consistency_status
  evidence_state: proposed_extension
```

### 10.12 Required Artifacts

```yaml
required_artifacts:
  human_receipt_shape:
    required_fields:
      - visible_status_marker
      - decision_card_connection_statement
      - selected_option_summary
      - short_reason
      - trace_reference_or_trace_id
  machine_trace_shape:
    required_fields:
      - decision_family
      - decision_card_ref
      - selected_option
      - rejected_options
      - evidence_refs
      - evidence_state
      - consumer_stage
  receipt_trace_consistency_rule:
    required: true
  evidence_state: proposed_extension
```

Recommended human-readable shape:

```yaml
human_receipt:
  visible_status_marker: "✅"
  statement: "تصمیم به decision card کرنل وصل شده است."
  selected_option_summary: "<what was selected>"
  short_reason: "<why this option was selected instead of alternatives>"
  trace_reference: "<decision_trace_id>"
```

Example Builder output:

```text
Action:
Select Image element.
Set height to 320px.

✅ تصمیم به decision card کرنل وصل شده است؛ برای ارتفاع Image مقدار 320px انتخاب شد چون این بخش نیاز به اندازهٔ ثابت و قابل بازتولید در Builder دارد، نه مقدار نسبی وابسته به والد.
```

Corresponding machine trace:

```yaml
decision_trace:
  id: BLD-TRACE-UNIT-001
  decision_family: unit_policy
  consumer_stage: builder.widget_configuration
  surface: image.height
  selected_option:
    value: 320
    unit: px
  rejected_options:
    - "%"
    - vh
    - auto
  decision_card_ref: kernel/decision-cards/unit-policy.v1.json
  evidence_refs:
    - kernel/source-cards/elementor-size-controls.v1.json
  evidence_state: validated
```

### 10.13 Required User-Facing States

```yaml
required_user_facing_states:
  success_receipt:
    allowed_when:
      - machine_trace_exists
      - decision_card_ref_present
      - selected_option_present
      - rejected_options_present
      - evidence_refs_present
      - evidence_state_is_not_insufficient_evidence
      - validator_or_gate_accepts_trace
    pattern: "✅ تصمیم به decision card کرنل وصل شده است؛ <selected_option> انتخاب شد چون <short_reason>."
  insufficient_evidence_receipt:
    required_when:
      - machine_trace_missing
      - decision_card_ref_missing
      - evidence_refs_missing
      - evidence_state_is_insufficient_evidence
      - validator_or_gate_evidence_not_inspected
    pattern: "⚠️ این تصمیم هنوز به decision card کرنل قابل‌اثبات وصل نشده است؛ برای تأیید، decision trace یا evidence لازم است."
  evidence_state: proposed_extension
```

### 10.14 Deferred Work

```yaml
deferred_work:
  - visual_UI_badges_inside_a_dedicated_operator_panel
  - automatic_expansion_of_receipt_into_full_trace_on_click
  - natural_language_reason_quality_scoring
  - multi_language_receipt_rendering_beyond_required_repository_language
  - telemetry_or_runtime_receipt_display_tracking
  evidence_state: proposed_extension
```

### 10.15 Overclaim Risks

```yaml
overclaim_risks:
  - green_check_becomes_decorative
  - human_receipt_claims_kernel_link_without_machine_trace
  - receipt_reason_is_written_after_the_fact_without_evidence
  - selected_option_is_explained_but_rejected_options_are_missing
  - reports_look_trustworthy_while_validators_do_not_enforce_consistency
  - Project_Gate_accepts_friendly_text_instead_of_structured_trace
  - receipt_presence_is_mistaken_for_production_readiness
  - raw_internal_evidence_is_shown_to_user_as_if_it_were_actionable
  evidence_state: proposed_extension
```

### 10.16 Completion Criteria

```yaml
completion_criteria:
  per_repository:
    - all_decision_bearing_report_surfaces_are_inventoried
    - every_required_surface_has_human_receipt_template_or_field
    - every_human_receipt_links_to_machine_readable_trace
    - validator_rejects_green_check_without_trace
    - validator_rejects_receipt_reason_not_supported_by_trace
    - positive_and_negative_fixtures_exist
    - CI_runs_receipt_trace_consistency_check
    - DECISION_ESCAPE_ROUTES_yml_records_updated_with_receipt_enforcement_status
  cross_repository:
    - Project_Gate_or_downstream_consumer_can_detect_missing_receipt
    - Project_Gate_or_downstream_consumer_can_detect_receipt_trace_mismatch
    - no_repository_claims_receipt_presence_as_production_ready
  evidence_state: proposed_extension
```

### 10.17 Next-Wave Dependency

```yaml
next_wave_dependency:
  value: >
    Wave 5 depends on Wave 4-level machine trace and downstream lineage enforcement.
    If machine-readable trace enforcement is absent, outputs must not show a green
    Kernel-linked success receipt. They must show insufficient_evidence instead.
  evidence_state: proposed_extension
```

### 10.18 Cross-Repository Reporting Rule Added by Wave 5

```yaml
cross_repository_reporting_rule:
  when_output_contains_kernel_governed_decision:
    must_show_human_receipt: true
    must_link_to_machine_trace: true
    must_explain_selected_option_briefly: true
    must_not_expose_full_trace_by_default: true
  required_user_visible_receipt:
    pattern: "✅ تصمیم به decision card کرنل وصل شده است؛ <selected_option> انتخاب شد چون <short_reason>."
  required_machine_backing:
    - decision_family
    - decision_card_ref
    - selected_option
    - rejected_options
    - evidence_refs
    - evidence_state
    - consumer_stage
  fail_closed_cases:
    - selected_option_present_but_no_decision_card_ref
    - green_check_present_but_no_machine_trace
    - reason_present_but_no_rejected_options_or_evidence_refs
    - receipt_claims_validated_but_evidence_state_is_unverified_or_insufficient_evidence
  evidence_state: proposed_extension
```

### 10.19 Required PR Checklist Addition

```markdown
- [ ] If this PR changes a decision-bearing output, report, handoff, or Builder instruction, I added or preserved the human-readable Kernel decision receipt.
- [ ] Every visible ✅ Kernel-linked decision receipt is backed by a machine-readable decision trace.
- [ ] I did not add a green check, reason sentence, or Kernel-linked claim without `decision_card_ref`, `selected_option`, `rejected_options`, `evidence_refs`, and `evidence_state`.
- [ ] If evidence was missing, I used `insufficient_evidence` instead of a friendly success message.
```

### 10.20 Required AGENTS.md Addition

```text
When producing or modifying any decision-bearing report, handoff, audit output, or Builder instruction, include a short human-readable Kernel decision receipt for every Kernel-governed decision that is presented to the user.

The receipt must be concise and user-facing, for example:

✅ تصمیم به decision card کرنل وصل شده است؛ px انتخاب شد چون این کنترل نیاز به مقدار ثابت و قابل بازتولید دارد.

Do not add this receipt unless a machine-readable decision trace exists and includes decision_family, decision_card_ref, selected_option, rejected_options, evidence_refs, evidence_state, and consumer_stage.

A green check without trace evidence is an overclaim.
```

------

## 11. Required Files and Artifacts

```yaml
required_or_documented_artifacts:
  canonical_architecture_document:
    path: docs/architecture/EV4_CONSUMER_DECISION_TRIGGER_ARCHITECTURE.md
    evidence_state: documented
  primary_operational_artifact:
    path: planning/DECISION_ESCAPE_ROUTES.yml
    evidence_state: documented
  schema_artifact:
    path: planning/decision-escape-routes.schema.json
    evidence_state: documented
  pr_template_checkbox:
    exact_file_path:
      status: insufficient_evidence
    evidence_state: documented
  AGENTS_md_update_instruction:
    file: AGENTS.md
    evidence_state: documented
  Persian_companion_document:
    required: false_if_not_needed
    condition: if_needed
    exact_file_path:
      status: insufficient_evidence
    evidence_state: documented
  fixtures:
    requirement: every_enforced_gate_must_have_both_negative_and_positive_fixtures
    evidence_state: documented
  diagnostic_ids:
    requirement: every_validator_failure_must_have_stable_diagnostic_ID
    evidence_state: documented
  coverage_matrix:
    requirement: audit_output_must_include_matrix_for_applicable_Critical_High_rules
    evidence_state: documented
  wave_5_receipt_artifacts:
    required:
      - human_receipt_template_or_schema_slot
      - machine_trace_reference
      - receipt_trace_consistency_validator
      - receipt_positive_and_negative_fixtures
      - receipt_CI_check
    evidence_state: proposed_extension
```

------

## 12. Forbidden Claims and Overclaim Controls

```yaml
forbidden_claim_controls:
  adoption_does_not_prove:
    - enforcement_complete
    - escape_routes_audited
    - ci_enforced
    - downstream_contract_enforced
    - production_ready
  wave_0_does_not_prove:
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
  wave_5_does_not_prove:
    - kernel_decision_validity_without_machine_trace
    - downstream_contract_enforced_without_downstream_evidence
    - production_ready
    - resolved_as_authored_fact
  missing_evidence_rule:
    - use_insufficient_evidence_when_evidence_was_not_inspected
    - never_convert_missing_evidence_into_a_guessed_value
  semantic_illusion_rule:
    - field_presence_is_not_semantic_enforcement
    - green_check_is_not_semantic_enforcement
    - boolean_single_ref_string_or_free_text_justification_is_not_enough_for_Critical_decision_gates
  evidence_state:
    wave_0_to_wave_4: documented
    wave_5: proposed_extension
```

------

## 13. Derived vs Authored Status Rules

```yaml
derived_not_authored:
  forbidden_authored_fields_in_DECISION_ESCAPE_ROUTES_yml:
    - resolved
    - production_ready
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
  wave_5_receipt_status:
    rule: >
      A human-readable receipt is also not an authored proof of resolution.
      It is only a visible rendering of a validated machine trace.
  evidence_state:
    canonical_rules: documented
    wave_5_rule: proposed_extension
```

------

## 14. Open Questions / Insufficient Evidence

```yaml
open_questions_or_insufficient_evidence:
  wave_0_patch_allowed:
    status: insufficient_evidence
  wave_0_expected_status_target:
    status: insufficient_evidence
  wave_1_expected_status_target:
    status: insufficient_evidence
  wave_2_detailed_scope:
    status: insufficient_evidence
  wave_2_patch_allowed:
    status: insufficient_evidence
  wave_2_required_files_exact_paths:
    status: insufficient_evidence
  wave_3_detailed_scope:
    status: insufficient_evidence
  wave_3_patch_allowed:
    status: insufficient_evidence
  wave_3_required_files_exact_paths:
    status: insufficient_evidence
  wave_4_detailed_scope:
    status: insufficient_evidence
  wave_4_patch_allowed:
    status: insufficient_evidence
  wave_4_required_files_exact_paths:
    status: insufficient_evidence
  wave_4_next_wave_dependency_in_canonical_document:
    status: insufficient_evidence
  later_waves_after_wave_4_in_canonical_document:
    status: insufficient_evidence
  exact_PR_template_file_path:
    status: insufficient_evidence
  exact_Persian_companion_document_path:
    status: insufficient_evidence
  wave_5_canonical_adoption:
    status: insufficient_evidence
    note: Wave 5 is proposed by this document and is not present in the current canonical architecture document.
```

------

## 15. Final Implementation Ordering

```yaml
implementation_order:
  - wave: 0
    name: Architecture baseline
    reason: establish_adoption_without_enforcement_claims
  - wave: 1
    name: Architect first-pass audit
    reason: discover_escape_routes_before_repair
  - wave: 2
    name: Architect P0 per-artifact enforcement
    reason: establish_fixture_tested_per_artifact_behavior
  - wave: 3
    name: Architect P0 CI enforcement
    reason: make_per_artifact_enforcement_fail_closed_in_CI
  - wave: 4
    name: Cross-turn lineage enforcement
    reason: enforce_sequence_and_downstream_lineage
  - wave: 5
    name: UX-Safe Human-Readable Kernel Decision Receipts
    reason: render_validated_trace_as_short_user_visible_decision_receipt
```

Mental model:

```text
Wave 0–4 build the rail.
Wave 5 puts a small visible signal on the rail.

The signal is useful only if the rail exists.
A green check without the rail is overclaim.
```

Final receipt rule:

```yaml
final_receipt_rule:
  if_kernel_governed_decision_is_visible_to_user:
    require_user_visible_receipt: true
    require_machine_trace: true
    require_trace_consistency_validation: true
  if_machine_trace_is_missing:
    forbid_green_check: true
    require_insufficient_evidence_message: true
```