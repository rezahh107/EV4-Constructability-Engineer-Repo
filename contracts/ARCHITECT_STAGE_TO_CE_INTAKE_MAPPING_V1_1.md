# Architect Stage to CE Intake Mapping v1.1

Status: declarative_mapping_contract_v1_1  
Mapping identity: `ev4-architect-stage-to-ce-intake-mapping@1.1.0`  
Source schema: `ev4-architect-stage-payload@1.0.0`  
Target schema: `ev4-ce-architect-stage-intake@1.1.0`  
Owner: `rezahh107/EV4-Constructability-Engineer-Repo`

## Purpose

This is the complete authoritative v1.1 mapping contract for Project Gate-produced CE Architect Stage Intake v1.1.

It is self-contained. A Project Gate implementation must not infer inherited behavior by combining this file with v1.0 prose.

The mapping is declarative. It does not implement Project Gate, perform CE review, create proof states, select implementation strategy, or authorize Builder work.

## Classification vocabulary

Every mapping row is classified as exactly one of:

```text
direct_evidence_copy
allowed_representation_conversion
deterministic_structural_projection
deterministic_derived_metadata
not_applicable
unsupported
```

`deterministic_derived_metadata` means Project Gate deterministically emits transition metadata from transition execution, versioned transition configuration, canonical source bundle content, or Project Gate identity. It does not add CE domain meaning and is not a CE semantic conclusion.

No CE semantic derivation is introduced in v1.1.

## Stable derivation rules

### CE-MAP-A2C-01 — Project Gate transition execution metadata

Outputs:

```text
$.project_gate_transition.executed
$.project_gate_transition.transition_id
$.project_gate_transition.transition_version
$.project_gate_transition.producer_repository
```

Authorities:

```yaml
executed:
  value: true
  authority: only after this transition invocation actually executes
transition_id:
  value: ev4-architect-to-ce-transition@1.0.0
  authority: versioned transition configuration
transition_version:
  value: 1.0.0
  authority: versioned transition configuration
producer_repository:
  value: rezahh107/EV4-Project-Gate
  authority: Project Gate identity
```

These fields are not direct Architect evidence copies.

### CE-MAP-A2C-02 — Canonical source bundle SHA-256

Input:

```text
complete source Stage Evidence Bundle JSON object
```

Canonicalization:

```text
ev4-canonical-json.v1
```

Encoding:

```text
UTF-8
```

Algorithm:

```text
SHA-256
```

Output:

```yaml
algorithm: sha256
canonicalization: ev4-canonical-json.v1
scope: source_bundle
value: <64 lowercase hex>
```

Target:

```text
$.project_gate_transition.source_bundle_hash
```

This computation is not an allowed representation conversion.

## Complete v1.1 mapping table

| source authority/path | target path | classification | ordering rule | missing-source behavior | duplicate behavior | unsupported-field behavior | provenance behavior | unresolved-evidence behavior | rule ID/version when derived |
|---|---|---|---|---|---|---|---|---|---|
| `$.schema_id` | `$.source_contract.schema_id` | direct_evidence_copy | not_applicable | invalid | not_applicable | not_applicable | copy_exact | not_applicable | not_applicable |
| `$.schema_version` | `$.source_contract.schema_version` | direct_evidence_copy | not_applicable | invalid | not_applicable | not_applicable | copy_exact | not_applicable | not_applicable |
| `$.owner_repository` | `$.source_contract.owner_repository` | direct_evidence_copy | not_applicable | invalid | not_applicable | not_applicable | copy_exact | not_applicable | not_applicable |
| `$.architecture_identity.selected_candidate_id` | `$.selected_architecture.selected_candidate_id` | direct_evidence_copy | not_applicable | invalid | reject | not_applicable | preserve_reference | not_applicable | not_applicable |
| `$.architecture_identity.selected_candidate_locked` | `$.selected_architecture.selected_candidate_locked` | direct_evidence_copy | not_applicable | invalid | reject | not_applicable | preserve_reference | not_applicable | not_applicable |
| `$.architecture_identity.architecture_family` | `$.selected_architecture.architecture_family` | direct_evidence_copy | not_applicable | invalid | reject | not_applicable | preserve_reference | not_applicable | not_applicable |
| `$.architecture_identity.decision_source.*refs` | `$.selected_architecture.decision_source_refs` | deterministic_structural_projection | sort_by_id | invalid | reject | reject | preserve_reference | not_applicable | not_applicable |
| `$.approved_structure_model.structure_nodes[]` | `$.structure_projection.nodes[]` | deterministic_structural_projection | sort_by_id | invalid | reject | reject | preserve_reference | not_applicable | not_applicable |
| `$.architect_intent.class_intent` | `$.architect_intent_preserved.class_intent` | direct_evidence_copy | preserve_source_order | invalid | reject | reject | preserve_reference | not_applicable | not_applicable |
| `$.architect_intent.responsive_risk_seeds[]` | `$.architect_intent_preserved.responsive_risk_seeds[]` | direct_evidence_copy | preserve_source_order | insufficient_evidence | reject | not_applicable | preserve_reference | preserve_unresolved | not_applicable |
| `$.architect_intent.dynamic_loop_intent` | `$.architect_intent_preserved.dynamic_loop_intent` | direct_evidence_copy | not_applicable | invalid | reject | reject | preserve_reference | not_applicable | not_applicable |
| `$.evidence_register[]` | `$.evidence_register[]` | direct_evidence_copy | preserve_source_order | invalid | reject | not_applicable | copy_exact | not_applicable | not_applicable |
| `$.unresolved_evidence[]` | `$.unresolved_evidence[]` | direct_evidence_copy | preserve_source_order | omit_if_optional | reject | not_applicable | copy_exact | copy_exact | not_applicable |
| `$.forbidden_work[]` | `$.forbidden_work[]` | direct_evidence_copy | preserve_source_order | invalid | reject | not_applicable | copy_exact | not_applicable | not_applicable |
| `$.boundary_assertions` | `$.negative_boundary_assertions` | allowed_representation_conversion | sort_by_source_path_then_target_path | invalid | reject | reject | preserve_reference | not_applicable | not_applicable |
| transition invocation completion | `$.project_gate_transition.executed` | deterministic_derived_metadata | not_applicable | invalid | not_applicable | not_applicable | not_applicable | not_applicable | `CE-MAP-A2C-01@1.0.0` |
| versioned transition configuration | `$.project_gate_transition.transition_id` | deterministic_derived_metadata | not_applicable | invalid | not_applicable | not_applicable | not_applicable | not_applicable | `CE-MAP-A2C-01@1.0.0` |
| versioned transition configuration | `$.project_gate_transition.transition_version` | deterministic_derived_metadata | not_applicable | invalid | not_applicable | not_applicable | not_applicable | not_applicable | `CE-MAP-A2C-01@1.0.0` |
| Project Gate producer identity | `$.project_gate_transition.producer_repository` | deterministic_derived_metadata | not_applicable | invalid | not_applicable | not_applicable | not_applicable | not_applicable | `CE-MAP-A2C-01@1.0.0` |
| source Stage Evidence Bundle `$.bundle_id` | `$.project_gate_transition.source_bundle_id` | direct_evidence_copy | not_applicable | invalid | not_applicable | not_applicable | copy_exact | not_applicable | not_applicable |
| complete source Stage Evidence Bundle canonical JSON | `$.project_gate_transition.source_bundle_hash` | deterministic_derived_metadata | not_applicable | invalid | not_applicable | not_applicable | not_applicable | not_applicable | `CE-MAP-A2C-02@1.0.0` |
| CE review/proof/action fields | None | unsupported | not_applicable | not_applicable | not_applicable | reject | not_applicable | not_applicable | not_applicable |
| Builder executable/runtime fields | None | unsupported | not_applicable | not_applicable | not_applicable | reject | not_applicable | not_applicable | not_applicable |

## Trace coverage rule

`CE-I21` requires v1.1 payloads to include exactly one valid `mapping_trace[]` row for each Project Gate transition metadata target:

```text
$.project_gate_transition.executed
$.project_gate_transition.transition_id
$.project_gate_transition.transition_version
$.project_gate_transition.producer_repository
$.project_gate_transition.source_bundle_id
$.project_gate_transition.source_bundle_hash
```

Required classifications:

```yaml
$.project_gate_transition.source_bundle_id: direct_evidence_copy
$.project_gate_transition.executed: deterministic_derived_metadata
$.project_gate_transition.transition_id: deterministic_derived_metadata
$.project_gate_transition.transition_version: deterministic_derived_metadata
$.project_gate_transition.producer_repository: deterministic_derived_metadata
$.project_gate_transition.source_bundle_hash: deterministic_derived_metadata
```

Required derivation rules:

```yaml
CE-MAP-A2C-01@1.0.0:
  - $.project_gate_transition.executed
  - $.project_gate_transition.transition_id
  - $.project_gate_transition.transition_version
  - $.project_gate_transition.producer_repository
CE-MAP-A2C-02@1.0.0:
  - $.project_gate_transition.source_bundle_hash
```

## Forbidden outputs

The mapping must not emit:

```text
ce_review_units
action_proposed
proof_states
constructability_review
implementation_strategy_map
builder_executable_package
first_safe_builder_batch
confirmation_request
```

It must not emit positive CE or Builder readiness claims.

## Real fixture policy

```yaml
real_cross_repository_validation: not_available
fixture_classification: synthetic
```
