# EV4 Constructability Engineer Repo

Mutable status authority: `STATUS.md`

Role: `implementation_strategy_gate`

## Purpose

EV4 Constructability Engineer sits between Architect and Builder. It determines whether approved architecture can be implemented safely without forcing Builder to guess.

```text
Architect says what should be built.
CE proves how it can be safely built.
Builder executes proven strategy.
Responsive validates post-build responsive behavior.
```

Core rule:

```text
not proven executable → not builder-ready
```

## EV4 Project Gate Workflow

CE participates in two planned gates:

```text
Architect output
→ EV4 Project Gate
→ accepted CE Input Package
→ CE review and output
→ CE Project Gate Export artifact
→ EV4 Project Gate runtime integration
→ accepted Builder Input Package
```

If Architect input fails the first gate, the user receives an Architect repair package. If CE output fails the second gate, the user receives a CE repair package or an Architect amendment package only when evidence establishes upstream ownership.

The CE repository owns a producer-emitted Project Gate artifact path for CE output. Project Gate runtime integration remains outside this repository.

## Canonical Architect-facing CE intake

For Project Gate-produced Architect Stage Payload work, the canonical CE-owned Architect-facing intake is:

```text
ev4-ce-architect-stage-intake@1.1.0
```

Accepted upstream source:

```text
ev4-architect-stage-payload@1.0.0
```

Declarative mapping contract:

```text
ev4-architect-stage-to-ce-intake-mapping@1.1.0
```

v1.1 adds a required `project_gate_transition` record so an executed `ev4-architect-to-ce-transition@1.0.0` can be represented truthfully without implying CE review, implementation strategy, Builder authorization, or real Elementor validation.

Historical compatibility-only Architect Stage intake files remain available:

```text
contracts/CE_ARCHITECT_STAGE_INTAKE_V1.md
contracts/ARCHITECT_STAGE_TO_CE_INTAKE_MAPPING_V1.md
schemas/ce_architect_stage_intake.v1.schema.json
```

The older legacy compatibility-only intake files also remain available:

```text
contracts/ARCHITECT_TO_CE_INPUT_MAPPING_V1.md
schemas/architect_ce_input_package.v1.schema.json
```

Those files target previous compatibility paths and must not be treated as the preferred intake for Project Gate-produced v1.1 transition output.

## CE Project Gate Producer Export

CE producer adoption uses these CE-owned artifacts:

```text
manifests/ce_pipeline_manifest.v1.json
schemas/ce_pipeline_manifest.v1.schema.json
schemas/ce_stage_payload.v1.schema.json
contracts/project-gate/producer-gate-export.v1.schema.json
contracts/project-gate/producer-gate-export.v1.lock.json
validator/project_gate_export.py
scripts/validate-project-gate-producer-adoption.py
```

Composition:

```text
CE Stage Payload
inside Stage Evidence Bundle v1
inside Producer Gate Export v1
```

The vendored Producer Gate Export contract is pinned to Project Gate merge commit:

```text
ea19c22c32458068e167b267da8b819e9263cdf7
```

Silent fallback is forbidden. A blocked CE run may still emit a valid machine artifact, but that artifact is not Builder authorization.

## CE Input and Output

CE receives only an Architect package accepted for constructability review.

CE output may become Builder-ready only when implementation strategy is proven and Builder has no remaining strategy decisions.

Expected Builder-ready conditions include:

```text
builder_executable_package.schema is ev4-builder-executable-package@1.0.0
selected_candidate_id remains locked
approved class intent remains preserved
blocking dependencies are empty
builder_decisions_required is zero
implementation strategy is explicit
first safe Builder batch is present
structured confirmation data is present
production readiness remains false
```

For visual-reference Builder packages, CE must keep reference carriers structured. In particular, `paradigm_to_structure_map.connector_layer` remains `{node, model}` in CE output; the downstream CE→Builder adapter owns any Builder-side `node:model` projection. See `docs/CE_TO_BUILDER_PRODUCER_CONTRACT.md`.

Typical CE concerns include geometry, source and target anchors, assets, overlays, z-index, responsive scope, interaction, Dynamic Loop, accessibility evidence, and exact Elementor UI-control evidence.

## Authority

This repository remains authoritative for its own constructability schemas, validators, fixtures, failure patterns, strategy rules, and Builder-ready package semantics.

EV4 Project Gate verifies the real CE-to-Builder path using official CE validation, the documented adapter, Builder intake validation, and preservation checks. It does not redesign architecture, invent strategy, replace CE contracts, or silently repair CE output.

When responsibility cannot be established:

```yaml
status: insufficient_evidence
repair_owner: unresolved
```

## Repair Loop

A future CE repair package will explain the confirmed problem in plain Persian, identify affected contract data, retain the original output identity, and state what valid data must remain unchanged. The corrected complete CE output is checked again before Builder receives it.

## CE Status Values

```text
executable_ready
blocked
needs_user_evidence
needs_architect_amendment
executable_with_logged_assumption
```

`executable_with_logged_assumption` is limited to explicit, low-risk, reversible, boundary-safe assumptions that leave no Builder strategy decision.

## Boundaries

CE does not redesign architecture, rescore candidates, change `selected_candidate_id`, act as Builder, or claim production readiness.

## Companion Repositories

```text
https://github.com/rezahh107/EV4-Project-Gate
https://github.com/rezahh107/EV4-Architect-Repo
https://github.com/rezahh107/EV4-Builder-Assistant-Repo
https://github.com/rezahh107/EV4-Responsive-Architect
```

## Current Status Authority

Current mutable implementation and readiness claims are maintained only in:

```text
STATUS.md
```

This README describes stable mission, contracts, and boundaries. It must not be used as the current mutable status authority. When README wording, `STATUS.md`, and live repository evidence differ, live default-branch evidence wins and `STATUS.md` must be reconciled.

---

## CE Conversation Quick Start

Canonical machine-readable startup contract:

```text
manifests/ce-conversation-bootstrap.v1.json
```

<!-- EV4_CE_BOOTSTRAP_QUICK_START_START -->
```text
1. Create or open the CE ChatGPT Project and load `release/EV4_CE_PROJECT_RELEASE_PACK_v1/PROJECT_INSTRUCTIONS.md` as the Project Instructions.
2. Send the exact normalized message `شروع`.
3. Upload the standalone `ce-input.json` produced by `EV4-Project-Gate / architect-to-ce`.
4. Upload the exact Architect source bundle whose canonical SHA-256 is declared by that CE input.
5. Treat any Receipt-like attachment as `diagnostic_untrusted` until official external Receipt validation succeeds.
6. Never extract nested `result.output`, rebuild CE input manually, or continue on mixed/conflicting attachments.
7. Only successful integrated authorization + intake validation + source binding may route to `architect_intake_validation`.
```
<!-- EV4_CE_BOOTSTRAP_QUICK_START_END -->

```text
exact normalized شروع + no maintenance intent
→ authorized CE bootstrap context
→ standalone ce-input.json + exact source bundle
→ official intake validation + validate_source_bundle_binding()
→ architect_intake_validation only
```

A valid attachment without the exact startup trigger or an already authorized `active_ce_run` does not create a CE run. Repository-maintenance intent always routes to `repository_maintenance`, even when the message contains `شروع`.

The normal filename `ce-input.json` is a convention, not proof. Acceptance requires parsed content matching `ev4-ce-architect-stage-intake@1.1.0`, official CE semantic validation, and successful source-bundle byte binding.

Receipt-like files are not validated audit evidence from `schema_version` alone. Until official external validation succeeds, they remain `receipt_validation_status: unverified` with `receipt_role: diagnostic_untrusted`; they never become CE semantic input. Mixed or conflicting candidates block automatic selection.

Never extract nested `result.output` or rebuild CE input manually. Bootstrap authorizes no Constructability conclusion, hidden-dependency inference, implementation strategy, Builder package, Builder readiness, Responsive completion, deployment, or production readiness.
