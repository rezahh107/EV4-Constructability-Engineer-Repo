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

These carriers remove a circular-proof gap between CE source evidence and the final CE Stage Payload. They are derived by code from existing CE-owned inputs and semantics. They do not replace `ev4-ce-stage-payload@1.0.0`, the final CE validation transaction, or the Project Gate exporter.

The authority chain is:

```text
canonical Architect intake + trusted source bundle + CE review/strategy/package inputs
→ deterministic intermediate derivation
→ four evaluator-derived carriers
→ final CE Stage Payload fidelity comparison
→ existing final validation transaction remains authoritative
```

No model-authored Boolean is proof by itself. Assertions in the final payload are comparison targets only.

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

Carrier content is deterministic. It contains no timestamps, random identifiers, network-derived state, GUI state, GitHub/PR state, or mutable filesystem-order assumptions. Identical inputs produce identical canonical JSON bytes.

Status precedence is:

```text
invalid > blocked > insufficient_evidence > complete
```

Diagnostics are CE-owned and stable. Families are:

```text
CE_IDENTITY_*
CE_REVIEW_UNIT_*
CE_DEPENDENCY_*
CE_STRATEGY_COVERAGE_*
CE_INTERMEDIATE_*
```

## Carrier 1 — `architecture_identity_preservation_result`

### Inputs

- canonical `ev4-ce-architect-stage-intake@1.1.0`;
- explicitly supplied trusted Architect source bundle referenced by the intake transition;
- current CE `constructability_review`.

### Derived facts

- source bundle identity and canonical hash match the intake transition;
- `selected_candidate_id` matches across source bundle, intake, and CE review;
- approved class set matches across source bundle, intake, and CE review;
- accepted Build Tree node identity set is preserved by CE review units;
- Architect Unknown IDs are preserved;
- `forbidden_work` is not weakened;
- review-unit traces cover accepted Architect nodes;
- no class/structure redesign occurs without `architect_decomposition_permission`.

Missing source facts produce `insufficient_evidence`; contradictions or unauthorized redesign produce `blocked` or `invalid`.

### Payload projection

The carrier derives and verifies `ce_stage_payload.architecture_identity`, including candidate locks, approved classes, Build Tree preservation, Unknown preservation, forbidden-work weakening, and review-unit traces.

## Carrier 2 — `ce_review_units_and_interrogation_results`

### Inputs

- canonical Architect intake structure projection;
- current CE `constructability_review.reviewed_nodes`.

### Derived facts

- every required Architect node has one review unit;
- every review unit maps to a known Architect node;
- review-unit IDs are unique;
- duplicate source-node mappings are rejected unless a future explicit repository rule allows them;
- every review unit has a structured `interrogation_result`;
- current constructability-review interrogation fields are present;
- class/structure change carries explicit Architect permission state;
- missing and orphan node sets are explicit.

Completeness is never defined as “`reviewed_nodes` is non-empty”.

### Payload projection

The carrier derives and verifies:

- `ce_stage_payload.constructability_review.reviewed_nodes`;
- `ce_stage_payload.architecture_identity.review_unit_traces`.

## Carrier 3 — `dependency_classification`

### Inputs

- complete Carrier 2;
- current CE constructability review;
- current CE rule dimensions and rule IDs.

### Classification dimensions

The carrier reuses existing CE rule semantics:

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

Each review unit receives exactly one result per dimension:

```text
satisfied
non_blocking_obligation
blocking
insufficient_evidence
not_applicable
```

The carrier exposes blocking dependency IDs, non-blocking obligations, unresolved dependency IDs, evidence references, downstream owner, and complete traceability. Derived blockers must exactly match `constructability_review.blocking_dependencies`; suppression and untraceable declarations fail closed.

### Payload projection

The carrier verifies:

- `ce_stage_payload.constructability_review.blocking_dependencies`;
- dependency-related `ce_stage_payload.unresolved_evidence`;
- evidence references used by classification against `ce_stage_payload.evidence_register`.

The carrier itself is not reduced to a string blocker list.

## Carrier 4 — `implementation_strategy_coverage_result`

### Inputs

- complete Carriers 1–3;
- canonical `implementation_strategy_map`;
- current Builder Executable Package when ready output is claimed.

### Derived facts

- every required review unit has Strategy coverage;
- non-blocking obligations are covered by Strategy for the same unit;
- blocking or insufficient dependencies remain uncovered and block/limit status;
- selected candidate and approved classes remain preserved;
- every strategy has zero hidden Builder decisions for ready output;
- Architect amendment requirements are not hidden;
- first safe Builder batch is present and decision-free;
- structured confirmation data is present;
- Builder package schema, candidate, class set, strategy reference, blockers, and decision count are consistent.

When Strategy is absent, the carrier emits one repository-local absence reason:

```text
strategy_unavailable_due_to_blocking_dependencies
strategy_unavailable_due_to_insufficient_evidence
strategy_missing_without_repository_supported_absence_basis
```

The reason is not copied from `builder_package_not_emitted_reason`; it is independently derived.

### Payload projection

The carrier derives and verifies:

- `ce_stage_payload.implementation_strategy_map`;
- `ce_stage_payload.builder_package_not_emitted_reason`;
- Strategy-related unresolved evidence visibility.

## Final CE Stage Payload fidelity

`validate_ce_payload_against_intermediate_carriers(...)` compares a separately assembled final CE Stage Payload with independently derived carriers. It verifies:

- shared `run_id`;
- architecture identity projection;
- reviewed nodes and traces;
- blocker equality;
- unresolved dependency preservation;
- evidence-reference preservation;
- Strategy Map equality;
- Strategy absence reason;
- selected candidate consistency across payload surfaces;
- absence of a false `complete` or emitted Builder package while any carrier is incomplete.

Deriving carriers from the final payload and comparing them back to the same payload is prohibited circular validation.

## Compatibility and integration boundary

This contract does not change:

- `ev4-ce-architect-stage-intake@1.1.0`;
- `ev4-ce-stage-payload@1.0.0`;
- `ev4-builder-executable-package@1.0.0`;
- Project Gate Producer Export contracts;
- Project Instructions or release-pack instructions;
- Architect, Builder, Responsive, Project Gate, or Shared Contracts repositories.

The current direct final-payload validation and exporter remain compatible. This PR exposes the carriers and fidelity validator as an independently callable prerequisite for a future replay runtime. It does not implement `evaluate_ce_stage`, `evaluate_ce_run`, replay Run State, conversational Stage Output contracts, GUI behavior, or Stage QC integration.
