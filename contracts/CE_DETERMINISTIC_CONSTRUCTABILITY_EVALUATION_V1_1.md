# CE Deterministic Constructability Evaluation v1.1

Status: active successor runtime contract merged through `PR #45`  
Owner: `rezahh107/EV4-Constructability-Engineer-Repo`

## Functional model

```text
verified Architect intake
+ verified source bundle
+ CE Review Draft
        ↓
derive mandatory review units and phase-aware claims
        ↓
normalize Builder proposals into closed Action IR
        ↓
claim-specific deterministic evaluators
        ↓
four intermediate evaluation results
        ↓
one CE Stage Payload assembler
        ↓
independently recompute and compare the Payload
        ↓
official verified Project Gate exporter
```

The Draft proposes analysis. It does not author authoritative technical results. `requested_claims` is additive and never replaces runtime-derived mandatory claims. An unknown action or an executable action with no proven applicability rule fails closed.

## Single authority path

The canonical transaction is:

```text
validator.payload_fidelity.evaluate_ce_transaction
```

Direct Python evaluation, verified Payload assembly, fidelity replay, and the official exporter converge on that transaction. The repository does not retain a second evaluator, policy registry, Payload assembler, final-Payload validator, intermediate-carrier authority path, or Builder-handoff path.

The official exporter is:

```text
validator.verified_project_gate_exporter
```

with explicit authoritative inputs:

```text
--review-draft
--source-intake
--source-bundle
```

## Authority and evidence

There is one canonical claim registry: `validator/claim_policy_registry.py`. Each policy names its owner, lifecycle phase, evaluator, allowed evidence modes, required semantics, Builder-handoff effect, and final-completion effect.

A stable file digest establishes file identity and integrity only. It does not establish geometry, overlay containment, UI-control existence, asset suitability, responsive behavior, accessibility, interaction validation, or QA. Claim-specific evaluators parse original source bytes or derive bounded attributed engineering judgments and bind results to the exact node, selected candidate, Architect intake, and source bundle.

Attributed engineering judgment is allowed only for repository-defined CE-owned claims and must carry explicit premises, derivation method, semantic facts, reviewer attribution, and limitations. It is not tool execution.

For `post_builder_runtime` claims:

- caller-authored completed-result mappings are not authority;
- only a repository-owned runner may create `VERIFIED_TOOL_EXECUTION` by executing a supported target in the current bound transaction;
- no Browser, Elementor, accessibility, interaction, or QA runner currently exists in this repository;
- the normal pre-Builder state is therefore a complete deterministic downstream obligation;
- a missing or incomplete mandatory obligation blocks Builder handoff;
- a complete `status: required` obligation does not block Builder handoff, but it blocks Final Project Gate until an accepted executed pass or explicit non-applicability is recorded.

## Four intermediate results

1. Architecture identity preservation compares candidate, classes, Build Tree nodes, Architect Unknowns, forbidden work, and review-unit traces.
2. Review units and interrogation compares all required Architect nodes with Draft coverage and detects missing, orphan, duplicate, and incomplete units.
3. Dependency classification emits one explicit row for every required node/claim pair. A missing row is a failure; it is never implicit `not_applicable`.
4. Implementation strategy coverage verifies strategy, Builder-action, hidden-decision, Architect-amendment, first-safe-batch, candidate, and class fidelity.

The four results are internal deterministic evaluation products. They are not caller-supplied authority artifacts.

## Payload and fidelity

`validator.payload_assembler.py` contains the only successor Payload assembler. The Payload is a deterministic projection of canonical identities, normalized Action IR, the four intermediate results, runtime obligations, and the policy registry.

Builder eligibility is derived. Safe-looking Draft Booleans and caller-authored runtime outcomes cannot set it.

Before export, `validator.payload_fidelity.evaluate_ce_transaction` reruns the evaluator pipeline, reassembles the expected Payload, and compares canonical JSON. Mutation of claim state, evidence, blockers, obligations, Unknowns, candidate/classes, Build Tree identity, Builder decisions, Architect amendments, strategy coverage, Builder package emission, Payload status, lifecycle status, or handoff authorization fails closed.

## Publication correctness

The verified exporter preserves:

- explicit operator input paths;
- strict JSON parsing and duplicate-key rejection;
- exact-byte snapshots and mutation detection;
- output/input alias rejection;
- deterministic canonical serialization;
- atomic publication;
- post-write byte, Schema, semantic, identity, and transaction validation;
- removal of a failed new output or restoration of a prior owned output;
- Git dirty state as reporting metadata only.

Dirty state does not change claim resolution, fidelity, Builder readiness, handoff authorization, exporter status, or exit code.

## Legacy compatibility

`ev4-ce-stage-payload@1.0.0` retains its historical meaning. The raw path is explicitly named and preview-only. It may produce diagnostics and migration output, but it adds `CE_EXPORT_LEGACY_PAYLOAD_AUTHORIZATION_FORBIDDEN` and cannot authorize Builder handoff or Project Gate transition.

The following contracts remain unchanged:

- `ev4-builder-executable-package@1.0.0`
- `stage-evidence-bundle.v1`
- `producer-gate-export.v1`
- the existing Project Gate transaction boundary

## Threat model

This repository is operated as a personal single-operator system. Object forgery, subclass spoofing, copy/deepcopy resistance, hidden fingerprints, cryptographic attestation, and hostile in-process callers are outside scope.

Correctness depends on canonical source binding, semantic evaluation, complete obligation derivation, deterministic projection, and recomputation before handoff—not object secrecy or Python object identity.