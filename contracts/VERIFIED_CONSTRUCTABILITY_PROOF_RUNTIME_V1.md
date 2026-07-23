# Verified Constructability Proof Runtime v1

Status: proposed successor runtime contract  
Owner: `rezahh107/EV4-Constructability-Engineer-Repo`  
Runtime: `ev4-ce-verified-constructability-runtime@1.0.0`

## Purpose

This contract separates model- or operator-authored CE analysis from authority-bearing proof.

```text
CE Review Draft
→ Claim Policy
→ CE-owned Evidence Adapters
→ Proof Resolver
→ VerifiedCEStagePayload
→ compatibility projection
→ existing deterministic Project Gate transaction
```

The compatibility projection remains `ev4-ce-stage-payload@1.0.0` because the pinned Project Gate Stage Evidence Bundle and Builder package contracts are unchanged. The authority-bearing successor is `ev4-ce-stage-payload@1.1.0`; only the official runtime may mint its opaque `VerifiedCEStagePayload` capability.

## Assurance distinctions

The runtime applies the following meanings:

- `DECLARATION`: caller-authored statement with no verification authority.
- `ATTESTATION`: attributed engineering judgment with reviewer, premises, method, and limitations.
- `INTEGRITY_RECEIPT`: byte or identity integrity only; it does not establish claim correctness.
- `EVIDENTIARY_RECEIPT`: claim-specific source/execution binding compatible with the authority effect.

Schema validity, field presence, a hash, or a non-empty object does not independently establish factual truth.

## Contracts

```yaml
review_draft:
  schema_id: ev4-ce-review-draft@1.0.0
  authority: non_authoritative_analysis

verified_payload:
  schema_id: ev4-ce-stage-payload@1.1.0
  authority: verifier_created_capability

legacy_projection:
  schema_id: ev4-ce-stage-payload@1.0.0
  authority: derived_compatibility_projection_only

builder_package:
  schema_id: ev4-builder-executable-package@1.0.0
  breaking_change: false
```

## Claim ownership

The canonical registry is `policies/constructability_claim_policy.v1.json`.

Required claims include:

- `geometry`
- `overlay_strategy`
- `responsive_behavior`
- `ui_control_path`
- `accessibility`
- `dynamic_loop_approval`
- `interaction_approval`
- `asset_source`
- `placeholder_policy`
- `qa`
- `constructability_status`
- `builder_eligibility`

`dynamic_loop_approval` and `interaction_approval` are Architect-owned. CE engineering judgment cannot mint these decisions.

Runtime-only responsive, accessibility, and QA outcomes become explicit downstream test obligations unless compatible verified execution or runtime artifact evidence is available.

## Capability boundary

Production capability checks require:

- exact production type;
- runtime-minted object identity;
- immutable retained state;
- exact Payload binding;
- exact Architect intake digest;
- exact source bundle digest;
- exact selected candidate;
- exact subject binding;
- production capability, not a fixture/test capability.

Plain dictionaries, copied state, subclasses, manually constructed lookalikes, stale capabilities, wrong-source capabilities, and test-only capabilities are rejected.

## Official export boundary

The official CLI accepts `--review-draft`, not a raw CE Stage Payload.

A raw Payload may be:

- schema/semantic diagnosed;
- rendered as a non-authoritative preview;
- migrated to a CE Review Draft.

It cannot independently produce `handoff.allowed=true`.

The in-process compatibility API `export_file(...)` accepts a path only when the exact canonical projection is already registered to a live production `VerifiedCEStagePayload` minted by the official assembler in that process. An arbitrary file with matching shape, fields, or hashes is rejected.

## Derived state

The assembler derives and callers cannot override:

- `geometry_proven`
- `overlay_strategy_proven`
- `responsive_behavior`
- `interaction_approved`
- `dynamic_loop_approved`
- `ui_control_evidence_present`
- `accessibility_evidenced`
- Node status
- `constructability_status`
- `payload_status`
- Evidence Register
- unresolved evidence
- downstream test obligations
- Builder package emission
- Builder eligibility

## Evidence Register

Official evidence records are runtime-produced. Each record retains claim, subject, producer, target binding, assurance kind, and a source or execution digest appropriate to its mode.

A hash of an evidence record is not substituted for a hash of the supporting source.

## Existing controls preserved

The verified wrapper retains the existing:

- Architect intake validation;
- exact source binding;
- selected-candidate and class identity checks;
- Builder package validation;
- Git provenance and dirty-worktree block;
- synthetic-evidence block;
- deterministic serialization;
- atomic publication;
- input/output alias protection;
- persisted-byte validation;
- output identity verification;
- transaction authorization recomputation.

The persisted transaction additionally recomputes the verifier-derived claim resolution before accepting `handoff.allowed=true`.

## Migration

```yaml
legacy_payload_validation_supported: true
legacy_payload_authorization_supported: false
successor_verified_payload_required_for_handoff: true
builder_contract_breaking_change: false
historical_payload_schema_rewritten: false
```
