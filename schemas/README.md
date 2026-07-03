# Schemas

The MVP has three Builder/constructability contracts:

- constructability_review.schema.json
- implementation_strategy_map.schema.json
- builder_executable_package.schema.json

The canonical Project Gate-produced Architect-facing CE intake contract is:

```text
ce_architect_stage_intake.v1_1.schema.json
schema_id: ev4-ce-architect-stage-intake@1.1.0
accepted source: ev4-architect-stage-payload@1.0.0
transition: ev4-architect-to-ce-transition@1.0.0
```

Historical compatibility-only Architect Stage intake schema:

```text
ce_architect_stage_intake.v1.schema.json
schema_id: ev4-ce-architect-stage-intake@1.0.0
```

Do not reinterpret v1.0.0; it remains frozen and records `project_gate_transition_implemented: false`.

Legacy compatibility-only Architect intake schema:

```text
architect_ce_input_package.v1.schema.json
```

The legacy schema targets `ev4-architect-output-contract@1.0.0` and must not be treated as the preferred target for new Project Gate transitions from Architect Stage Payload v1.

The Builder package schema is intentionally strict. It uses hard gates such as const values and empty blocking dependencies for executable-ready output.

For visual-reference packages, `builder_executable_package.schema.json` intentionally keeps CE-side `paradigm_to_structure_map.connector_layer` structured as an object with `node` and `model`. The Builder-side compact `node:model` string is a downstream adapter projection, not a CE schema output shape.
