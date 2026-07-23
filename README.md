# EV4 Constructability Engineer Repo

Mutable status authority: `STATUS.md`

Role: `implementation_strategy_gate`

## Purpose

EV4 Constructability Engineer sits between Architect and Builder.

```text
Architect says what should be built.
CE establishes how it can be built without hidden Builder decisions.
Builder executes the evaluated strategy.
```

Core rule:

```text
not deterministically established executable → not Builder-ready
```

## Lean personal runtime

This repository is operated by one owner. Functional correctness remains strict. Hostile in-process
callers, object forgery, subclass spoofing, copy/deepcopy resistance, privilege escalation, and
enterprise authorization machinery are outside the current threat model.

Correctness depends on canonical source identity, complete obligation derivation, claim-specific
semantic evaluation, deterministic projection, and recomputation before handoff—not Python object
identity or hidden runtime state.

## CE runtime

```text
verified Architect intake
+ verified source bundle
+ Lean CE Review Draft
→ derive required review units and claims
→ claim-specific deterministic evaluators
→ four intermediate results
→ one CE Stage Payload assembler
→ independent recomputation and comparison
→ existing Project Gate transaction
→ Builder handoff only when every functional condition passes
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

## Runtime intake

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
- Schema and semantic validation remain mandatory;
- multiple valid CE inputs block as ambiguous;
- extra irrelevant, Receipt-like, malformed, legacy, or wrong-stage files produce a warning when one valid CE input exists;
- a source bundle is requested only when needed to establish correctness;
- supplied relevant source evidence is verified before it is relied upon;
- invalid or insufficient CE input remains fail-closed.

## Lean CE Review Draft

The model- or human-facing input is `ev4-ce-review-draft@1.0.0`. It contains engineering analysis:

- `proposed_action` and `engineering_rationale`;
- additive `requested_claims`;
- candidate source references and structured claim semantics;
- assumptions and limitations;
- implementation strategy proposals;
- Builder action proposals;
- unresolved questions and downstream-test suggestions.

The Draft does not author authoritative outcomes. It cannot set proven Booleans, constructability
status, Builder eligibility, Builder package emission, Payload status, or handoff authorization.
`requested_claims` is advisory and additive. The runtime derives mandatory claims from Architect
nodes, action types, class/structure changes, responsive/overlay/interaction/Dynamic Loop/asset/UI/
accessibility consequences, Builder execution requirements, and applicable CE rules.

An unknown action fails closed. An empty required-claim set is valid only when a repository rule
explicitly establishes non-applicability for every action.

## Claim-specific evaluation

The single canonical registry is `validator/claim_policy_registry.py`. It distinguishes:

- `VERIFIED_ARTIFACT`;
- `VERIFIED_TOOL_EXECUTION`;
- `VERIFIED_ARCHITECT_DECISION`;
- `ATTRIBUTED_ENGINEERING_JUDGMENT`;
- `DOWNSTREAM_TEST_OBLIGATION`.

Important distinctions:

```text
attributed engineering judgment != tool execution
source integrity != claim correctness
runtime-only claim != editor configuration assertion
non-empty object != proven claim
```

A file path and SHA-256 prove file identity and integrity only. Claim-specific evaluators must parse
or adapt the exact source, derive required semantic facts, and bind the result to the exact node,
candidate, Architect intake, and source bundle.

Runtime-only responsive, accessibility, and QA claims require actual captured execution from a known
repository-supported evaluator. Without it, the runtime emits a downstream obligation that remains
visible and blocks Builder handoff. Architect-owned interaction and Dynamic Loop decisions must be
present in canonical Architect input; CE cannot self-approve them.

## Four intermediate results

1. Architecture identity preservation compares candidate, classes, Build Tree nodes, Architect
   Unknowns, forbidden work, and trace completeness.
2. Review units and interrogation compares every required Architect node with Draft coverage and
   detects missing, orphan, duplicate, and incomplete units.
3. Dependency classification emits one explicit row for every required node/claim pair. A missing
   row is failure, not implicit `not_applicable`.
4. Implementation strategy coverage verifies strategy coverage, Builder targets, hidden decisions,
   Architect amendments, first-safe-batch completeness, candidate fidelity, and class fidelity.

## Builder-ready integrity

Builder-ready is impossible unless all of these are true:

```text
architecture identity result is complete
review-unit coverage is complete
every required dependency is satisfied or explicitly non-applicable
no unresolved blocking evidence remains
strategy coverage is complete
no hidden Builder decision remains
no hidden Architect amendment remains
Builder package is valid against ev4-builder-executable-package@1.0.0
```

The assembler does not use `all(...)` over an unproven empty requirement set. CE does not claim
production readiness.

## Deterministic Payload and export

`validator/payload_assembler.py` contains the only successor Payload assembler.
`validator/payload_fidelity.py` independently reruns the same evaluator pipeline, reassembles the
expected Payload, and compares canonical JSON before export. This detects mutation of claim status,
evidence, blockers, unresolved evidence, candidate/classes, Build Tree identity, Unknowns, forbidden
work, Builder decisions, Architect amendments, strategy coverage, Builder package emission, Payload
status, and handoff authorization.

Key artifacts:

```text
schemas/ce_review_draft.v1.schema.json
schemas/constructability_review.v1_1.schema.json
schemas/ce_stage_payload.v1_1.schema.json
validator/claim_policy_registry.py
validator/review_obligations.py
validator/claim_evaluators.py
validator/intermediate_results.py
validator/payload_assembler.py
validator/payload_fidelity.py
validator/verified_constructability.py
validator/verified_project_gate_exporter.py
contracts/CE_DETERMINISTIC_CONSTRUCTABILITY_EVALUATION_V1_1.md
```

Official command:

```bash
ev4-ce-project-gate-export \
  --review-draft <ce-review-draft.json> \
  --source-intake <architect-intake.json> \
  --source-bundle <architect-source-bundle.json> \
  --output <ce-project-gate.json>
```

Historical `ev4-ce-stage-payload@1.0.0` artifacts retain their meaning and remain diagnosable or
previewable. The named legacy path always carries:

```yaml
assurance_kind: DECLARATION
verification_status: MANUAL_UNVERIFIED
official_builder_authorization: false
```

A raw legacy Payload cannot produce `handoff.allowed=true`.

Export protections retained for correctness include deterministic serialization, exact source
snapshot checks, source and selected-candidate/class binding, synthetic-evidence blocking, atomic
writes, persisted-byte validation, export identity verification, transaction recomputation, and no
silent fallback.

## Boundaries

CE does not redesign architecture, rescore candidates, change `selected_candidate_id`, self-approve
Architect-owned decisions, act as Builder, hide Unknowns/blockers, or claim real Elementor,
responsive, accessibility, deployment, or production completion without compatible evidence.

## Quick start

1. Load `release/EV4_CE_PROJECT_RELEASE_PACK_v1/PROJECT_INSTRUCTIONS.md`.
2. Supply the valid Architect intake and exact source bundle.
3. Produce an `ev4-ce-review-draft@1.0.0` containing analysis and proposals only.
4. Let the runtime derive obligations and run claim-specific evaluators.
5. Keep unavailable runtime evidence as explicit downstream obligations.
6. Export only through `ev4-ce-project-gate-export` and the successor deterministic path.

## Validation

```bash
python -m pip install -e '.[dev]'
python scripts/check-ce-bootstrap.py
python scripts/validate-ce-architect-stage-intake.py
python scripts/validate-behavioral-rule-coverage.py
python scripts/validate-role-alignment-fixtures.py
python scripts/validate-project-gate-producer-adoption.py
npm run test:reference-paradigm-lock
pytest -q
ruff check .
```

## Companion repositories

```text
rezahh107/EV4-Project-Gate
rezahh107/EV4-Architect-Repo
rezahh107/EV4-Builder-Assistant-Repo
rezahh107/EV4-Responsive-Architect
```