# CE Validation Transaction Audit

Status: `implemented_pending_fresh_independent_review`  
Final live base audited: `9b80da790426912d662b7e55cef4e51edbf8d495`  
Starting observed main: `2a483b1a78651b3a23f334cf8ec2f877fd930a6a`  
Scope: CE startup through Project Gate export and Builder handoff gating.

The base advanced through merged PR #41 during the audit. Its canonical `payload.data` owner-path repair was integrated before final validation.

This document is an audit record. Enforcement exists only where the table names executable code, tests, or CI. Documentation text is not authorization.

## Executable state machine

| State | Executable owner | Input carrier | Required predecessor | Authorization predicate | Output | Deterministic failure / repair owner |
|---|---|---|---|---|---|---|
| startup classification | `scripts/ce_bootstrap_routing.py` | routing request | none | exact NFC-normalized `شروع` or an already-authorized active CE run; repository-maintenance intent has precedence | explicit routing result | non-authorizing route / CE |
| attachment classification | `scripts/ce_bootstrap_routing.py` | exact captured attachment bytes | authorized CE context | exactly one canonical CE intake, exactly one source bundle, no conflicting semantic or receipt-like carrier | classified snapshots | blocked ambiguity/conflict / caller or upstream owner |
| source binding | official intake validator plus bootstrap routing | captured CE intake and source-bundle snapshots | valid attachment set | bundle ID, canonical digest, transition identity, producer identity, upstream owner, and second-read equality all pass | `architect_intake_validation` route | structured binding diagnostic / Architect or Project Gate |
| Architect intake validation | `scripts/validate-ce-architect-stage-intake.py` | private snapshots of intake and source bundle | source binding | active v1.1 contract and semantic rules pass | intake report | invalid or `insufficient_evidence` / Architect or Project Gate |
| CE payload validation | `validator/engine.py` and CE payload validator | captured CE payload snapshot | accepted intake | schema, semantic, constructability, identity, evidence, and package rules pass | validated in-memory payload | no artifact publication / CE |
| Project Gate export construction | `validator/ce_validation_transaction.py` | captured payload, intake, and source bundle | all prior validation | all snapshots remain byte-stable and all required identities agree | in-memory Producer Gate Export | no publication / CE or repository owner |
| handoff recomputation | `validator/ce_validation_transaction.py` | complete export | constructed export | payload status, unresolved evidence, constructability, package eligibility, mandatory stage status, synthetic state, and official semantic validation all agree | allowed or blocked handoff | deterministic non-authorizing diagnostic / CE |
| publication | `validator/project_gate_exporter.py` | validated canonical bytes | successful construction | output is inside repo, not an input alias, and any overwritten target is CE-owned | atomically written output | invalid candidate removed or prior owned artifact restored / repository owner |
| post-write verification | `validator/project_gate_exporter.py` | exact persisted bytes | publication | byte equality, schema, semantic, transaction authorization, and export identity all pass | final result dimensions | non-authorizing result; invalid target marked non-consumable / repository owner |

## Authority-bearing field classification

| Surface | Classification | Rule |
|---|---|---|
| routing request `operating_mode`, attachments, receipt text | caller assertion | never authorizes without executable recomputation |
| bootstrap `activation_authorized`, `pipeline_execution` | derived result | computed only by canonical routing path |
| intake negative boundary assertions | diagnostic/contract boundary | cannot grant CE or Builder authority |
| CE payload status and Builder package fields | caller-authored carrier values | schema and semantic validators recompute eligibility |
| export `validation.*` | derived integrity result | integrity does not imply authorization |
| export `handoff.allowed` | derived authorization result | independently recomputed before and after publication |
| output filename or existing JSON shape | non-authorizing | overwrite requires exact CE ownership markers |

## Invariants

| ID | Result | Executable evidence |
|---|---|---|
| `CE-TRX-001` | implemented | integrated bootstrap authorization and captured-input routing |
| `CE-TRX-002` | preserved | repository-maintenance precedence from PR #40 |
| `CE-TRX-003` | implemented | exact payload/intake/source snapshots plus second-read equality |
| `CE-TRX-004` | implemented for active surfaces | handoff and provenance assertions are recomputed or rejected |
| `CE-TRX-005` | partially implemented | active intake/payload/export identities agree; canonical intake/payload do not currently carry a common Kernel `decision_lineage` carrier |
| `CE-TRX-006` | implemented for active carriers | ambiguity/conflict and mixed evidence fail closed |
| `CE-TRX-007` | implemented | official CE semantics and Builder package eligibility gate handoff |
| `CE-TRX-008` | implemented | malformed/duplicate/incomplete inputs produce structured failures and no authorized partial output |
| `CE-TRX-009` | implemented | integrity, semantic status, authorization, publication, and consumability are reported separately |
| `CE-TRX-010` | implemented | input aliases and unowned overwrite targets are rejected; failed overwrite restores prior CE-owned output |
| `CE-TRX-011` | preserved | current public contract IDs remain unchanged and existing lock validators remain active |
| `CE-TRX-012` | implemented | CI runs focused semantic mutation tests; this document does not describe prose as enforcement |

## Confirmed limitations

1. The active `ev4-ce-architect-stage-intake@1.1.0` and `ev4-ce-stage-payload@1.0.0` contracts do not expose one shared canonical Kernel `decision_lineage` field. The existing sequence validator therefore remains synthetic/fixture evidence and is not represented here as runtime end-to-end lineage enforcement.
2. Closing that gap requires an explicit cross-repository contract revision and upstream producer migration. This bounded repair does not invent a CE-only competing lineage carrier or silently bump a public contract.
3. Project Gate runtime acceptance, Builder acceptance, real Elementor execution, Responsive completion, deployment, and production readiness remain unverified.
