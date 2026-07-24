# PR #45 Main Reconciliation

## Decision

`PR #45` remains the sole verified CE runtime. Current `main`, including merged `PR #46`, is integrated through a normal merge commit. Only functional invariants are adopted; the parallel intermediate-carrier authority path is not retained.

## Canonical path

```text
CE Review Draft + verified Architect inputs
→ validator.payload_fidelity.evaluate_ce_transaction
→ verified CE Stage Payload
→ fidelity replay
→ validator.verified_project_gate_exporter
→ Builder handoff when all pre-Builder conditions pass
```

The official CLI requires explicit `--review-draft`, `--source-intake`, `--source-bundle`, `--output`, `--repo-root`, and `--overwrite` inputs. No authoritative sibling-file discovery or `--intermediate-inputs` carrier is used.

## Adopted functional invariants

- strict JSON snapshots for every authoritative input;
- deterministic output/input alias rejection;
- exact-byte mutation detection;
- canonical serialization and atomic publication;
- post-write byte, Schema, semantic, identity, and transaction checks;
- restoration of prior owned output or removal of a failed new output;
- dirty Git state retained as metadata only.

## Retained PR #45 behavior

- one phase-aware Claim Policy Registry;
- one closed Action Contract Registry and normalized Action IR;
- derived class and Build Tree effects;
- source-type-specific original-artifact parsers;
- current-transaction repository-owned runtime execution when a supported implemented target exists;
- explicit downstream runtime obligations when execution is unavailable;
- legacy `ev4-ce-stage-payload@1.0.0` validation/preview without Builder authorization.

## Limitations

This reconciliation does not claim deployment, production readiness, real Elementor execution, or fresh independent review. Those states require separate evidence.
