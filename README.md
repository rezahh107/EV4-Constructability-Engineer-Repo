# EV4 Constructability Engineer Repo

Status: mvp_design_ready  
Role: `implementation_strategy_gate`  
Position: between `EV4 Architect` and `EV4 Builder Assistant`  
Default behavior: fail-closed

---

## Summary

`EV4 Constructability Engineer` is the implementation strategy gate for the EV4 Elementor V4 pipeline.

It inspects Architect output before Builder receives it. Its job is to prove whether the approved architecture is actually executable without forcing Builder to guess.

```text
Architect says what should be built.
Constructability Engineer proves how it can be safely built.
Builder executes only proven strategy.
Responsive Architect validates and repairs post-build responsive behavior.
```

Core principle:

```text
Approved architecture ≠ approved implementation strategy.
```

Default rule:

```text
not proven executable → not builder-ready
```

---

## Why This Repo Exists

The Smart Home Connector section exposed a missing role boundary.

The Architect output approved:

```text
- a decorative connector layer
- an Association Lines / SVG node
- connector visual intent between feature cards and a central house visual
```

But connector execution also required:

```text
- source anchors for each feature card
- target anchor for the house visual
- geometry mapping method
- overlay containment strategy
- z-index / positioning model
- decision between unified SVG, independent SVG connectors, CSS lines, or temporary skip
- fallback / repair policy if visual alignment drifts
```

The Builder generated one integrated SVG connector and attempted to repair drift with scale, transform, and absolute positioning guesses. That was the wrong reasoning layer.

The real issue was not CSS sizing. The real issue was unresolved geometry mapping and unresolved implementation strategy.

---

## Repository Role

This repository owns:

```text
- constructability review
- hidden execution dependency detection
- implementation strategy mapping
- blocking vs non-blocking dependency classification
- user evidence requests
- Architect amendment requests
- Builder Executable Package emission only when safe
```

This repository must not:

```text
- redesign architecture
- rescore architecture
- change selected_candidate_id
- add or remove approved class names unless explicit Architect amendment allows it
- act as a second Builder
- emit Builder instructions when Builder still has to decide strategy
- claim production readiness
```

---

## System Flow

```text
EV4 Architect Repo
        │
        │ approved architecture / handoff
        ▼
EV4 Constructability Engineer Repo
        │
        │ Builder Executable Package only if executable_ready
        ▼
EV4 Builder Assistant Repo
        │
        │ real Elementor execution evidence
        ▼
EV4 Responsive Architect
```

---

## Constructability Status Enum

```text
executable_ready
blocked
needs_user_evidence
needs_architect_amendment
executable_with_logged_assumption
```

Use `executable_with_logged_assumption` only when all are true:

```text
- risk is low
- action is reversible
- assumption is explicit
- assumption is visible in the output
- no architecture boundary is crossed
- builder_decisions_required == 0
```

---

## Builder Executable Package Gate

A Builder package may be emitted only when:

```yaml
builder_package_status: executable_ready
builder_decisions_required: 0
blocking_dependencies: []
selected_candidate_locked: true
selected_candidate_id_unchanged: true
approved_class_names_unchanged: true
confirmation_request: present
first_safe_builder_batch: present
```

Allowed remaining unknowns:

```yaml
production_ready: false
frontend_qa: not_checked
responsive_final_qa: not_checked
browser_rendering: not_checked
```

These unknowns are allowed only when they do not block the next Builder action.

---

## Action Interrogation Protocol

For every executable node or proposed Builder action, Engineer asks:

```text
1. Does this action require geometry?
2. Are source anchors and target anchors defined or measured?
3. Does this action require an external asset?
4. If the asset is missing, is there an explicit placeholder policy?
5. Does this action require overlay / z-index / containment strategy?
6. Does this action imply responsive behavior?
7. If responsive is unknown, is the current scope explicitly desktop-only?
8. Does this action imply interaction?
9. Does this action imply Dynamic Loop or data binding?
10. Does this action make an accessibility claim?
11. Does this action use an exact Elementor UI control path?
12. Is the action reversible if wrong?
13. Would a wrong assumption force meaningful rework?
14. Does this action require changing approved structure or class names?
15. Does this action require Architect amendment?
```

Rule:

```text
Silence from Architect is not proof of executability.
```

---

## Failure Pattern Library MVP

```text
FP-01 geometry_dependency_not_proven
Connector lines, arrows, visual relationships, decorative overlays between elements.

FP-02 asset_dependency_not_proven
Image/SVG/icon/background asset referenced without source or placeholder policy.

FP-03 overlay_strategy_not_proven
Absolute/fixed/decorative layer without containment, positioning, or z-index model.

FP-04 responsive_behavior_implied_not_defined
Mobile/tablet/breakpoint behavior without evidence or explicit block.

FP-05 interaction_implied_not_confirmed
Clickable cards, hover states, tabs, accordions, modals, toggles.

FP-06 dynamic_loop_not_approved
Repeated elements assumed to use Dynamic Loop or data binding without approval.

FP-07 accessibility_claim_without_evidence
Accessibility, ARIA, semantic, keyboard, or WCAG claims without proof.

FP-08 ui_control_path_uncertainty
Exact Elementor control path without current UI, user statement, installed version, or official docs evidence.
```

---

## Validator Rules MVP

```text
R01 builder_decisions_required must be 0 for executable_ready.
R02 blocking_dependencies must be empty for executable_ready.
R03 geometry_required requires geometry_proven.
R04 asset_required requires asset source or placeholder policy.
R05 overlay_strategy_required requires overlay_strategy_proven.
R06 responsive actions require evidence-backed strategy or explicit block.
R07 interaction requires approval.
R08 Dynamic Loop requires approval and data binding map.
R09 structure/class changes require explicit Architect permission.
R10 exact UI control paths require evidence.
R11 executable_ready requires structured confirmation_request and first_safe_builder_batch.
R12 production_ready requires separate QA evidence.
R13 logged assumptions must be low-risk, reversible, visible, and boundary-safe.
R14 any blocked node blocks executable_ready.
R15 selected_candidate_id and approved class names must remain locked.
R16 accessibility_claims require evidence.
```

---

## Planned Repository Structure

```text
EV4-Constructability-Engineer-Repo/
├── README.md
├── docs/
│   ├── PROTOCOL.md
│   ├── ROLE_BOUNDARIES.md
│   ├── IMPLEMENTATION_STRATEGY_GATE.md
│   └── FAILURE_PATTERN_LIBRARY.md
├── schemas/
│   ├── constructability_review.schema.json
│   ├── implementation_strategy_map.schema.json
│   └── builder_executable_package.schema.json
├── validator/
│   ├── engine.py
│   ├── rules.py
│   └── exceptions.py
├── fixtures/
│   ├── valid/
│   ├── invalid/
│   └── regression/
│       └── r01_unflagged_connector_geometry_dependency.yaml
├── tests/
│   ├── test_fixtures.py
│   └── test_smart_home_regression.py
├── pyproject.toml
└── .github/
    └── workflows/
        └── validate-fixtures.yml
```

---

## First Patch Plan

### PATCH-001 — Fail-Closed Core

```text
- create schemas
- create validator engine
- create rule definitions
- create ConstructabilityException
- add 5 valid fixtures
- add 5 invalid fixtures
- add Smart Home regression fixture
- add pytest tests
```

Definition of Done:

```text
- r01_unflagged_connector_geometry_dependency fails closed
- no executable_ready if builder_decisions_required > 0
- no executable_ready if blocking_dependencies is not empty
- no Builder package if geometry strategy is missing
- no Builder package if exact UI path lacks evidence
- production_ready: true fails without QA evidence
```

### PATCH-002 — CLI and GitHub Action

```text
- add CLI command
- add GitHub Action
- run tests on pull requests
```

### PATCH-003 — Documentation Hardening

```text
- add protocol docs
- add role boundary docs
- add failure pattern docs
- add schema examples
```

### PATCH-004 — Builder Contract Alignment

```text
- align Builder intake with Builder Executable Package
- preserve structured confirmation_request
- enforce selected_candidate_id and approved_class_names lock
```

---

## Companion Repositories

```text
EV4 Architect Repo
Recommended slug: EV4-Architect-Repo
Current slug: elementor-v4-architect-prompt-pack

EV4 Builder Assistant Repo
https://github.com/rezahh107/EV4-Builder-Assistant-Repo

EV4 Responsive Architect Repo
https://github.com/rezahh107/EV4-Responsive-Architect
```

---

## Current Status

```yaml
project_status:
  role: implementation_strategy_gate
  mvp_design: ready
  implementation_started: false
  fail_closed_default: true
  builder_package_emission: blocked_until_validator_exists
  production_ready: false
```
