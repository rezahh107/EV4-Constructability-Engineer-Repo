# Architect Stage to CE Intake Mapping v1.1

Status: declarative_mapping_contract_v1_1  
Mapping identity: `ev4-architect-stage-to-ce-intake-mapping@1.1.0`  
Source schema: `ev4-architect-stage-payload@1.0.0`  
Target schema: `ev4-ce-architect-stage-intake@1.1.0`  
Owner: `rezahh107/EV4-Constructability-Engineer-Repo`

## Purpose

This mapping contract preserves v1.0 evidence mapping behavior and adds the transition execution record needed when the intake is produced by Project Gate.

The mapping is declarative. It does not implement Project Gate, perform CE review, create proof states, select implementation strategy, or authorize Builder work.

## Added v1.1 mapping

| source path | target path | classification | rule |
|---|---|---|---|
| source Stage Evidence Bundle `$.bundle_id` | `$.project_gate_transition.source_bundle_id` | direct_evidence_copy | CE-I15 |
| source Stage Evidence Bundle canonical hash | `$.project_gate_transition.source_bundle_hash` | allowed_representation_conversion | CE-I15 |
| transition implementation identity | `$.project_gate_transition.transition_id` | direct_evidence_copy | CE-I14 |
| Project Gate producer repository | `$.project_gate_transition.producer_repository` | direct_evidence_copy | CE-I14 |

## Preserved v1.0 mapping behavior

The following classifications remain allowed:

```text
direct_evidence_copy
allowed_representation_conversion
deterministic_structural_projection
not_applicable
unsupported
```

No semantic derivation is introduced in v1.1.

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
