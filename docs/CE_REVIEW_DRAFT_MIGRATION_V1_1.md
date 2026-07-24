# CE Review Draft migration — deterministic evaluator v1.1

Use `ev4-ce-review-draft@1.0.0` as engineering input. The Draft may contain rationale, assumptions,
limitations, candidate source references, claim semantics, implementation strategies, Builder-action
proposals, unresolved questions, and downstream-test suggestions.

Do not put authoritative outcomes in the Draft. In particular, do not add `geometry_proven`,
`overlay_strategy_proven`, `constructability_status`, `builder_eligibility`,
`builder_package_emitted`, `payload_status`, or `handoff_allowed`.

`requested_claims` is advisory and additive. The runtime derives mandatory obligations from the
accepted Architect Build Tree, supported action vocabulary, proposed changes, responsive/overlay/
interaction/Dynamic Loop/asset/UI/accessibility consequences, Builder execution requirements, and
applicable CE rules. Omission from `requested_claims` cannot remove a mandatory claim.

For CE-owned engineering claims, provide complete structured semantics and explicit premises.
A file reference and digest are not semantic proof. For runtime-only claims, pass actual captured
execution results from a known evaluator or leave an explicit downstream obligation. A downstream
obligation remains visible and cannot authorize Builder handoff.

The migration preserves the legacy raw Payload for diagnostic preview only. Use the verified Draft
export command for any successor handoff attempt.
