# CE Intermediate Validation Carriers v1

```yaml
contract_id: ev4-ce-intermediate-validation-carriers
contract_version: 1.0.0
owner_repository: rezahh107/EV4-Constructability-Engineer-Repo
scope: repository_internal_derived_validation_artifacts
public_cross_repository_contract: false
builder_authorization: false
project_gate_authorization: false
```

## Purpose

The four carriers provide deterministic, inspectable evidence between canonical CE inputs and the final CE Stage Payload. They do not replace `ev4-ce-stage-payload@1.0.0`, `ev4-builder-executable-package@1.0.0`, the existing CE final validation transaction, or the Project Gate exporter.

The only authoritative intermediate-validation path is:

```text
raw canonical inputs
→ derive Carrier 1
→ validate Carrier 1
→ derive Carrier 2
→ validate Carrier 2
→ derive Carrier 3
→ validate Carrier 3
→ derive Carrier 4
→ validate Carrier 4
→ compare the final CE Stage Payload with internally derived facts
→ return one deterministic transaction result
```

The repository-owned entry point is:

```python
evaluate_ce_intermediate_validation(...)
```

## Authoritative input set

The composite evaluator receives only:

- `run_id`;
- canonical `ev4-ce-architect-stage-intake@1.1.0`;
- the trusted source bundle already referenced by the intake contract;
- the current CE constructability review;
- the current Implementation Strategy Map when present;
- the current Builder Executable Package when present;
- a separately assembled final CE Stage Payload.

No serialized carrier is accepted as authoritative input.

## Carrier authority boundary

Serialized intermediate carriers are observational outputs.

They may be used as:

- deterministic diagnostic artifacts;
- inspectable intermediate results;
- fixture outputs;
- test evidence;
- debugging and reporting surfaces.

They are not authoritative inputs to the final CE Payload fidelity decision. An authoritative result must rederive all four carriers from raw canonical inputs inside the same repository-owned evaluator execution.

The individual derivation functions remain available for diagnostics, tests, and artifact generation:

```python
derive_architecture_identity_preservation(...)
derive_review_units_and_interrogation_results(...)
derive_dependency_classification(...)
derive_implementation_strategy_coverage(...)
validate_carrier(...)
```

`validate_ce_payload_against_intermediate_carriers(...)` is retained only as a diagnostic compatibility wrapper. It is excluded from the package public authority surface and must not be used to authorize Builder readiness or Project Gate transition.

## Common envelope

All four carriers use:

```yaml
schema_id: ev4-ce-intermediate-validation-carrier@1.0.0
schema_version: 1.0.0
carrier_kind: <one of four kinds>
owner_repository: rezahh107/EV4-Constructability-Engineer-Repo
run_id: <stable run identity>
status: complete | insufficient_evidence | blocked | invalid
diagnostics: []
source_identities: []
derived_data: {}
```

Carrier content is deterministic and contains no timestamps, random identifiers, network-derived state, GUI state, GitHub/PR state, or mutable filesystem-order assumptions. Identical inputs produce identical canonical JSON bytes.

Status precedence is:

```text
invalid > blocked > insufficient_evidence > complete
```

Diagnostic families are:

```text
CE_IDENTITY_*
CE_REVIEW_UNIT_*
CE_DEPENDENCY_*
CE_STRATEGY_COVERAGE_*
CE_INTERMEDIATE_*
```

## Carrier 1 — `architecture_identity_preservation_result`

Inputs:

- canonical Architect intake;
- trusted Architect source bundle;
- current CE constructability review.

Derived facts include:

- source bundle ID and canonical hash consistency;
- selected-candidate preservation;
- approved class-set preservation;
- accepted Build Tree node preservation;
- Architect Unknown preservation;
- forbidden-work preservation;
- review-unit trace coverage;
- absence of unauthorized class or structure redesign.

The payload projection covers `ce_stage_payload.architecture_identity`.

## Carrier 2 — `ce_review_units_and_interrogation_results`

Inputs:

- canonical Architect structure projection;
- current CE `constructability_review.reviewed_nodes`.

Derived facts include:

- complete source-node coverage;
- unique CE `review_unit_id` values;
- one Architect source mapping per review unit;
- no missing or orphan mappings;
- structured interrogation results;
- all current CE interrogation fields;
- explicit Architect permission state for class or structure changes.

`review_unit_id` is the canonical CE execution identity. `architect_node_ref` is source traceability evidence only.

## Carrier 3 — `dependency_classification`

Carrier 3 classifies every CE review unit across the existing rule dimensions:

| Dimension | Existing rule |
|---|---|
| geometry | `R03_GEOMETRY_MUST_BE_PROVEN` |
| asset | `R04_ASSET_SOURCE_OR_PLACEHOLDER` |
| overlay | `R05_OVERLAY_STRATEGY_MUST_BE_PROVEN` |
| responsive | `R06_RESPONSIVE_ACTION_REQUIRES_STRATEGY_OR_BLOCK` |
| interaction | `R07_INTERACTION_REQUIRES_APPROVAL` |
| Dynamic Loop | `R08_DYNAMIC_LOOP_REQUIRES_APPROVAL` |
| class/structure change | `R09_STRUCTURE_OR_CLASS_CHANGE_REQUIRES_PERMISSION` |
| exact UI path | `R10_UI_CONTROL_PATH_REQUIRES_EVIDENCE` |
| accessibility | `R16_ACCESSIBILITY_CLAIM_REQUIRES_EVIDENCE` |

Legal classifications are:

```text
satisfied
non_blocking_obligation
blocking
insufficient_evidence
not_applicable
```

Carrier 3 must expose the same CE `review_unit_id` set as Carrier 2. Any mismatch is an internal consistency failure and fails closed.

## Carrier 4 — `implementation_strategy_coverage_result`

Strategy coverage is keyed exclusively by CE `review_unit_id` through the existing Strategy `node_id` field.

`architect_node_ref` must not be accepted as an interchangeable Strategy key. No dual-ID guessing, alias lookup, or fallback resolution is permitted.

Carrier 4 verifies:

- every CE review unit has Strategy coverage;
- non-blocking obligations are covered by Strategy for the same review unit;
- blockers and insufficient evidence remain visible;
- selected candidate and approved classes are preserved;
- zero hidden Builder decisions;
- no hidden Architect amendments;
- complete structured confirmation data;
- a decision-free first safe Builder batch;
- Builder package schema, status, candidate, class set, Strategy reference, blockers, and decision count.

When Strategy is absent, the deterministic non-emission reasons remain:

```text
strategy_unavailable_due_to_blocking_dependencies
strategy_unavailable_due_to_insufficient_evidence
strategy_missing_without_repository_supported_absence_basis
```

When Strategy exists but complete validated Builder output cannot be produced, the repository-local reason is:

```text
builder_package_not_emitted_due_to_incomplete_strategy_coverage
```

Detailed causes remain in diagnostics rather than a larger reason taxonomy.

## Final CE Stage Payload fidelity

The final comparator receives the raw Builder Executable Package that Carrier 4 validated in the same composite transaction.

When Carrier 4 is `complete`, the final payload must satisfy all of these:

```yaml
builder_package_emitted: true
builder_package_not_emitted_reason: null
builder_executable_package: canonically equal to the raw validated package
```

Canonical equality uses compact, sorted JSON bytes. Object-key ordering does not affect equality, while any nested semantic drift does.

When Carrier 4 is not `complete`, the final payload must satisfy:

```yaml
builder_package_emitted: false
builder_executable_package: null
builder_package_not_emitted_reason: <Carrier 4 deterministic reason>
```

The comparator also verifies run identity, architecture projection, reviewed nodes, review traces, blockers, unresolved dependencies, evidence references, Strategy Map equality, and selected-candidate consistency.

## Fidelity and Builder readiness

Fidelity and Builder readiness are separate outputs.

```yaml
complete_ready:
  fidelity_passed: true
  builder_ready: true
  transaction_status: complete

faithful_blocked:
  fidelity_passed: true
  builder_ready: false
  transaction_status: blocked

faithful_insufficient_evidence:
  fidelity_passed: true
  builder_ready: false
  transaction_status: insufficient_evidence

payload_drift:
  fidelity_passed: false
  builder_ready: false
  transaction_status: blocked | invalid
```

`builder_ready=true` is forbidden unless all carriers are complete, all carrier validations pass, Review Unit identities are internally consistent, final-payload fidelity passes, and an exact validated Builder package is present.

## Compatibility and integration boundary

This contract does not change:

- `ev4-ce-architect-stage-intake@1.1.0`;
- `ev4-ce-stage-payload@1.0.0`;
- `ev4-builder-executable-package@1.0.0`;
- Project Gate Producer Export contracts;
- the existing CE final validation transaction;
- Project Instructions or release-pack instructions;
- Architect, Builder, Responsive, Project Gate, or Shared Contracts repositories.

The carriers do not authorize Builder execution or Project Gate transition. The existing final CE validation transaction remains authoritative and compatible.

## Out of scope

This contract does not add:

- conversational Stage Output contracts;
- `evaluate_ce_stage`;
- `evaluate_ce_run`;
- replay Run State;
- GUI or Stage QC integration;
- signatures, tokens, seals, attestations, receipts, remote provenance services, GitHub identity enforcement, or repository-settings requirements.
