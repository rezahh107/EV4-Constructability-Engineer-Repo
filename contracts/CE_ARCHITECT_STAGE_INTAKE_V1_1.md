# CE Architect Stage Intake v1.1

Status: canonical_new_architect_facing_intake  
Contract identity: `ev4-ce-architect-stage-intake@1.1.0`  
Owner: `rezahh107/EV4-Constructability-Engineer-Repo`  
Accepted source: `ev4-architect-stage-payload@1.0.0`

## Purpose

This contract corrects v1.0 so CE intake can truthfully represent a Project Gate-produced Architect-to-CE transition.

`ev4-ce-architect-stage-intake@1.0.0` remains unchanged as historical compatibility. It required `ce_processing_prerequisites.project_gate_transition_implemented: false`, so it cannot represent an already executed Project Gate transition without semantic contradiction.

v1.1 adds a required `project_gate_transition` record.

## Transition execution record

```yaml
project_gate_transition:
  executed: true
  transition_id: ev4-architect-to-ce-transition@1.0.0
  transition_version: 1.0.0
  producer_repository: rezahh107/EV4-Project-Gate
  source_bundle_id: <source Stage Evidence Bundle id>
  source_bundle_hash:
    algorithm: sha256
    canonicalization: ev4-canonical-json.v1
    scope: source_bundle
    value: <64 lowercase hex>
```

The record means only:

```text
Project Gate executed the Architect-to-CE transition for this specific intake.
```

It does not mean:

```text
constructability proven
CE approved
implementation strategy selected
Builder ready
Builder executable
production ready
real Elementor validation completed
```

## Mapping trace requirement

v1.1 mapping traces must use the complete self-contained mapping contract:

```text
ev4-architect-stage-to-ce-intake-mapping@1.1.0
```

The classification `deterministic_derived_metadata` is allowed only for deterministic Project Gate metadata. It requires a `derivation_rule` record and must not be used for CE semantic conclusions.

Required derivation rules:

```yaml
CE-MAP-A2C-01@1.0.0:
  outputs:
    - $.project_gate_transition.executed
    - $.project_gate_transition.transition_id
    - $.project_gate_transition.transition_version
    - $.project_gate_transition.producer_repository
CE-MAP-A2C-02@1.0.0:
  outputs:
    - $.project_gate_transition.source_bundle_hash
```

`$.project_gate_transition.source_bundle_id` remains a direct evidence copy from the source Stage Evidence Bundle id.

## Stable rule IDs added in v1.1

| rule_id | meaning |
|---|---|
| `CE-I13` | Project Gate-produced v1.1 intake must include transition execution metadata |
| `CE-I14` | transition identity, version, and producer repository must be exact |
| `CE-I15` | source bundle identity and hash must remain traceable |
| `CE-I16` | transition execution does not equal CE review execution |
| `CE-I17` | transition execution does not authorize Builder execution |
| `CE-I18` | real Elementor validation remains unavailable unless proven separately |
| `CE-I19` | incomplete transition provenance is invalid |
| `CE-I20` | insufficient evidence remains distinct from invalid input |
| `CE-I21` | mapping trace must completely describe Project Gate transition metadata |

Existing `CE-I01` through `CE-I12` keep their v1.0 meaning.

## Versioning

```yaml
preserved:
  - ev4-ce-architect-stage-intake@1.0.0
  - ev4-architect-stage-to-ce-intake-mapping@1.0.0
added:
  - ev4-ce-architect-stage-intake@1.1.0
  - ev4-architect-stage-to-ce-intake-mapping@1.1.0
```

## Real fixture policy

```yaml
real_cross_repository_validation: not_available
fixture_classification: synthetic
```

Synthetic transition fixtures prove contract behavior only. They do not prove real Elementor artifact compatibility.
