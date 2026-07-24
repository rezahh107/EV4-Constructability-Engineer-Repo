# CE Phase-Aware Builder Lifecycle v1.1

## Status

Active local successor contract merged through `PR #45` into `main`.

It does not modify the public Builder package or Project Gate envelope contracts.

## Lifecycle

```text
Canonical Architect Intake
+ Canonical Source Bundle
+ CE Review Draft
→ phase-aware claim derivation
→ closed Action IR
→ pre-Builder evaluation
→ mandatory runtime obligations
→ CE Builder-ready Payload
→ Builder execution
→ actual runtime-obligation validation
→ Final Project Gate
```

The following states are independent:

```text
CE Builder-ready
Runtime validated
Production ready
```

`payload_status=complete` means the CE stage is complete and an eligible Builder package may be emitted. It does not mean that post-Builder runtime claims passed and never means production-ready.

## Claim phases

Every canonical claim declares exactly one phase:

- `pre_builder_static`: CE or Architect decisions required before Builder handoff;
- `pre_builder_capability`: original-source or bounded capability evidence required before handoff;
- `post_builder_runtime`: an implemented target is required and CE carries a deterministic obligation until an actual runner can validate it.

A mandatory runtime claim with no complete obligation blocks Builder handoff. A complete obligation with `status=required` does not block Builder, but blocks Final Project Gate.

## Runtime obligation

```yaml
obligation_id:
claim_id:
subject_ref:
consumer_stage: post_builder_runtime_validation
required_runner:
target_identity:
required_inputs: []
expected_assertions: []
completion_criteria:
blocking_boundary: final_project_gate
status: required | executed_pass | executed_fail | not_applicable
blocks_builder_handoff: false
blocks_final_completion: true
```

An obligation is a required future validation transaction. It is not execution evidence.

The obligation identity, claim, subject, runner, target, required inputs, and assertions must be deterministic and complete. A missing, malformed, duplicate, or incorrectly bound obligation is a pre-Builder correctness failure.

## Runtime evidence boundary

A JSON document containing `observed`, `observed_layout`, `accessible_name`, `passed`, `execution_status`, `exit_code`, `captured_result`, or similar authored result fields is a declaration and cannot produce `VERIFIED_TOOL_EXECUTION`.

A runtime claim may become executed only when a repository-owned runner invokes a real command or tool, generates observations internally, binds the result to the exact implemented target and current transaction, and returns an accepted pass.

No Browser, Elementor, accessibility, interaction, or QA runner currently exists in this repository. These claims therefore remain downstream obligations during normal CE-to-Builder handoff.

## Original-source evidence boundary

`VERIFIED_ARTIFACT` requires:

```text
original source bytes
→ claim-specific repository parser
→ derived facts
→ semantic comparison
```

Supported local source types are JSON, HTML, CSS, and SVG. A caller-authored `facts` envelope is not an original source. A cached extract is accepted only when the repository parser regenerates identical facts from the original source.

## Action IR

The single Action Contract Registry defines accepted actions, parameters, aliases, effects, claims, and permissions. Every accepted proposal is normalized into:

```yaml
action_id:
action_type:
target_node:
normalized_parameters:
derived_effects:
required_claims:
required_permissions:
decision_state:
source_draft_path:
```

Raw Draft parameters are not exported. Builder package actions are projected from normalized Action IR only.

## Canonical evaluation and export

```text
validator.payload_fidelity.evaluate_ce_transaction
→ validator.payload_assembler
→ verified ev4-ce-stage-payload@1.1.0
→ validator.verified_project_gate_exporter
```

The historical raw `ev4-ce-stage-payload@1.0.0` route remains validation and migration-preview only and cannot authorize Builder handoff.

## Compatibility

```yaml
builder_package_schema: ev4-builder-executable-package@1.0.0
producer_gate_export_contract: unchanged
project_gate_transaction_boundary: unchanged
ce_payload_schema: ev4-ce-stage-payload@1.1.0
legacy_payload_validation_supported: true
legacy_payload_authorization_supported: false
```

## Threat-model boundary

This contract addresses functional correctness. Cryptographic attestation, hostile in-process caller resistance, privilege tokens, plugin sandboxing, and production deployment are outside scope.