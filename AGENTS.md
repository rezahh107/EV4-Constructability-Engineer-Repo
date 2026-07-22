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

## Temporary Shared UX/UI Policy

For constructability work involving UX/UI obligations, read and silently apply:

```text
policies/EV4_TEMP_CROSS_REPO_UX_UI_STANDARDS_POLICY_r001.md
```

Pinned identity:

```yaml
policy_id: EV4-TEMP-CROSS-REPO-UX-UI-STANDARDS-POLICY-r001
revision: r001
sha256: fd023d9b815b6d525539d595700a1768245ae83cca401c71fb61ba22d4f76483
git_blob_sha: b52182c54577189d1b7832199fb699ee67f7d7fb
```

Apply only materially applicable Rule IDs. Verify that the locked Architect intent can express every applicable `HARD_GATE` and `REQUIRED_DEFAULT` without redesign, and convert runtime-only outcomes into explicit Builder or Responsive test obligations.

Do not weaken a Rule ID because implementation is inconvenient, promote editor or saved-state evidence to runtime proof, or treat `HEURISTIC` and `PREFERRED_DEFAULT` rules as automatic Builder-readiness blockers. Do not add unsupported fields or wrapper Artifacts solely to carry this policy.

This temporary policy is supplemental and becomes historical only after an explicitly adopted, pinned Kernel replacement exists.
