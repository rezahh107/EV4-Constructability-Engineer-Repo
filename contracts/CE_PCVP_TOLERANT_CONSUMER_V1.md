# CE PCVP Tolerant Consumer v1

Status: additive dormant reader
Policy: `EV4-PCVP@1.0.0`
Architecture lock: `EV4-PCVP-ROLL-LOCK-20260727-R1`
Compatibility mode: `DUAL_READ`

## Boundary

The canonical Architect-facing intake remains:

```text
ev4-ce-architect-stage-intake@1.1.0
```

That intake may now contain the optional canonical field:

```text
$.continuation_assurance
```

When the field is absent, current legacy behavior is unchanged. When present,
the CE intake reader validates the exact immutable Decision Kernel carrier
schemas and the repository-correct Constructability profile before the intake
can be treated as verified.

The local schemas and profile are byte-pinned, non-authoritative copies. The
canonical owner remains `rezahh107/EV4-Decision-Kernel`.

## Mechanically enforced behavior

- exact `EV4-PCVP@1.0.0` identity;
- incoming `source_stage=ARCHITECT`;
- global Claim, Effect, and Authorization ID uniqueness;
- resolvable Claim dependencies and Effect references;
- referenced Authorization is active, covering, scope-equal, and bound to the
  `ARCHITECT → CONSTRUCTABILITY_ENGINEER` edge;
- safe reversible defaults cannot authorize external or irreversible Effects;
- a critical contradicted dependency blocks its Effect;
- Stage Summary references only the current Effect and its dependencies;
- GREEN, YELLOW, and RED projections are derived from current dependencies
  rather than trusted as independent authority.

Inactive Authorization records may remain in carrier history, but an Effect
cannot use one as current permission. Uncertainty outside the current Effect's
explicit dependencies does not alter its projection.

## Explicit non-goals

This reader does not:

- emit a CE-authored PCVP carrier into Builder or Project Gate outputs;
- load PCVP as an active runtime policy;
- change CE constructability, Builder-ready, Runtime, or final-gate authority;
- claim adoption, activation, validation of real external artifacts, release
  readiness, or production readiness;
- replace current CE schemas, validators, deterministic evaluation, or export.

Producer support remains a separate dormant work step after downstream
consumers are tolerant. Strict activation remains a separate decision after
boundary verification.
