# EV4 Constructability Engineer Repo

Mutable status authority: `STATUS.md`

Role: `implementation_strategy_gate`

## Purpose

EV4 Constructability Engineer sits between Architect and Builder.

```text
Architect says what should be built.
CE proves how it can be built without hidden Builder decisions.
Builder executes the proven strategy.
```

Core rule:

```text
not proven executable → not Builder-ready
```

## Lean Personal Runtime

This repository is operated by one owner. Runtime correctness remains strict, but enterprise-style authorization and attestation are not CE execution gates.

Two concerns are separated:

### Repository maintenance

Machine-readable mode identifier: `repository_maintenance`.

Includes code, contracts, schemas, fixtures, tests, CI, PRs, and documentation.

Keep normal automated validation. Maintenance evidence does not authorize or block a normal CE project run.

### CE runtime

```text
CE Input
→ Schema Validation
→ Semantic Validation
→ Constructability Review
→ Implementation Strategy
→ Builder Eligibility Check
→ Deterministic Export
```

Runtime states:

```text
INTAKE_VALIDATING
→ REVIEW_ACTIVE
→ STRATEGY_READY
→ EXPORT_VALIDATING
→ COMPLETED
```

`EVIDENCE_REQUIRED` is used only when a concrete correctness question remains unresolved.

## Runtime Intake

Canonical Architect-facing CE input:

```text
ev4-ce-architect-stage-intake@1.1.0
```

Accepted upstream source:

```text
ev4-architect-stage-payload@1.0.0
```

Mapping contract:

```text
ev4-architect-stage-to-ce-intake-mapping@1.1.0
```

Behavior:

- sending `شروع` first is optional;
- `active_ce_run` is not an authorization gate;
- a valid CE input can start intake directly;
- schema and semantic validation remain mandatory;
- multiple valid CE inputs block as ambiguous;
- extra irrelevant, Receipt-like, malformed, legacy, or wrong-stage files produce a warning when one valid CE input exists;
- a source bundle is requested only when needed to establish correctness;
- supplied relevant source evidence is verified before it is relied upon;
- invalid or insufficient CE input remains fail-closed.

## Builder-ready Integrity

Builder-ready remains impossible unless all of these are true:

```text
builder_executable_package.schema is ev4-builder-executable-package@1.0.0
selected_candidate_id remains locked
approved architecture and class intent remain preserved
blocking dependencies are empty
builder_decisions_required is zero
implementation strategy is explicit and complete
first safe Builder batch is present
required structured confirmation data is present
```

CE does not claim production readiness.

## Deterministic Export

CE owns the producer-emitted Project Gate artifact path:

```text
CE Stage Payload
inside Stage Evidence Bundle v1
inside Producer Gate Export v1
```

Key artifacts:

```text
manifests/ce_pipeline_manifest.v1.json
schemas/ce_pipeline_manifest.v1.schema.json
schemas/ce_stage_payload.v1.schema.json
contracts/project-gate/producer-gate-export.v1.schema.json
validator/project_gate_export.py
scripts/validate-project-gate-producer-adoption.py
```

Export protections remain:

- deterministic serialization;
- schema-valid output;
- source and artifact consistency checks;
- atomic writes;
- invalid-artifact publication blocking;
- no silent fallback;
- blocked output is never Builder authorization.

## Boundaries

CE does not:

- redesign architecture;
- rescore candidates;
- change `selected_candidate_id`;
- act as Builder;
- hide unknowns or blocking dependencies;
- claim real Elementor validation, responsive completion, deployment, or production readiness without evidence.

## Quick Start

1. Load `release/EV4_CE_PROJECT_RELEASE_PACK_v1/PROJECT_INSTRUCTIONS.md`.
2. Send the valid `ce-input.json`; `شروع` is optional.
3. Add a source bundle only after CE reports a specific blocking evidence need.
4. Treat extra files as warnings unless they create multiple valid CE inputs or contradict relevant evidence.
5. Continue until the implementation strategy and Builder eligibility checks pass.
6. Export through the deterministic CE Project Gate path.

Controlled quick-start contract:

1. Load `release/EV4_CE_PROJECT_RELEASE_PACK_v1/PROJECT_INSTRUCTIONS.md`.
2. Send the valid `ce-input.json`; sending `شروع` first is optional.
3. Add a source bundle only when CE reports a concrete evidence requirement.
4. Extra unrelated files are warnings, not runtime blockers.
5. CE blocks only invalid/insufficient CE input, multiple valid CE inputs, or relevant evidence that contradicts the selected input.
6. Builder-ready remains impossible while dependencies, strategy decisions, required fields, or validation errors remain.

## Validation

```bash
python -m pip install -e '.[dev]'
python scripts/check-ce-bootstrap.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_bootstrap_semantics.py
python scripts/validate-ce-architect-stage-intake.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_architect_stage_intake.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_strategy_batch_gates.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_builder_producer_contract.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_project_gate_exporter.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_validation_transaction.py
python scripts/validate-behavioral-rule-coverage.py
python scripts/validate-role-alignment-fixtures.py
npm run test:reference-paradigm-lock
```

## Companion Repositories

```text
rezahh107/EV4-Project-Gate
rezahh107/EV4-Architect-Repo
rezahh107/EV4-Builder-Assistant-Repo
rezahh107/EV4-Responsive-Architect
```
