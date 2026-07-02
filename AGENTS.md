# AGENTS.md

## Scope

These instructions apply to the entire repository unless a closer nested `AGENTS.md` or `AGENTS.override.md` provides more specific guidance.

## Repository Role

`EV4-Constructability-Engineer-Repo` is the implementation-strategy gate between Architect and Builder.

It receives an approved architecture handoff, identifies hidden execution dependencies, proves or blocks implementation strategy, preserves locked architecture identity, and emits a Builder-ready package only when Builder has no remaining strategy decision.

## Read First

1. `README.md`
2. `STATUS.md`, when present
3. `docs/PROTOCOL.md`
4. `docs/ROLE_BOUNDARIES.md`
5. the relevant schema, validator, rule, fixture, and test files

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

## Hard Boundaries

Do not:

- redesign or rescore the approved architecture;
- change `selected_candidate_id` or approved class intent;
- act as Builder;
- emit Builder instructions while Builder decisions remain;
- treat silence as proof of geometry, asset, overlay, interaction, responsive, Dynamic Loop, accessibility, or UI-control readiness;
- claim production readiness;
- copy CE schemas into Project Gate as competing canonical contracts.

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
