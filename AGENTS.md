# AGENTS.md

## Scope

These instructions apply to the entire repository unless a closer nested `AGENTS.md` or `AGENTS.override.md` provides more specific guidance.

## Repository Role

`EV4-Constructability-Engineer-Repo` is the implementation-strategy gate between Architect and Builder.

It receives an approved architecture handoff, identifies hidden execution dependencies, proves or blocks implementation strategy, preserves locked architecture identity, and emits a Builder-ready package only when Builder has no remaining strategy decision.

For new Project Gate work, its canonical Architect-facing intake is `ev4-ce-architect-stage-intake@1.0.0`.

## Read First

1. `README.md`
2. `STATUS.md`, when present
3. `contracts/CE_ARCHITECT_STAGE_INTAKE_V1.md`
4. `contracts/ARCHITECT_STAGE_TO_CE_INTAKE_MAPPING_V1.md`
5. `schemas/ce_architect_stage_intake.v1.schema.json`
6. `scripts/validate-ce-architect-stage-intake.py`
7. `docs/PROTOCOL.md`
8. `docs/ROLE_BOUNDARIES.md`
9. the relevant schema, validator, rule, fixture, and test files

Follow the current owning contract and validated fixtures over proposals or historical notes.

## Project Gate Position

```text
Architect package
→ CE review and output
→ EV4 Project Gate
→ accepted: Builder Input Package
→ not accepted: CE repair or evidenced upstream amendment
```

Project Gate integration is documented but the verifier and user interface are not implemented yet.

Project Gate may execute this repository's official validators and the documented downstream adapter. It must not invent implementation strategy or replace CE contracts.

For the Architect → CE boundary, Project Gate must not create CE-owned conclusions. The CE intake package may preserve Architect evidence and deterministic projections only.

## Canonical Architect Intake

Canonical new intake:

```text
ev4-ce-architect-stage-intake@1.0.0
```

Accepted source:

```text
ev4-architect-stage-payload@1.0.0
```

Mapping contract:

```text
ev4-architect-stage-to-ce-intake-mapping@1.0.0
```

Legacy compatibility-only files:

```text
contracts/ARCHITECT_TO_CE_INPUT_MAPPING_V1.md
schemas/architect_ce_input_package.v1.schema.json
```

Do not use the legacy Architect output contract as the preferred target for new Architect Stage Payload transitions.

## Hard Boundaries

Do not:

- redesign or rescore the approved architecture;
- change `selected_candidate_id` or approved class intent;
- act as Builder;
- emit Builder instructions while Builder decisions remain;
- treat silence as proof of geometry, asset, overlay, interaction, responsive, Dynamic Loop, accessibility, or UI-control readiness;
- claim production readiness;
- copy CE schemas into Project Gate as competing canonical contracts;
- require Project Gate to invent `ce_review_units[].action_proposed`, proof-state conclusions, identity consistency verdicts, pre-ingestion verdicts, implementation strategy, or Builder authorization at intake.

Default behavior is fail-closed:

```text
not proven executable → not builder-ready
```

## Change Rules

For changes affecting Builder intake:

- preserve public contract behavior unless a breaking change is explicitly approved;
- update schemas, validators, rules, fixtures, tests, and docs together;
- preserve locked architecture identity and valid evidence;
- add malformed, boundary, and regression cases for changed behavior;
- document compatibility and versioning impact;
- avoid unrelated refactoring;
- do not weaken a confirmed regression fixture without an explicit decision record.

## Validation

Use the repository's current validation sequence:

```bash
python -m pip install -e '.[dev]'
pytest -q
python scripts/validate-behavioral-rule-coverage.py
python scripts/validate-role-alignment-fixtures.py
npm run test:reference-paradigm-lock
```

For Architect Stage Intake changes, also run:

```bash
python scripts/validate-ce-architect-stage-intake.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_architect_stage_intake.py
```

Run the checks relevant to the change and report exactly which commands passed. Do not claim full validation if only a subset ran.

## Evidence and Determinism

Use explicit evidence states and retain source paths, fixture IDs, validator outputs, and rule IDs.

Synthetic fixtures must be labelled synthetic. A shape check is not equivalent to passing the official schema and behavioral validator.

When repair ownership cannot be established, use:

```yaml
status: insufficient_evidence
repair_owner: unresolved
```

## Pull Requests

A PR should state:

- the constructability problem or contract change;
- affected schemas, rules, fixtures, and downstream handoffs;
- compatibility impact;
- validation commands actually executed;
- remaining unverified behavior or missing evidence.
