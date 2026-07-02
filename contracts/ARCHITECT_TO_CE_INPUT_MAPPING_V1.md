# Architect to CE Input Mapping v1

Status: contract_definition_v1  
Input schema: `ev4-architect-output-contract@1.0.0`  
CE ingestion schema: `ev4-architect-to-ce-input-package@1.0.0`  
Owning repo: `rezahh107/EV4-Constructability-Engineer-Repo`

## Purpose

This contract defines how normalized Architect output becomes a strict CE input package.

It prevents CE from receiving conceptual prose and having to guess executable structure. It also prevents Architect output from being mistaken for Builder-ready execution data.

## Boundary

Accepted input to CE must remain non-executable:

```yaml
accepted_for_ce_review: true
builder_executable_allowed: false
builder_ready_status: not_builder_ready_without_ce_proof
production_ready_allowed: false
```

CE may produce a Builder Executable Package only after constructability review proves all required strategy details and Builder has zero remaining strategy decisions.

## Required schema

Use:

```text
schemas/architect_ce_input_package.v1.schema.json
```

The schema is strict:

- `additionalProperties: false`
- all review units are explicit
- all proof states are explicit
- unmapped fields are forbidden
- semantic guessing is forbidden
- Builder package emission is forbidden at ingestion time

## Mapping rules Architect → CE

| Source | Target | Mapping rule | Failure condition |
|---|---|---|---|
| `schema` | `source_architect_schema` | require `ev4-architect-output-contract@1.0.0` | reject other schemas |
| `selected_candidate_id` | `selected_candidate_id` and `architect_contract.selected_candidate_id` | copy exact | reject if changed or empty |
| `selected_candidate_locked` | `selected_candidate_locked` | require `true` | reject if false/missing |
| `approved_structure_tree[]` | `approved_structure_tree[]` | copy normalized nodes | reject if node IDs are missing |
| `approved_class_names[]` | `approved_class_names[]` and `architect_contract.approved_class_names[]` | copy exact unique list | reject duplicates or unresolved names |
| `ce_review_units[]` | `ce_review_units[]` | copy exact | reject if any executable node has no review unit |
| `evidence_gaps_for_ce[]` | `ce_review_units[].interrogation_inputs.*.state` | convert to `not_proven` or `blocked` | reject if proof is missing but not represented |
| `responsive_qa_seed` | `ce_review_units[].interrogation_inputs.responsive` | map without inference | reject if responsive behavior is implied but absent |
| Builder-ready fields | none | forbidden | reject if present |

## Proof-state mapping

CE ingestion must use explicit proof states:

```text
not_required
evidence_backed
not_proven
blocked
```

Missing evidence is never treated as false and never upgraded to proven.

Boundary states must use:

```text
preserved
not_proven
requires_architect_amendment
blocked
```

## Pre-ingestion validation checklist

A CE input package is acceptable only when all checks below are true:

```yaml
architect_schema_valid: true
no_additional_properties: true
no_builder_ready_claim: true
selected_candidate_locked: true
approved_class_names_resolved: true
all_review_units_mapped: true
unmapped_fields: []
```

## CE no-guessing rule

CE must not infer or invent:

```text
geometry
source_target_anchors
asset source
placeholder policy
overlay strategy
containment
z-index
responsive behavior
interaction
Dynamic Loop
accessibility evidence
Elementor UI control path
class boundary changes
structure boundary changes
```

If any of these are required but not proven, CE must use one of:

```text
blocked
needs_user_evidence
needs_architect_amendment
```

## Builder package gate

At ingestion time:

```yaml
builder_package_emission_allowed_at_ingestion: false
semantic_guessing_allowed: false
ambiguous_fields_allowed: false
```

A Builder Executable Package may appear only after CE review satisfies the existing package-mode requirements: `constructability_status: executable_ready`, `builder_decisions_required: 0`, and `blocking_dependencies: []`.
