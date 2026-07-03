# Architect Stage Payload to CE Intake Mapping v1

Status: declarative_mapping_contract_v1  
Mapping identity: `ev4-architect-stage-to-ce-intake-mapping@1.0.0`  
Source schema: `ev4-architect-stage-payload@1.0.0`  
Target schema: `ev4-ce-architect-stage-intake@1.0.0`  
Owner: `rezahh107/EV4-Constructability-Engineer-Repo`

## Purpose

This mapping contract defines what a future Project Gate implementation may transform from Architect Stage Payload v1 into CE Architect Stage Intake v1.

It is declarative only. It does not implement Project Gate, perform constructability review, create CE proof states, or authorize Builder work.

## Classification vocabulary

Every target field is classified as exactly one of:

```text
direct_evidence_copy
allowed_representation_conversion
deterministic_structural_projection
not_applicable
unsupported
```

No `semantic_derivation` is used in this v1 mapping. CE semantic derivations are intentionally excluded from intake generation.

## Mapping table

| source path | target path | classification | ordering rule | missing source behavior | duplicate behavior | unsupported-field behavior | provenance behavior | unresolved-evidence behavior |
|---|---|---|---|---|---|---|---|---|
| `$.schema_id` | `$.source_contract.schema_id` | direct_evidence_copy | not_applicable | invalid | not_applicable | not_applicable | copy_exact | not_applicable |
| `$.schema_version` | `$.source_contract.schema_version` | direct_evidence_copy | not_applicable | invalid | not_applicable | not_applicable | copy_exact | not_applicable |
| `$.owner_repository` | `$.source_contract.owner_repository` | direct_evidence_copy | not_applicable | invalid | not_applicable | not_applicable | copy_exact | not_applicable |
| `$.architecture_identity.selected_candidate_id` | `$.selected_architecture.selected_candidate_id` | direct_evidence_copy | not_applicable | invalid | reject | not_applicable | preserve_reference | not_applicable |
| `$.architecture_identity.selected_candidate_locked` | `$.selected_architecture.selected_candidate_locked` | direct_evidence_copy | not_applicable | invalid | reject | not_applicable | preserve_reference | not_applicable |
| `$.architecture_identity.architecture_family` | `$.selected_architecture.architecture_family` | direct_evidence_copy | not_applicable | invalid | reject | not_applicable | preserve_reference | not_applicable |
| `$.architecture_identity.decision_source.*refs` | `$.selected_architecture.decision_source_refs` | deterministic_structural_projection | sort_by_id | invalid | reject | reject | preserve_reference | not_applicable |
| `$.approved_structure_model.structure_nodes[]` | `$.structure_projection.nodes[]` | deterministic_structural_projection | sort_by_id | invalid | reject | reject | preserve_reference | not_applicable |
| `$.architect_intent.class_intent` | `$.architect_intent_preserved.class_intent` | direct_evidence_copy | preserve_source_order | invalid | reject | reject | preserve_reference | not_applicable |
| `$.architect_intent.responsive_risk_seeds[]` | `$.architect_intent_preserved.responsive_risk_seeds[]` | direct_evidence_copy | preserve_source_order | insufficient_evidence | reject | not_applicable | preserve_reference | preserve_unresolved |
| `$.architect_intent.dynamic_loop_intent` | `$.architect_intent_preserved.dynamic_loop_intent` | direct_evidence_copy | not_applicable | invalid | reject | reject | preserve_reference | not_applicable |
| `$.evidence_register[]` | `$.evidence_register[]` | direct_evidence_copy | preserve_source_order | invalid | reject | not_applicable | copy_exact | not_applicable |
| `$.unresolved_evidence[]` | `$.unresolved_evidence[]` | direct_evidence_copy | preserve_source_order | omit_if_optional | reject | not_applicable | copy_exact | copy_exact |
| `$.forbidden_work[]` | `$.forbidden_work[]` | direct_evidence_copy | preserve_source_order | invalid | reject | not_applicable | copy_exact | not_applicable |
| `$.boundary_assertions` | `$.negative_boundary_assertions` | allowed_representation_conversion | sort_by_source_path_then_target_path | invalid | reject | reject | preserve_reference | not_applicable |
| CE review/proof/action fields | None | unsupported | not_applicable | not_applicable | not_applicable | reject | not_applicable | not_applicable |
| Builder executable/runtime fields | None | unsupported | not_applicable | not_applicable | not_applicable | reject | not_applicable | not_applicable |

## Rules

1. Missing required identity or evidence paths are invalid.
2. Missing unresolved evidence that blocks CE transition is `insufficient_evidence`.
3. Unsupported fields must be rejected or retained only as provenance if explicitly allowed by this contract.
4. Evidence states must be copied exactly; no mapping may upgrade `proposed`, `unverified`, or `insufficient_evidence`.
5. Structural projections must define deterministic ordering.
6. Duplicate identity, evidence, class, node, or mapping records are rejected unless a rule explicitly says otherwise.
7. The mapping does not output CE proof states, CE review units, implementation strategy, Builder action authorization, or production readiness.

## Real fixture policy

```yaml
real_cross_repository_validation: not_available
```
