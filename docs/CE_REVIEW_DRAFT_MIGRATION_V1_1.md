# CE Review Draft migration — deterministic evaluator v1.1

Status: active guidance for the runtime merged through `PR #45`.

Use `ev4-ce-review-draft@1.0.0` as the independent engineering input. The Draft may contain rationale, assumptions, limitations, original-source references, claim semantics, implementation strategies, Builder-action proposals, unresolved questions, runtime execution requests, and downstream-test suggestions.

Do not put authoritative outcomes in the Draft. In particular, do not add or pre-author:

```text
geometry_proven
overlay_strategy_proven
constructability_status
builder_eligibility
builder_package_emitted
payload_status
handoff_allowed
execution_status
exit_code
captured_result
result_digest
transaction_id
```

`requested_claims` is advisory and additive. The runtime derives mandatory obligations from the accepted Architect Build Tree, the closed action vocabulary, proposed class and structure effects, responsive/overlay/interaction/Dynamic Loop/asset/UI/accessibility consequences, Builder execution requirements, and applicable CE rules. Omission from `requested_claims` cannot remove a mandatory claim.

For CE-owned pre-Builder engineering claims, provide complete structured semantics and explicit premises. A file reference or digest establishes identity and integrity only; it is not semantic proof. Original JSON, HTML, CSS, or SVG evidence is evaluated through repository-owned claim-specific parsers.

For `post_builder_runtime` claims:

- the Draft may request execution, but it must not supply a completed authority-shaped result;
- only a repository-owned runner may create `VERIFIED_TOOL_EXECUTION` by executing a supported target in the current bound transaction;
- no Browser, Elementor, accessibility, interaction, or QA runner currently exists in this repository;
- therefore the normal pre-Builder representation is a complete deterministic downstream obligation;
- a missing or incomplete mandatory obligation blocks Builder handoff;
- a complete obligation with `status: required` does not block Builder handoff, but it keeps `final_project_gate: blocked` until an accepted executed pass or explicit non-applicability is recorded;
- an obligation is never execution evidence.

The canonical path is:

```text
CE Review Draft
+ verified Architect intake
+ verified source bundle
→ validator.payload_fidelity.evaluate_ce_transaction
→ verified ev4-ce-stage-payload@1.1.0
→ validator.verified_project_gate_exporter
```

The historical raw `ev4-ce-stage-payload@1.0.0` path remains validation and migration-preview only. It cannot authorize Builder handoff or Project Gate transition.