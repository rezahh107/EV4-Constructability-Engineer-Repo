# EV4 Constructability Engineer Repo

Status: constructability system active; Project Gate integration planned; Project Gate program not implemented.

Role: `implementation_strategy_gate`

## Purpose

EV4 Constructability Engineer sits between Architect and Builder. It determines whether approved architecture can be implemented safely without forcing Builder to guess.

```text
Architect says what should be built.
CE proves how it can be safely built.
Builder executes proven strategy.
Responsive validates post-build responsive behavior.
```

Core rule:

```text
not proven executable → not builder-ready
```

## EV4 Project Gate Workflow

CE participates in two planned gates:

```text
Architect output
→ EV4 Project Gate
→ accepted CE Input Package
→ CE review and output
→ EV4 Project Gate
→ accepted Builder Input Package
```

If Architect input fails the first gate, the user receives an Architect repair package. If CE output fails the second gate, the user receives a CE repair package or an Architect amendment package only when evidence establishes upstream ownership.

The Python verifier and simple user interface are not implemented yet.

## Canonical Architect-facing CE intake

For new Architect Stage Payload work, the canonical CE-owned Architect-facing intake is:

```text
ev4-ce-architect-stage-intake@1.0.0
```

Accepted upstream source:

```text
ev4-architect-stage-payload@1.0.0
```

Declarative mapping contract:

```text
ev4-architect-stage-to-ce-intake-mapping@1.0.0
```

This intake contains Architect evidence, deterministic projections, provenance, unresolved evidence, and negative downstream-readiness assertions only. It does not contain CE review conclusions, implementation strategy, proof-state conclusions, Builder authorization, or production readiness.

Legacy compatibility-only intake files remain available:

```text
contracts/ARCHITECT_TO_CE_INPUT_MAPPING_V1.md
schemas/architect_ce_input_package.v1.schema.json
```

Those files target the previous `ev4-architect-output-contract@1.0.0` / `/builder-feed-export` path and must not be treated as the preferred intake for new Project Gate transitions.

The Project Gate Architect-to-CE transition is not implemented by this repository change.

## CE Input and Output

CE receives only an Architect package accepted for constructability review.

CE output may become Builder-ready only when implementation strategy is proven and Builder has no remaining strategy decisions.

Expected Builder-ready conditions include:

```text
builder_executable_package.schema is ev4-builder-executable-package@1.0.0
selected_candidate_id remains locked
approved class intent remains preserved
blocking dependencies are empty
builder_decisions_required is zero
implementation strategy is explicit
first safe Builder batch is present
structured confirmation data is present
production readiness remains false
```

For visual-reference Builder packages, CE must keep reference carriers structured. In particular, `paradigm_to_structure_map.connector_layer` remains `{node, model}` in CE output; the downstream CE→Builder adapter owns any Builder-side `node:model` projection. See `docs/CE_TO_BUILDER_PRODUCER_CONTRACT.md`.

Typical CE concerns include geometry, source and target anchors, assets, overlays, z-index, responsive scope, interaction, Dynamic Loop, accessibility evidence, and exact Elementor UI-control evidence.

## Authority

This repository remains authoritative for its own constructability schemas, validators, fixtures, failure patterns, strategy rules, and Builder-ready package semantics.

EV4 Project Gate verifies the real CE-to-Builder path using official CE validation, the documented adapter, Builder intake validation, and preservation checks. It does not redesign architecture, invent strategy, replace CE contracts, or silently repair CE output.

When responsibility cannot be established:

```yaml
status: insufficient_evidence
repair_owner: unresolved
```

## Repair Loop

A future CE repair package will explain the confirmed problem in plain Persian, identify affected contract data, retain the original output identity, and state what valid data must remain unchanged. The corrected complete CE output is checked again before Builder receives it.

## CE Status Values

```text
executable_ready
blocked
needs_user_evidence
needs_architect_amendment
executable_with_logged_assumption
```

`executable_with_logged_assumption` is limited to explicit, low-risk, reversible, boundary-safe assumptions that leave no Builder strategy decision.

## Boundaries

CE does not redesign architecture, rescore candidates, change `selected_candidate_id`, act as Builder, or claim production readiness.

## Companion Repositories

```text
https://github.com/rezahh107/EV4-Project-Gate
https://github.com/rezahh107/EV4-Architect-Repo
https://github.com/rezahh107/EV4-Builder-Assistant-Repo
https://github.com/rezahh107/EV4-Responsive-Architect
```

## Status

```yaml
role: implementation_strategy_gate
fail_closed_default: true
project_gate_handoff: documented
project_gate_runtime: not_implemented
canonical_architect_facing_intake: ev4-ce-architect-stage-intake@1.0.0
architect_stage_to_ce_mapping: ev4-architect-stage-to-ce-intake-mapping@1.0.0
builder_package_emission: evidence_gated
builder_executable_package_schema: ev4-builder-executable-package@1.0.0_required
production_ready: false
```
