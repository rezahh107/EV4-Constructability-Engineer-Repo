# CE Verified Constructability Proof Runtime v1.1

## Identity

```yaml
contract_id: ev4-ce-verified-constructability-proof-runtime@1.1.0
review_draft_schema: ev4-ce-review-draft@1.0.0
verified_payload_schema: ev4-ce-stage-payload@1.1.0
constructability_review_schema: ev4-constructability-review@1.1.0
builder_package_schema: ev4-builder-executable-package@1.0.0
claim_policy_registry: validator/claim_policy_registry.py
```

## Authority boundary

```text
Lean CE Review Draft
+ verified Architect intake
+ verified source bundle
+ CE-owned evidence adapters
→ claim-specific proof resolution
→ verifier-created VerifiedCEStagePayload
→ deterministic Project Gate export
```

The Draft is a `DECLARATION` of analysis and candidate evidence references. It does not carry Builder authorization.

Only the official runtime may mint:

- `VerifiedArtifactEvidence`;
- `VerifiedToolExecutionEvidence`;
- `VerifiedArchitectDecision`;
- `AttributedEngineeringJudgment`;
- `DownstreamTestObligation`;
- `VerifiedConstructabilityProof`;
- `VerifiedCEStagePayload`.

Exact-type immutable capability checks reject ordinary mappings, subclasses, copied state, test-only objects, stale source bytes, and mismatched target bindings.

## Claim ownership

| Claim | Authority owner | Accepted evidence | Unavailable behavior |
|---|---|---|---|
| `geometry` | CE | verified artifact or attributed engineering judgment | `INSUFFICIENT_EVIDENCE` |
| `overlay_strategy` | CE | verified artifact or attributed engineering judgment | `INSUFFICIENT_EVIDENCE` |
| `responsive_behavior` | downstream runtime validation | verified tool execution | `DOWNSTREAM_VALIDATION_REQUIRED` |
| `ui_control_path` | CE | verified artifact | `INSUFFICIENT_EVIDENCE` |
| `accessibility` | downstream runtime validation | verified tool execution | `DOWNSTREAM_VALIDATION_REQUIRED` |
| `dynamic_loop_approval` | Architect | verified Architect decision | `ARCHITECT_DECISION_REQUIRED` |
| `interaction_approval` | Architect | verified Architect decision | `ARCHITECT_DECISION_REQUIRED` |
| `asset_source` | CE | verified artifact | `INSUFFICIENT_EVIDENCE` |
| `placeholder_policy` | CE | attributed engineering judgment | `INSUFFICIENT_EVIDENCE` |
| `QA` | downstream runtime validation | verified tool execution | `DOWNSTREAM_VALIDATION_REQUIRED` |
| `constructability_status` | CE runtime | derived only | blocked |
| `builder_eligibility` | CE runtime | derived only | blocked |

The executable registry in `validator/claim_policy_registry.py` is canonical when this summary and runtime code differ.

## Evidence modes

### `VERIFIED_ARTIFACT`

Requires exact source bytes, source identity, claim identity, Payload identity, and subject binding. A digest establishes source integrity, not claim correctness; the claim policy must still admit the artifact mode.

### `VERIFIED_TOOL_EXECUTION`

Requires runtime-captured tool identity, version or commit, method or command, target identity, timestamps, successful exit code, and result digest. Caller-authored tool metadata is not accepted as execution evidence.

### `VERIFIED_ARCHITECT_DECISION`

Requires the exact verified Architect intake, decision JSON Pointer, selected candidate identity, subject binding, and source digest. CE cannot create Architect approval.

### `ATTRIBUTED_ENGINEERING_JUDGMENT`

Retains reviewer identity, premises, derivation method, limitations, and claim semantics. It may support only claims whose policy admits CE judgment. It is not represented as source fact or tool execution.

### `DOWNSTREAM_TEST_OBLIGATION`

Records the consumer stage, required test, blocking behavior, and completion criteria. It remains explicitly unproven and blocks Builder authorization until replaced by policy-compatible evidence.

## Derived outputs

The assembler derives and callers cannot override:

- `geometry_proven`;
- `overlay_strategy_proven`;
- `responsive_behavior`;
- `interaction_approved`;
- `dynamic_loop_approved`;
- `ui_control_evidence_present`;
- `accessibility_evidenced`;
- node status;
- `constructability_status`;
- `payload_status`;
- unresolved evidence;
- Evidence Register records;
- Builder package emission and status;
- Builder eligibility;
- `handoff.allowed`.

## Legacy compatibility

```yaml
legacy_payload_schema: ev4-ce-stage-payload@1.0.0
legacy_payload_validation_supported: true
legacy_payload_authorization_supported: false
legacy_preview_assurance_kind: DECLARATION
legacy_preview_verification_status: MANUAL_UNVERIFIED
successor_verified_payload_required_for_handoff: true
builder_contract_breaking_change: false
```

Historical Payloads and fixtures are preserved. They may be validated, diagnosed, displayed, or migrated to Draft form. They cannot mint a verified Payload or produce `handoff.allowed=true`.

## Preserved transaction controls

- exact source snapshots and second-read equality;
- source intake and source bundle binding;
- selected candidate and approved class identity preservation;
- Git provenance collection;
- dirty-worktree blocking;
- synthetic-evidence derivation and blocking;
- deterministic canonical serialization;
- atomic publication;
- persisted-byte validation;
- export identity verification;
- transaction authorization recomputation;
- compatible `ev4-builder-executable-package@1.0.0` validation.

## Non-claims

This contract does not claim real Elementor execution, responsive completion, accessibility completion, Project Gate consumer acceptance, Builder execution, deployment, or production readiness without external compatible evidence.
