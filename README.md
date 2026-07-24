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

## Repository maintenance

`repository_maintenance` remains an explicit out-of-band route for code, contracts, Schemas, tests,
CI, and documentation work. It does not authorize or execute the CE runtime pipeline, and its
maintenance evidence does not substitute for project evidence.

## CE runtime

```text
verified Architect intake
+ verified source bundle
+ Lean CE Review Draft
→ normalize every Builder proposal into closed Action IR
→ derive required review units and phase-aware claims
→ evaluate pre-Builder static and capability claims
→ emit complete post-Builder runtime obligations
→ four intermediate results
→ one CE Stage Payload assembler
→ independent recomputation and comparison
→ Builder handoff when CE Builder-ready
→ actual downstream runtime validation
→ Final Project Gate only after obligation closure
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

## Phase-aware claim evaluation

The single canonical registry is `validator/claim_policy_registry.py`. Every claim declares its
`lifecycle_phase`, evaluator kind, allowed evidence modes, Builder-handoff effect, and
final-completion effect.

```text
pre_builder_static
pre_builder_capability
post_builder_runtime
```

The runtime separates strategy from outcome:

```text
responsive_strategy != responsive_behavior
accessibility_strategy != accessibility runtime validation
interaction_approval != interaction_validation
```

Important distinctions:

```text
CE Builder-ready != runtime validated
CE Builder-ready != production ready
runtime obligation != execution proof
attributed engineering judgment != verified artifact
source digest != source-derived semantic fact
```

CE-owned geometry, overlay, responsive-strategy, accessibility-strategy, and placeholder decisions
may use `ATTRIBUTED_ENGINEERING_JUDGMENT` when the policy permits it. Architect-owned interaction and
Dynamic Loop approval must come from canonical Architect input.

Capability evidence starts from an original JSON, HTML, CSS, or SVG source. A claim-specific
repository parser reads the original bytes, derives facts, records parser identity and digest, and
compares those facts with the required semantics. A pre-authored `facts` envelope cannot become
`VERIFIED_ARTIFACT`. A cached extract is accepted only when the same parser regenerates identical
facts from the original source.

No real Browser, Elementor, accessibility, interaction, or QA runner currently exists in this
repository. Therefore authored `observed`, `passed`, `execution_status`, `exit_code`, or similar
fields are declarations and are rejected as runtime evidence. The CE stage emits deterministic
post-Builder obligations instead of fabricating `VERIFIED_TOOL_EXECUTION`.

## Closed Action IR

`validator/action_contract_registry.py` is the one canonical Builder-action vocabulary.
`validator/action_ir.py` rejects unknown actions, unknown parameters, effect-bearing parameters
under the wrong action, ambiguous aliases, conflicting combinations, and unresolved hidden choices.
Supported aliases are normalized exactly once.

Every accepted action becomes:

```yaml
action_id:
action_type:
target_node:
normalized_parameters:
derived_effects:
required_claims:
required_permissions:
decision_state:
source_draft_path:
```

Builder package actions are projected only from this Action IR. Raw Draft parameters are never
copied into an authority-bearing package. Class, structure, decision, permission, and
`forbidden_work` effects are derived from the closed registry and canonical Architect inputs.

## Runtime obligations

Every mandatory `post_builder_runtime` claim receives a complete obligation containing the exact
claim, subject, target identity, required runner, required inputs, assertions, completion criteria,
status, and blocking boundary.

Normal pre-Builder state:

```yaml
status: required
blocking_boundary: final_project_gate
blocks_builder_handoff: false
blocks_final_completion: true
```

A complete open obligation permits Builder handoff when every pre-Builder condition passes. It
remains visible through Payload assembly, Builder package projection, export, and fidelity replay.
It blocks Final Project Gate until an actual downstream runner returns an accepted bound pass.

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
every pre-Builder dependency is satisfied or explicitly non-applicable
every mandatory post-Builder claim has a complete runtime obligation
no unresolved pre-Builder evidence remains
strategy coverage is complete
no hidden Builder decision remains
no hidden Architect amendment remains
Builder package is valid against ev4-builder-executable-package@1.0.0
```

The assembler does not use `all(...)` over an unproven empty requirement set. `payload_status=complete`
means the CE stage is complete and Builder-ready; it does not mean runtime-validated or
production-ready. Lifecycle carriers keep `final_project_gate=blocked` while runtime obligations are
open.

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
validator/action_contract_registry.py
validator/action_ir.py
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
4. Let the runtime normalize Action IR and evaluate pre-Builder claims.
5. Carry mandatory post-Builder outcomes as explicit runtime obligations.
6. Hand the decision-free normalized package to Builder.
7. Close runtime obligations only through actual downstream execution.
8. Export only through `ev4-ce-project-gate-export` and the canonical deterministic path.

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
