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

## Bounded fail-closed repair

Reviewed head `bc3e30018e664ab2de19683dc718669567b6b693` contained two confirmed defects. The repair:

- removes caller-supplied provenance from the public `export_file` API;
- requires every public/operator execution to call live `inspect_git_provenance`;
- keeps `build_export(..., provenance=...)` only as an internal composition boundary;
- parses the source intake from one captured byte snapshot;
- verifies that the source intake remains byte-identical after official validation;
- hashes `file_bytes` and `external_artifact` scopes from the captured bytes rather than an uncontrolled reread;
- converts source-intake read failures into blocking `CE_EXPORT_SOURCE_INTAKE_READ_FAILED` diagnostics;
- returns structured CLI JSON with exit code `1` and writes no output for read failures or mutation.

These repairs require fresh independent PR Inspector review. They do not claim that earlier findings are finally closed.

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

The existing `validate-fixtures` workflow runs the complete pytest and repository validation sequence. Focused regression coverage now includes public provenance bypass rejection, exact live-inspection identity propagation, dirty-checkout blocking, stable byte-snapshot hashing, `PermissionError`, `FileNotFoundError`, generic `OSError`, source mutation, structured CLI failure, deterministic repeat, and invalid-output absence.
