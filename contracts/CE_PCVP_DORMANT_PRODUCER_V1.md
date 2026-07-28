# EV4-PCVP v1 dormant Constructability producer

This work unit preserves the active CE runtime as carrier-free and exposes one
explicit dormant derivation API for later boundary verification.

## Locked behavior

- Decision Kernel commit `069a50fa243b01fa578a7c1bcb8864d9e796d34b`
  remains the canonical profile and schema authority.
- One fixed CE-local identity descriptor validates the Lock, profile, four schema
  mirrors, canonical paths, local paths, non-authoritative flags, and fixed
  digests. The mutable Lock is validated data, not digest authority.
- `validator.payload_assembler` has no producer import, attachment call, flag, or
  alternate activation surface. Active output remains the exact legacy Builder
  package without `continuation_assurance`.
- `derive_continuation_assurance(...)` accepts only authoritative Architect
  intake/source mappings with their exact bytes, a CE Review Draft, repository
  root, and supported runtime execution requests.
- The dormant derivation re-verifies source identity, reruns the existing CE
  evaluator, performs fidelity replay, validates the complete Builder package
  schema, then privately projects and validates the carrier.
- Raw Builder packages, persisted payloads, caller-completed runtime results,
  mismatched bytes, malformed inputs, and coordinated Lock-plus-file drift fail
  closed.
- Builder execution, Responsive completion, deployment, and production readiness
  remain `UNVERIFIED`; the external Builder mutation remains
  `AUTHORIZATION_REQUIRED` with no Authorization record.

Rollout status remains `not_yet_adopted`; activation effect remains `NONE`.
