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
Architect Intake
+ Lean CE Review Draft
→ Claim-specific Proof Policy
→ CE-owned Evidence Adapters
→ Proof Resolver
→ Verified CE Stage Payload
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

## Lean CE Review Draft

The model- or human-facing review input is:

```text
ev4-ce-review-draft@1.0.0
```

It contains engineering analysis only:

- `proposed_action`;
- `engineering_rationale`;
- `requested_claims`;
- `candidate_source_refs`;
- `assumptions` and `limitations`;
- implementation strategy proposals;
- Builder action proposals;
- unresolved questions and downstream test obligations.

The Draft must not manufacture proof hashes, verification states, producer identities, run IDs, proven Booleans, constructability status, Builder eligibility, or handoff authorization. Candidate references remain non-authoritative until an official CE adapter resolves and verifies them.

## Verified Constructability Authority

The canonical claim registry is `validator/claim_policy_registry.py`. It separates:

- `VERIFIED_ARTIFACT`;
- `VERIFIED_TOOL_EXECUTION`;
- `VERIFIED_ARCHITECT_DECISION`;
- `ATTRIBUTED_ENGINEERING_JUDGMENT`;
- `DOWNSTREAM_TEST_OBLIGATION`.

Important distinctions:

```text
attributed engineering judgment != verified source fact
source integrity != claim correctness
runtime-only claim != editor configuration assertion
non-empty proof object != proven claim
```

The CE runtime mints exact-type immutable capabilities. Plain dictionaries, subclasses, copied state, test-only capabilities, stale source bindings, wrong subjects, wrong Payloads, wrong intake identities, and wrong selected candidates cannot authorize the official export.

Runtime-only responsive, accessibility, and QA claims require `VERIFIED_TOOL_EXECUTION`. When execution evidence is unavailable, the resolver emits `DOWNSTREAM_TEST_OBLIGATION`; it does not convert editor descriptions or saved-state assertions into runtime proof.

Architect-owned interaction and dynamic-loop decisions require `VERIFIED_ARCHITECT_DECISION`. CE judgment cannot self-approve them.

## Builder-ready Integrity

Builder-ready remains impossible unless all of these are true:

```text
verified successor Payload is present
all requested claims have policy-compatible resolved evidence
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
Verified CE Stage Payload v1.1
inside Stage Evidence Bundle v1
inside Producer Gate Export v1
```

Key artifacts:

```text
schemas/ce_review_draft.v1.schema.json
schemas/constructability_review.v1_1.schema.json
schemas/ce_stage_payload.v1_1.schema.json
validator/claim_policy_registry.py
validator/verified_constructability.py
validator/verified_project_gate_exporter.py
contracts/project-gate/producer-gate-export.v1.schema.json
scripts/report-ce-model-trust-field-reduction.py
```

Official command:

```bash
ev4-ce-project-gate-export \
  --review-draft <ce-review-draft.json> \
  --source-intake <architect-intake.json> \
  --source-bundle <architect-source-bundle.json> \
  --output <ce-project-gate.json>
```

Historical `ev4-ce-stage-payload@1.0.0` artifacts remain schema- and semantic-diagnosable. Their export path is explicitly:

```yaml
assurance_kind: DECLARATION
verification_status: MANUAL_UNVERIFIED
official_builder_authorization: false
```

A raw legacy Payload cannot produce `handoff.allowed=true`.

Export protections remain:

- deterministic serialization;
- Schema-valid output;
- exact source and artifact binding;
- source-intake and source-bundle snapshot checks;
- Git provenance collection;
- synthetic-evidence blocking;
- atomic writes;
- persisted-byte validation;
- transaction authorization recomputation;
- no silent fallback;
- blocked output is never Builder authorization.

## Boundaries

CE does not:

- redesign architecture;
- rescore candidates;
- change `selected_candidate_id`;
- self-approve Architect-owned decisions;
- act as Builder;
- hide unknowns or blocking dependencies;
- claim real Elementor validation, responsive completion, accessibility completion, deployment, or production readiness without compatible evidence.

## Quick Start

1. Load `release/EV4_CE_PROJECT_RELEASE_PACK_v1/PROJECT_INSTRUCTIONS.md`.
2. Supply the valid Architect intake and exact source bundle.
3. Produce an `ev4-ce-review-draft@1.0.0` containing analysis, requested claims, candidate source references, limitations, and proposals only.
4. Let the official CE adapters verify sources and mint proof capabilities.
5. Resolve unavailable runtime evidence as downstream test obligations.
6. Export only through `ev4-ce-project-gate-export` and the verified successor Payload.

Controlled quick-start contract:

1. Sending `شروع` first remains optional.
2. Extra unrelated files are warnings, not runtime blockers.
3. CE blocks invalid/insufficient inputs, ambiguous canonical inputs, contradictory relevant evidence, provenance mismatch, or unresolved authority-bearing claims.
4. Builder-ready remains impossible while dependencies, strategy decisions, required evidence, or validation errors remain.
5. Legacy raw Payloads may be inspected or previewed but never authorize Builder handoff.

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
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_authority_mutation_harness.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_verified_constructability_runtime.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_claim_policy_and_model_reduction.py
python scripts/report-ce-model-trust-field-reduction.py
python scripts/validate-behavioral-rule-coverage.py
python scripts/validate-role-alignment-fixtures.py
npm run test:reference-paradigm-lock
pytest -q
ruff check .
```

## Companion Repositories

```text
rezahh107/EV4-Project-Gate
rezahh107/EV4-Architect-Repo
rezahh107/EV4-Builder-Assistant-Repo
rezahh107/EV4-Responsive-Architect
```
