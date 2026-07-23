# CE Review Draft Migration v1.1

## Scope

This guide migrates historical manually authored `ev4-ce-stage-payload@1.0.0` content into the non-authoritative `ev4-ce-review-draft@1.0.0` input.

It does not convert historical proof assertions into verified evidence.

## Field treatment

### Preserve as analysis

Move these meanings into the Draft when present:

| Historical meaning | Draft destination |
|---|---|
| reviewed Node identity | `reviewed_nodes[].node_id` |
| proposed implementation action | `reviewed_nodes[].proposed_action` |
| engineering explanation | `reviewed_nodes[].engineering_rationale` |
| required proof question | `reviewed_nodes[].requested_claims[]` |
| source path or decision pointer candidate | `reviewed_nodes[].candidate_source_refs[]` |
| assumptions | `reviewed_nodes[].assumptions[]` |
| limitations and unresolved evidence | `reviewed_nodes[].limitations[]` and `unresolved_questions[]` |
| implementation strategy | `implementation_strategy_proposal` |
| proposed Builder actions | `builder_action_proposals[]` |
| runtime-only unfinished proof | `downstream_test_obligations[]` |

### Never preserve as authority

Discard or diagnose these caller-authored states rather than copying them into the Draft:

```text
*_proven
responsive_behavior=evidence_backed
interaction_approved
dynamic_loop_approved
accessibility_evidenced
ui_control_evidence_present
evidence_register.state=validated
payload_status
constructability_status
builder_package_status
builder_package_emitted
verification_status
handoff.allowed
```

Do not copy caller-authored `producer`, `source_sha256`, `tool_identity`, `run_id`, `method`, or `verification_status` as verified provenance. Keep a source path or decision pointer only as a candidate reference for an official adapter.

## Migration result

A migrated Draft has this assurance:

```yaml
assurance_kind: DECLARATION
contains_engineering_analysis: true
contains_verified_proof_authority: false
may_request_official_source_verification: true
may_authorize_builder_handoff: false
```

## Official continuation

```text
migrated Draft
→ verify exact Architect intake and source bundle
→ resolve candidate source references through CE adapters
→ attribute permitted CE judgment
→ create downstream obligations for unavailable runtime evidence
→ assemble VerifiedCEStagePayload
→ run official deterministic export
```

## Legacy preview

The historical raw Payload path remains available for diagnostics and preview. Its fixed result is:

```yaml
assurance_kind: DECLARATION
verification_status: MANUAL_UNVERIFIED
official_builder_authorization: false
handoff.allowed: false
```

It cannot silently upgrade into the successor authority path.
