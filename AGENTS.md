# AGENTS.md

## Scope

These instructions apply to the entire repository unless a closer `AGENTS.md` or `AGENTS.override.md` provides narrower guidance.

## Repository Role

`EV4-Constructability-Engineer-Repo` is the implementation-strategy gate between Architect and Builder.

```text
Architect defines approved intent.
CE proves an implementation strategy.
Builder executes only a strategy that leaves no Builder decision.
```

Core rule:

```text
not proven executable → not Builder-ready
```

## Read First

1. `README.md`
2. `STATUS.md`
3. `contracts/CE_ARCHITECT_STAGE_INTAKE_V1_1.md`
4. `contracts/ARCHITECT_STAGE_TO_CE_INTAKE_MAPPING_V1_1.md`
5. `schemas/ce_architect_stage_intake.v1_1.schema.json`
6. `scripts/validate-ce-architect-stage-intake.py`
7. `manifests/ce_pipeline_manifest.v1.json`
8. relevant schemas, validators, fixtures, tests, and export code

Current validated contracts and fixtures override historical notes.

## Operating Modes

### `repository_maintenance`

Use for repository inspection, code changes, tests, CI, schemas, documentation, contracts, PRs, and status reconciliation.

Allowed controls:

- normal CI;
- automated tests;
- schema and semantic validation tests;
- regression tests;
- deterministic export and atomic-write tests.

Repository-maintenance governance is not a CE runtime prerequisite.

### `ce_runtime`

Normal runtime flow:

```text
CE Input
→ Schema Validation
→ Semantic Validation
→ Constructability Review
→ Implementation Strategy
→ Builder Eligibility Check
→ Deterministic Export
```

The runtime state model is:

```text
INTAKE_VALIDATING
→ REVIEW_ACTIVE
→ STRATEGY_READY
→ EXPORT_VALIDATING
→ COMPLETED

EVIDENCE_REQUIRED is entered only when correctness cannot be established.
```

No runtime state requires PR creation, PR Inspector, independent review, external Receipt, exact-head evidence, governance bundle, or GitHub workflow evidence.

## Runtime Intake Policy

Canonical CE input:

```text
ev4-ce-architect-stage-intake@1.1.0
```

Rules:

- `شروع` is an optional conversation shortcut, not an authorization gate.
- `active_ce_run` is accepted for compatibility but is not an authorization gate.
- a valid CE input may start runtime intake directly;
- filenames are hints, never authority;
- multiple valid CE inputs block automatic selection;
- invalid, legacy, Receipt-like, wrong-stage, malformed, or unrelated extra files are warnings when one valid canonical CE input exists;
- invalid or semantically insufficient canonical CE input remains fail-closed;
- source bundle evidence is required only when a concrete correctness question cannot be resolved from the canonical input;
- when relevant source evidence is supplied and relied upon, its exact bytes, identity, hash, transition, and provenance must be verified;
- Receipt-like files are diagnostic and non-semantic.

## Correctness Controls That Must Remain

### Input and identity

- JSON/schema validation;
- semantic validation;
- `selected_candidate_id` consistency;
- approved architecture intent preservation;
- protected class/build-tree identity;
- explicit unknown tracking.

### Constructability and strategy

- hidden dependency tracking;
- blocking dependency tracking;
- implementation strategy completeness;
- no silent architecture redesign;
- no Builder decision hidden inside batch parameters.

### Builder-ready

Builder-ready is forbidden when any of these remain:

- blocking dependencies;
- unresolved strategic decisions;
- incomplete implementation strategy;
- missing required fields;
- invalid package schema;
- candidate or architecture identity mismatch.

### Export

Keep:

- deterministic serialization;
- schema-valid artifacts;
- artifact consistency checks;
- atomic writes;
- input/output alias protection;
- invalid-artifact publication blocking;
- regression coverage.

## Hard Boundaries

Do not:

- redesign or rescore approved architecture;
- change `selected_candidate_id`;
- remove unknowns silently;
- emit Builder instructions while Builder decisions remain;
- claim real Elementor, responsive, deployment, or production readiness without evidence;
- treat Receipt prose as semantic input;
- replace deterministic validation with manual assumptions.

## Validation

Baseline:

```bash
python -m pip install -e '.[dev]'
pytest -q
python scripts/validate-behavioral-rule-coverage.py
python scripts/validate-role-alignment-fixtures.py
npm run test:reference-paradigm-lock
```

Runtime intake:

```bash
python scripts/check-ce-bootstrap.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_bootstrap_semantics.py
python scripts/validate-ce-architect-stage-intake.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_architect_stage_intake.py
```

Exporter and Builder eligibility:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_strategy_batch_gates.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_builder_producer_contract.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_project_gate_exporter.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_validation_transaction.py
```

Report only commands actually executed.

## Pull Requests

For changes affecting runtime, schemas, Builder intake, or export, state:

- root cause;
- behavior before and after;
- affected contracts and compatibility;
- tests actually executed;
- remaining limitations.

Use focused branches and avoid unrelated refactoring.

## Temporary Shared UX/UI Policy Adapter

Use `policies/EV4_TEMP_CROSS_REPO_UX_UI_STANDARDS_POLICY_r002.md` only as a supplemental policy below repository authority.

```yaml
policy_id: EV4-TEMP-CROSS-REPO-UX-UI-STANDARDS-POLICY-r002
revision: r002
filename: EV4_TEMP_CROSS_REPO_UX_UI_STANDARDS_POLICY_r002.md
sha256: f09b6978e10833c1ab3c3e35a9128db894684c5ed9cd876fa87699016b6def95
repository_role: constructability_engineer
local_consumption_scope: constructability review, implementation strategy, Builder eligibility, and downstream test transfer
role_must:
  - prove a feasible strategy for applicable hard gates and required defaults
  - preserve locked architecture
  - verify target-project capability when strategy depends on it
  - transfer runtime-only outcomes as explicit tests
role_must_not:
  - redesign for implementation convenience
  - silently downgrade a hard gate
  - claim runtime proof from editor or saved-state evidence
```

Keep nonmaterial routing internal. Represent material failures, exceptions, unresolved requirements, evidence gaps, and downstream obligations through existing repository-supported fields or a concise visible status when continuation or owner action is affected. Do not add unsupported fields or hidden-storage claims.

`r001` remains an immutable historical revision. A filename, ID, revision, byte, or digest mismatch is `TEMP_UX_UI_POLICY_IDENTITY_MISMATCH`. This adapter does not create Kernel adoption, a new runtime state, or a parallel approval path.
