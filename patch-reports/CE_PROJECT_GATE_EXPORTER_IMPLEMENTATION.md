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
- derives repository identity, branch, and exact commit from Git;
- writes deterministic canonical JSON atomically and revalidates after write;
- blocks handoff for synthetic evidence, unresolved evidence, non-executable CE state, absent/ineligible Builder package, or dirty checkout;
- rejects malformed/tampered/source-mismatched/unsafe-path cases before an allowed artifact is written.

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

The existing `validate-fixtures` workflow runs `pytest -q`, so the new exporter unit and integration tests are enforced by the authoritative CI path without adding a competing workflow.
