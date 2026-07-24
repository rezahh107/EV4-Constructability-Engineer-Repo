# CE Deterministic Constructability Evaluation v1.1

Status: successor runtime contract for PR #45  
Owner: `rezahh107/EV4-Constructability-Engineer-Repo`

## Functional model

```text
verified Architect intake
+ verified source bundle
+ CE Review Draft
        ↓
derive mandatory review units and claims
        ↓
claim-specific deterministic evaluators
        ↓
four intermediate evaluation results
        ↓
one CE Stage Payload assembler
        ↓
recompute and compare persisted Payload
        ↓
existing Project Gate transaction
```

The Draft proposes analysis. It does not author authoritative technical results.
`requested_claims` is additive and never replaces runtime-derived mandatory claims.
An unknown action or an executable action with no proven applicability rule fails closed.

## Authority and evidence

There is one canonical registry: `validator/claim_policy_registry.py`.
Each claim policy names its owner, evaluator, required semantics, and blocking behavior.

A stable file digest establishes file identity and integrity only. It does not establish geometry,
overlay containment, UI-control existence, asset suitability, responsive behavior, accessibility,
or QA. Claim-specific evaluators parse or adapt the source and bind their result to the exact node,
selected candidate, Architect intake, and source bundle.

Attributed engineering judgment is allowed only for repository-defined CE-owned claims and must
carry explicit premises, derivation method, semantic facts, reviewer attribution, and limitations.
It is not tool execution. Runtime-only claims require an actual captured result from a known
repository-supported evaluator; otherwise they become downstream obligations and block Builder
handoff.

## Four intermediate results

1. Architecture identity preservation compares candidate, classes, Build Tree nodes, Architect
   Unknowns, forbidden work, and review-unit traces.
2. Review units and interrogation compares all required Architect nodes with Draft coverage and
   detects missing, orphan, duplicate, and incomplete units.
3. Dependency classification emits one explicit row for every required node/claim pair. A missing
   row is a failure; it is never implicit `not_applicable`.
4. Implementation strategy coverage verifies strategy, Builder-action, hidden-decision, Architect
   amendment, first-safe-batch, candidate, and class fidelity.

## Payload and fidelity

`assemble_ce_stage_payload(...)` is the only successor Payload assembler. The Payload is a pure
projection of canonical identities, the four intermediate results, and the policy registry.
Builder eligibility is derived; safe-looking caller Booleans are ignored because they are not Draft
fields.

Before export, the runtime independently reruns the same evaluator pipeline, reassembles the
expected Payload, and compares canonical JSON. Mutation of claim state, evidence, blockers,
Unknowns, candidate/classes, Builder decisions, Architect amendments, strategy coverage,
Builder package emission, Payload status, or handoff authorization fails closed.

## Legacy compatibility

`ev4-ce-stage-payload@1.0.0` retains its historical meaning. The raw path is explicitly named and
preview-only. It may produce diagnostics and migration output, but it always adds
`CE_EXPORT_LEGACY_PAYLOAD_AUTHORIZATION_FORBIDDEN` and cannot authorize Builder handoff.

The following contracts remain unchanged:

- `ev4-builder-executable-package@1.0.0`
- `stage-evidence-bundle.v1`
- `producer-gate-export.v1`
- the existing Project Gate transaction boundary

## Threat model

This repository is operated as a personal single-operator system. Object forgery, subclass spoofing,
copy/deepcopy resistance, hidden fingerprints, and hostile in-process callers are outside scope.
Correctness does not depend on object secrecy or Python object identity. It depends on canonical
source binding, semantic evaluation, complete obligation derivation, deterministic projection, and
recomputation before handoff.
