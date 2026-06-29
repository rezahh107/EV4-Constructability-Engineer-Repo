# Implementation Strategy Gate

This repository is the EV4 implementation strategy gate between Architect and Builder.

## Gate Question

Can Builder execute the next action without guessing?

If the answer is no, the package is not builder-ready.

## Fail-Closed Behavior

The gate fails closed by default. Missing proof is not neutral. Missing proof blocks execution or requests evidence.

## Builder Package Is Not a Design Document

A Builder Executable Package must contain executable decisions, not open questions. If Builder must choose between implementation strategies, the package is invalid.

Examples of invalid Builder decisions:

- choose unified SVG or independent SVG connectors
- guess card anchors
- choose overlay containment model
- choose z-index stack
- decide whether cards are clickable
- decide whether repeated cards are Dynamic Loop
- decide responsive behavior

## Safe Output Routes

The Engineer may output:

- blocked
- needs_user_evidence
- needs_architect_amendment
- executable_with_logged_assumption
- executable_ready

Only executable_ready emits a Builder Executable Package.
