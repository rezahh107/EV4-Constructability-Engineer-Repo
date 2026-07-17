# CE-01 Real Project Gate Exporter Implementation

Prompt ID: `P-002`  
Task ID: `CE-01`

## Problem

The repository had adopted the CE Stage Payload, Stage Bundle shape, Producer Gate Export contract, fixtures, and validators, but it did not expose a real operator command that assembled and wrote `ce-project-gate.json`. The mutable status therefore overstated the executable exporter surface.

## Implementation

- adds `ev4-ce-project-gate-export` and `scripts/export-ce-project-gate.py`;
- consumes the active CE Stage Payload and accepted Architect→CE intake;
- requires the actual source bundle and invokes the official intake validator for binding;
- invokes the official CE constructability validation path;
- validates an emitted `ev4-builder-executable-package@1.0.0`;
- vendors exact pinned `stage-evidence-bundle.v1` bytes and a non-authoritative lock;
- builds and validates a complete Stage Evidence Bundle and Producer Gate Export;
- derives repository identity, branch, exact commit, and dirty state from live Git inspection;
- writes deterministic canonical JSON atomically and revalidates after write;
- blocks handoff for synthetic evidence, unresolved evidence, non-executable CE state, absent/ineligible Builder package, or dirty checkout;
- rejects malformed/tampered/source-mismatched/unsafe-path cases before an allowed artifact is written.

## Bounded fail-closed repairs

Reviewed heads identified bounded defects. The repairs:

- remove caller-supplied provenance from the public `export_file` API;
- require every public/operator execution to call live `inspect_git_provenance`;
- keep `build_export(..., provenance=...)` only as an internal composition boundary;
- parse the source intake from one captured byte snapshot;
- verify that the source intake remains byte-identical after official validation;
- hash `file_bytes` and `external_artifact` scopes from the captured bytes rather than an uncontrolled reread;
- convert source-intake read failures into blocking `CE_EXPORT_SOURCE_INTAKE_READ_FAILED` diagnostics;
- return structured CLI JSON with exit code `1` and write no output for source read failures or mutation;
- report post-write cleanup failure truthfully instead of claiming the invalid artifact is absent;
- preserve the original post-write validation diagnostic together with `CE_EXPORT_POST_WRITE_CLEANUP_FAILED`;
- mark cleanup-failed artifacts as invalid, persisted, prohibited from consumption, and never as valid blocked exports;
- restore the exact historical `builder_authorization_at_intake`, `real_cross_repository_validation`, and `fixture_classification` fields in the `CE_ARCHITECT_STAGE_INTAKE_V1_1` status block.

These repairs require fresh independent PR Inspector review. They do not claim that earlier findings are finally closed.

## Cleanup-failure result contract

```yaml
status: invalid
output_written: true
output_valid: false
output_cleanup_failed: true
artifact_state: invalid_artifact_persisted
artifact_must_not_be_consumed: true
handoff_allowed: false
```

When cleanup succeeds, the state is `invalid_artifact_removed` and `output_written=false`. Cleanup failure is not represented as an intentional blocked handoff artifact.

## Boundaries retained

```yaml
project_gate_runtime_integration: not_implemented
builder_context_package_generation: forbidden_in_ce
builder_runtime_authorization: not_claimed
responsive_completion: insufficient_evidence
production_ready: false
shared_runtime_dependency: not_added
contract_version_bump: none
```

## Validation authority

The existing `validate-fixtures` workflow runs the complete pytest and repository validation sequence. Focused regression coverage includes public provenance bypass rejection, exact live-inspection identity propagation, dirty-checkout blocking, stable byte-snapshot hashing, source-read errors, source mutation, deterministic repeat, successful invalid-output cleanup, schema/identity cleanup failure, structured CLI cleanup-failure output, and exact historical status-block integrity.
