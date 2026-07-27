# EV4-PCVP v1 dormant Constructability producer

This work unit prepares the existing CE Builder package boundary to add an
optional `continuation_assurance` carrier in a later activation change.

## Locked behavior

- Decision Kernel remains the canonical Policy, profile, and schema owner.
- The existing non-authoritative Constructability profile and four carrier
  schema copies remain pinned to immutable Decision Kernel commit
  `069a50fa243b01fa578a7c1bcb8864d9e796d34b`.
- The producer derives only from a Builder package that the existing CE runtime
  already classified as `executable_ready`.
- The carrier never treats CE Builder-readiness as Builder execution,
  Responsive completion, deployment, or production readiness.
- The external Builder mutation remains `AUTHORIZATION_REQUIRED` and preserves
  the existing owner confirmation boundary.

`PRODUCER_EMISSION_ENABLED` is hard-coded to `False`, the lock forbids caller
override, and no environment variable or public API can enable emission. The
active CE runtime returns the exact legacy Builder package without a carrier.

Changing emission belongs to a separate activation PR after tolerant consumers,
boundary verification, non-blocking trial evidence, and independent review.

Rollout status remains `not_yet_adopted`; activation effect remains `NONE`.
