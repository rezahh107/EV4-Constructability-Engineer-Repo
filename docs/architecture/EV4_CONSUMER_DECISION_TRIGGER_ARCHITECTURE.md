# EV4 Consumer Decision Trigger Architecture

**Local role:** upstream architecture adoption document  
**Version adopted:** 0.4.1  
**Canonical source repo:** `rezahh107/EV4-Decision-Kernel`  
**Canonical source path:** `docs/architecture/EV4_CONSUMER_DECISION_TRIGGER_ARCHITECTURE.md`  
**Adoption status:** architecture_adopted_only  

---

## Adoption Boundary

This repository adopts the EV4 Consumer Decision Trigger Architecture as an upstream decision-gate contract.

Presence of this document does **not** prove that this repository has completed decision escape-route audit, schema enforcement, validator implementation, fixtures, CI, sequence enforcement, runtime monitoring, OS/harness enforcement, or downstream contract enforcement.

Allowed claim from this file:

```yaml
claim_allowed: architecture_adopted
claim_forbidden:
  - enforcement_complete
  - escape_routes_audited
  - validator_backed
  - fixture_tested
  - ci_enforced
  - sequence_ci_enforced
  - runtime_monitor_enforced
  - os_harness_enforced
  - downstream_contract_enforced
  - production_ready
```

Repository-specific status must come from inspected evidence and, once initialized, from:

```text
planning/DECISION_ESCAPE_ROUTES.yml
planning/decision-escape-routes.schema.json
```

---

## Core Contract

This document is not model memory. It is the boundary lock for EV4 consumer repositories.

An EV4 consumer repository must not allow a Kernel-governed decision to pass as valid output unless the output contains a valid Kernel decision reference or explicitly returns `insufficient_evidence`.

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

A decision escape route is any path where a model, prompt, schema, validator, handoff artifact, fixture, example, fallback rule, free-form field, implementation default, runtime path, or downstream intake path can carry a Kernel-governed decision without a valid reference to EV4-Decision-Kernel.

---

## Behavioral Rule Coverage Alignment

This repository adopts the EV4 architecture as a domain-specific profile of Behavioral Rule Coverage v0.4.1.

```yaml
brc_alignment:
  behavioral_rule_coverage_version: "0.4.1"
  interpretation:
    decision_gate: domain_specific_behavioral_gate
    decision_escape_route: domain_specific_enforcement_free_or_under_enforced_gate
    decision_enforcement_carrier: domain_specific_enforcement_carrier
  rule_status_source:
    use_brc_status_ladder: true
    do_not_invent_stronger_status: true
```

Use this enforcement status ladder:

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

Do not use legacy aliases such as `prompt_only`, `schema_required`, `validator_enforced`, `fixture_verified`, or `ci_verified` in new records.

---

## Derived Status Rule

`resolved` and `production_ready` are not authored facts.

They are derived conclusions computed from:

```yaml
derived_from:
  - risk
  - session_scope
  - enforcement_status
  - carriers
  - downstream_evidence
  - inspected_proof
```

Do not add authored `resolved` or `production_ready` fields to `DECISION_ESCAPE_ROUTES.yml` records.

---

## Minimum Thresholds

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
  High:
    minimum: validator_backed
    preferred:
      - fixture_tested
      - ci_enforced
```

A single-fixture CI test is not sufficient for a Critical cross-turn rule.

---

## Prompt-Only Enforcement Is Insufficient

A prompt instruction is not an enforcement carrier.

A Markdown requirement, example output, or advisory audit is not hard enforcement.

Hard enforcement must come from machine-checkable or boundary-checkable carriers such as:

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

---

## Semantic Illusion Warning

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

Critical decision gates require minimum semantic children.

---

## Wave 0 Boundary

This file is a Wave 0 architecture adoption artifact.

Wave 0 may claim:

```yaml
allowed_wave_0_claims:
  - architecture_document_added
  - upstream_contract_adopted
```

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

---

## Local Next Step

The next implementation step for this repository is not to claim enforcement. The next step is to initialize local operational state, then run a repo-specific audit:

```text
planning/DECISION_ESCAPE_ROUTES.yml
planning/decision-escape-routes.schema.json
```

Until that exists and is verified, this repository is only `architecture_adopted`, not `enforcement_complete`.
