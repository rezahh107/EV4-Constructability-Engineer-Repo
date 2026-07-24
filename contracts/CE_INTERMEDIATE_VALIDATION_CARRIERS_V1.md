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

## Purpose and authority boundary

The four intermediate carriers are deterministic, inspectable outputs derived from raw CE inputs. Serialized carrier files are observational artifacts only. They cannot authorize Builder readiness, final Payload fidelity, or Project Gate transition.

The sole authoritative intermediate evaluator is:

```python
evaluate_ce_intermediate_validation(...)
```

It accepts these raw inputs:

```yaml
- run_id
- canonical Architect intake
- trusted Architect source bundle referenced by that intake
- independent CE constructability review
- independent Implementation Strategy Map, when present
- independent Builder Executable Package, when present
- separately assembled final CE Stage Payload
- authoritative CE repository root
```

Its authority chain is:

```text
official final Payload Schema validation
+ official final Payload semantic validation
+ raw canonical CE inputs
→ derive Carrier 1 and validate
→ derive Carrier 2 and validate
→ derive Carrier 3 and validate
→ derive Carrier 4 and validate
→ compare final Payload with internally derived facts
→ return fidelity and Builder readiness as separate results
```

The evaluator never accepts caller-supplied serialized carriers. Any diagnostic helper that compares serialized carriers is private, returns no authority-shaped `passed`, `fidelity_passed`, or `builder_ready` field, and cannot participate in producer authorization.

## Official producer integration

The authoritative CE producer transaction requires the operator to supply the independent intermediate artifact explicitly through both public surfaces:

```python
def export_file(
    *,
    repo_root: Path,
    payload_path: Path,
    source_intake_path: Path,
    source_bundle_path: Path,
    intermediate_inputs_path: Path,
    output_path: Path,
    overwrite: bool = False,
) -> ExportResult:
    ...
```

```text
--intermediate-inputs path/to/current-ce-intermediate-inputs.json
```

No sibling filename, intake-directory adjacency, alternate search path, or silent fallback participates in authority. The supplied artifact retains this repository-owned identity:

```yaml
schema_id: ev4-ce-intermediate-export-inputs@1.0.0
schema_version: 1.0.0
run_id: <same run_id as final Payload>
constructability_review: {}
implementation_strategy_map: {} | null
builder_executable_package: {} | null
```

These values must be independent CE runtime outputs. The producer must not reconstruct them from the final Payload immediately before evaluation.

The exporter resolves all four public inputs once, protects the output from aliasing any of them, snapshots their exact bytes independently, and rechecks byte stability before publication. Before Stage Manifest construction it:

1. verifies the source intake and source bundle;
2. validates the explicit intermediate artifact and run identity;
3. runs `evaluate_ce_intermediate_validation(...)`;
4. requires successful fidelity;
5. runs the existing official final CE validation transaction;
6. derives intermediate Stage Manifest status and output hashes from internally derived carriers;
7. permits Builder handoff only when the composite result is Builder-ready and all functional export gates pass.

A missing, changed, malformed, run-mismatched, or Payload-inconsistent intermediate input artifact fails closed before publication. Git dirty state is retained only in result metadata and never authorizes or blocks the transaction.

## Common carrier envelope

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

Carrier content is timestamp-free, network-independent, canonically serialized, and deterministic. Identical inputs produce identical canonical JSON bytes.

Status precedence is:

```text
invalid > blocked > insufficient_evidence > complete
```

Diagnostic families remain:

```text
CE_IDENTITY_*
CE_REVIEW_UNIT_*
CE_DEPENDENCY_*
CE_STRATEGY_COVERAGE_*
CE_INTERMEDIATE_*
```

## Carrier 1 — `architecture_identity_preservation_result`

Carrier 1 derives identity preservation from the canonical intake, the trusted source bundle, and the independent constructability review. It verifies source-bundle identity and hash, selected candidate, approved classes, Build Tree identity, Architect Unknowns, forbidden work, review traces, and absence of unauthorized architecture redesign.

## Carrier 2 — `ce_review_units_and_interrogation_results`

Carrier 2 proves complete CE review-unit coverage and structured interrogation results. `review_unit_id` is the canonical CE-owned identity. `architect_node_ref` is source traceability only. The two values may differ and are never treated as aliases.

## Carrier 3 — `dependency_classification`

Carrier 3 classifies every CE Review Unit across the current repository rule dimensions, preserves blockers and unresolved evidence, and exposes the same canonical `review_unit_id` set as Carrier 2. Any identity-set disagreement is invalid.

## Carrier 4 — `implementation_strategy_coverage_result`

Carrier 4 keys Strategy coverage exclusively by CE `review_unit_id`, using the existing Strategy `node_id` field. A Strategy keyed by `architect_node_ref` is orphaned unless that value is independently the actual Review Unit ID.

Before Carrier 4 may become complete, a raw Builder package must:

1. pass `schemas/builder_executable_package.schema.json` under Draft 2020-12;
2. pass the existing Builder eligibility semantics;
3. preserve candidate, class set, Strategy reference, blocker state, zero Builder decisions, confirmation data, and first safe batch requirements.

Canonical equality proves sameness only. It does not replace Schema or semantic validity.

When a Strategy exists but package or coverage validation is incomplete, the bounded non-emission reason is:

```text
builder_package_not_emitted_due_to_incomplete_strategy_coverage
```

Existing absence reasons remain:

```text
strategy_unavailable_due_to_blocking_dependencies
strategy_unavailable_due_to_insufficient_evidence
strategy_missing_without_repository_supported_absence_basis
```

## Final Payload fidelity and Builder readiness

The composite result separates:

```yaml
transaction_status: complete | insufficient_evidence | blocked | invalid
fidelity_passed: boolean
builder_ready: boolean
carrier_statuses: {}
carriers: {}
diagnostics: []
```

No final Payload can pass authoritative fidelity unless it first passes the official `ev4-ce-stage-payload@1.0.0` Schema and `validate_document(..., mode="full")` semantics.

A Schema-valid non-ready Payload normally uses:

```yaml
payload_status: insufficient_evidence
builder_package_emitted: false
builder_executable_package: null
```

The composite transaction may still derive `transaction_status: blocked` while fidelity remains true and `builder_ready` remains false.

When Carrier 4 is complete, the final Payload must emit the exact raw Builder package validated in that same transaction:

```yaml
builder_package_emitted: true
builder_package_not_emitted_reason: null
builder_executable_package: canonical equality with validated raw package
```

When Carrier 4 is not complete, the final Payload must not emit a Builder package and must preserve the deterministic non-emission reason.

## Compatibility and exclusions

This contract does not change these public cross-repository contracts:

```text
ev4-ce-architect-stage-intake@1.1.0
ev4-ce-stage-payload@1.0.0
ev4-builder-executable-package@1.0.0
producer-gate-export.v1
stage-evidence-bundle.v1
```

The existing official final CE validation transaction remains authoritative after the composite prerequisite. Carrier artifacts themselves do not authorize Builder execution or Project Gate transition.

Out of scope remains:

- conversational Stage Output contracts;
- `evaluate_ce_stage` or `evaluate_ce_run`;
- replay Run State;
- GUI or Stage QC integration;
- external repository changes;
- signatures, secrets, tokens, attestations, remote provenance, or repository-setting enforcement.
