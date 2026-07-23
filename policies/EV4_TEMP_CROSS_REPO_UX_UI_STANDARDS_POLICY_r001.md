# EV4 Temporary Cross-Repository UX/UI Standards Policy

**Policy ID:** `EV4-TEMP-CROSS-REPO-UX-UI-STANDARDS-POLICY-r001`  
**Status:** `READY_FOR_TEMPORARY_CROSS_REPOSITORY_USE`  
**Revision:** `r001`  
**Language:** English for rules and identifiers; repositories may explain results to the user in Persian  
**Intended consumers:**  
- `EV4-Architect-Repo`
- `EV4-Constructability-Engineer-Repo`
- `EV4-Builder-Assistant-Repo`
- `EV4-Responsive-Architect`
- `EV4-Project-Gate`

**Artifact role:** Temporary, shared, role-neutral UX/UI guidance and evaluation profile  
**Operating mode:** Silent internal use inside each repository's existing workflow  
**Primary objective:** Make a small set of clear, common, high-value UX/UI rules consistently available to EV4 roles until a Kernel-owned rule pack is implemented.

---

## 0. Temporary authority and sunset boundary

This file is a temporary supplemental policy.

It does not replace, supersede, activate, weaken, or reinterpret:

- repository-level `AGENTS.md` or nested instructions;
- active overrides;
- canonical contracts and schemas;
- validators and fixtures;
- locked Architect identity or `selected_candidate_id`;
- accepted Project Gate transitions;
- CE constructability authority;
- Builder execution boundaries;
- Responsive runtime evidence;
- explicit current task-scoped user decisions;
- future EV4 Decision Kernel authority.

Use this precedence order:

```text
explicit current user decision
→ repository instructions and active overrides
→ canonical contracts, schemas, validators, and locked artifacts
→ this temporary shared policy
→ platform guidance, professional heuristics, and examples
```

When a future Kernel UX/UI Rule Pack is released and explicitly adopted:

```text
future pinned Kernel Rule Pack
→ supersedes this temporary policy
→ requires an explicit migration record
→ this file becomes historical_non_authoritative
```

No repository may silently fork the meaning of a Rule ID defined here.

---

## 1. Why this file exists

The current EV4 role policies already contain strong design, constructability, implementation, responsive, accessibility, performance, and evidence guidance.

However, a small group of recurring UX/UI rules should be:

- named consistently;
- available to every relevant role;
- evaluated only when applicable;
- separated from implementation mechanism;
- associated with evidence ownership;
- prevented from becoming unsupported conformance claims;
- easy to replace with a future Kernel-owned rule pack.

This file provides that temporary shared layer.

It is deliberately smaller than the full EV4 Domain corpus.

---

## 2. Required use behavior

### 2.1 Silent application

Apply applicable rules internally.

Do not normally expose:

- Rule routing;
- internal checklists;
- rule-strength classifications;
- hidden evaluation notes;
- source register details;
- long standards explanations.

User-facing responses may remain concise and practical unless the user requests an audit or reasoning report.

### 2.2 Applicability before enforcement

Do not apply every rule to every design.

For each potentially relevant Rule ID, determine:

```text
applicable
not_applicable
downstream_validation_required
unresolved
```

`not_applicable` requires a bounded reason when the rule would otherwise appear relevant.

### 2.3 Do not convert heuristics into false hard gates

A professional heuristic or preferred default is not automatically a blocking normative requirement.

Rule strength values:

```yaml
HARD_GATE:
  meaning: A selected normative, safety, semantic, or authority boundary.
  default_failure_effect: block, repair, or explicit downstream obligation.

REQUIRED_DEFAULT:
  meaning: EV4 requires this behavior unless a higher-authority constraint justifies an exception.
  default_failure_effect: repair or explicit exception.

PREFERRED_DEFAULT:
  meaning: Use by default when suitable; alternatives are allowed with a clear basis.
  default_failure_effect: no automatic block.

HEURISTIC:
  meaning: Broad professional evaluation guidance.
  default_failure_effect: no automatic block; contributes to candidate comparison and risk.

DOWNSTREAM_TEST_OBLIGATION:
  meaning: The current role can define the requirement but cannot prove the rendered outcome.
  default_failure_effect: transfer an explicit test obligation to the correct role.
```

### 2.4 No unsupported conformance claim

This policy adopts selected accessibility constraints and professional rules.

It does **not** independently establish:

```text
WCAG 2.2 Level A conformance
WCAG 2.2 Level AA conformance
WCAG 2.2 Level AAA conformance
ISO 9241-110 conformance
platform-wide accessibility conformance
production usability
```

A full WCAG conformance claim requires the applicable full-page and level requirements, not only selected criteria or architecture intent.

---

## 3. Common evaluation states

Use these internal result states:

```yaml
satisfied:
  meaning: The current role supplied the evidence it owns.

exception:
  meaning: A higher-authority requirement or bounded project condition justifies deviation.
  requires:
    - reason
    - affected_rule_id
    - risk
    - next_validation_owner_when_applicable

unresolved:
  meaning: A material fact or decision remains unknown.
  requires:
    - missing_fact
    - repair_or_evidence_owner

not_applicable:
  meaning: The rule does not apply to this bounded design decision.
  requires:
    - concise_reason_when_nonobvious

downstream_validation_required:
  meaning: Design or implementation intent exists, but runtime proof belongs downstream.
  requires:
    - next_owner
    - test_obligation
```

---

## 4. Role consumption matrix

### 4.1 Architect

Architect must:

- identify applicable rules during decomposition, candidate generation, scoring, recommendation, approved-tree preparation, and final audit;
- express design intent and constraints;
- define required states and user-recovery paths at architecture level;
- preserve semantic, reading-order, focus-order, responsive, accessibility, and content-variability obligations;
- record evidence gaps and downstream validation obligations;
- avoid claiming runtime or full conformance.

Architect must not:

- invent exact implementation controls or values without sufficient basis;
- treat a heuristic as a normative standard;
- prove target-project availability;
- claim runtime accessibility or usability.

### 4.2 Constructability Engineer

CE must:

- verify that the approved design can express every applicable hard gate and required default;
- resolve exact implementation strategy without redesigning;
- verify target-project capability when it can change the strategy;
- turn runtime-only outcomes into explicit Builder or Responsive test obligations;
- leave zero hidden strategy decisions to Builder.

CE must not:

- weaken a Rule ID because implementation is inconvenient;
- silently replace a blocked requirement with a workaround;
- claim runtime proof from editor or saved-state evidence.

### 4.3 Builder

Builder must:

- implement the accepted strategy and applicable Rule obligations;
- use established tokens and reusable mechanisms where supplied;
- preserve required states, semantics, focus behavior, responsive intent, and recovery behavior;
- report an implementation blocker rather than inventing architecture.

Builder must not:

- select a competing architecture;
- reinterpret `HARD_GATE` or locked intent;
- claim successful runtime behavior without observation;
- treat a spacing preference as more authoritative than content, typography, or accessibility.

### 4.4 Responsive Architect

Responsive must:

- validate actual rendered behavior across required viewport, content, direction, input, and state conditions;
- verify source order, focus order, reflow, visibility, obstruction, motion alternatives, target usability, and state behavior;
- separate observed evidence from inferred behavior.

### 4.5 Project Gate

Project Gate may verify:

- policy identity and revision;
- referenced Rule IDs;
- allowed statuses;
- required evidence fields;
- exception rationale presence;
- unresolved owner assignment;
- downstream test obligation presence;
- prohibited conformance claims;
- role and authority boundaries.

Project Gate must not:

- decide the best visual design;
- score usability from appearance alone;
- replace Architect, CE, Builder, or Responsive judgments;
- claim that policy-shape validity proves product quality.

---

## 5. Core temporary Rule Set

# A. Purpose, hierarchy, and comprehension

## `EV4-UX-PURPOSE-001` — Purpose before mechanism

```yaml
strength: REQUIRED_DEFAULT
applies_when:
  - a consequential UI structure, element, interaction, or visual mechanism is selected
requirement:
  - identify the user goal and expected outcome before selecting the mechanism
  - preserve the goal independently of the reference screenshot or implementation tool
disallowed_shortcut:
  - selecting a mechanism only because it visually resembles the reference
architect_evidence:
  - goal_or_outcome
  - selected_mechanism_rationale
```

## `EV4-UX-HIERARCHY-001` — Clear information and action hierarchy

```yaml
strength: HEURISTIC
applies_when:
  - a page, section, dialog, form, card, or multi-action region is designed
requirement:
  - identify the primary content or task
  - identify the primary action when one exists
  - group related information and separate unrelated groups
evaluation_questions:
  - can the user understand where to start
  - is the primary action distinguishable without making every element prominent
  - does spacing communicate grouping
```

## `EV4-UX-RECOGNITION-001` — Recognition over recall

```yaml
strength: HEURISTIC
applies_when:
  - the user must choose, remember, compare, resume, or enter information
requirement:
  - expose necessary options, labels, context, history, defaults, or examples when practical
  - do not rely on placeholder-only labeling for required field identity
  - avoid requiring the user to remember information available to the system
```

# B. Feedback, control, error, and state

## `EV4-UX-STATUS-001` — Visible system status

```yaml
strength: REQUIRED_DEFAULT
applies_when:
  - an action has delay, asynchronous processing, multi-step progress, saving, upload, generation, or state change
requirement:
  - define pending or in-progress feedback
  - define success or completion feedback
  - define failure feedback
  - prevent ambiguous repeated activation when consequential
downstream_test:
  - verify actual state transition and announcement behavior
```

## `EV4-UX-CONTROL-001` — User control and safe exit

```yaml
strength: REQUIRED_DEFAULT
applies_when:
  - the user can enter a flow, alter data, trigger a consequential action, or make a reversible change
requirement:
  - provide an appropriate exit, cancel, back, edit, undo, or recovery path
  - use confirmation when consequences are high and reversal is unavailable or costly
  - do not trap the user in a flow without a justified safety reason
```

## `EV4-UX-ERROR-001` — Prevent and recover from errors

```yaml
strength: REQUIRED_DEFAULT
applies_when:
  - invalid input, destructive action, unavailable state, failed request, or business-rule conflict is possible
requirement:
  - prevent predictable errors where practical
  - identify the affected field or action
  - explain the correction or recovery path
  - preserve valid user input when retrying unless safety requires clearing it
  - do not use color as the only error signal
```

## `EV4-UX-STATES-001` — Complete relevant state inventory

```yaml
strength: REQUIRED_DEFAULT
applies_when:
  - an interactive component, data region, media region, form, or asynchronous feature exists
required_state_candidates:
  - default
  - hover_when_pointer_relevant
  - focus
  - active_or_pressed
  - selected_or_expanded
  - disabled_when_valid
  - loading_or_pending
  - empty
  - error
  - success
rule:
  - include every materially applicable state
  - do not require meaningless states
  - define state differences through more than color when necessary
```

## `EV4-UX-CONSISTENCY-001` — Consistency and user expectations

```yaml
strength: HEURISTIC
applies_when:
  - a pattern, term, icon, color role, control, or interaction is repeated
requirement:
  - preserve the same meaning and behavior for the same pattern
  - follow established platform and product conventions unless a documented reason justifies deviation
  - avoid using the same visual treatment for conflicting meanings
```

# C. Semantics and accessibility constraints

## `EV4-A11Y-SEMANTICS-001` — Semantic structure and source order

```yaml
strength: HARD_GATE
applies_when:
  - meaningful text, headings, lists, regions, media, navigation, actions, forms, or reordered layouts exist
requirement:
  - select semantic roles by meaning, not appearance
  - preserve meaningful document hierarchy
  - preserve logical source and reading order
  - distinguish navigation from action
  - keep meaningful text as text when practical
proof_boundary:
  architect: defines semantic and source-order intent
  ce: proves implementation strategy
  builder: implements accepted semantics
  responsive: validates rendered order and behavior
```

## `EV4-A11Y-KEYBOARD-FOCUS-001` — Keyboard and focus operability

```yaml
strength: HARD_GATE
applies_when:
  - an interactive control, modal, disclosure, menu, form, custom interaction, sticky region, or overlay exists
requirement:
  - every required action must be keyboard operable
  - focus order must remain logical
  - focus must be visible
  - focus must not become materially obscured by authored content
  - opening and closing composite interactions must preserve a defined focus route
proof_boundary:
  architect: intent and order constraints
  ce: feasible pattern and control proof
  builder: implementation
  responsive: runtime keyboard and focus validation
```

## `EV4-A11Y-CONTRAST-001` — Contrast as a measurable constraint

```yaml
strength: HARD_GATE
applies_when:
  - text, essential icons, focus indication, boundaries, or state differentiation depend on foreground/background contrast
requirement:
  - treat applicable WCAG contrast thresholds as measurable constraints
  - evaluate actual color combinations, states, gradients, overlays, and backgrounds
  - do not infer runtime contrast from token names or screenshots alone
claim_limit:
  - passing selected contrast checks does not establish full WCAG conformance
```

## `EV4-A11Y-TARGET-001` — Usable target area and spacing

```yaml
strength: HARD_GATE
applies_when:
  - pointer or touch interaction is used
requirement:
  - meet the adopted minimum target-size requirement or a valid exception
  - use a larger practical target where frequency, mobility, environment, or error cost warrants it
  - ensure the active hit area matches the intended visible control
  - avoid dense adjacent targets that create accidental activation risk
proof_boundary:
  architect: target and density constraint
  ce: control and spacing strategy
  builder: hit-area implementation
  responsive: runtime measurement
```

## `EV4-A11Y-REFLOW-001` — Text resize, content reflow, and localization resilience

```yaml
strength: HARD_GATE
applies_when:
  - meaningful text or localized content appears
requirement:
  - avoid fixed heights that clip variable meaningful text
  - preserve access to content under required text enlargement and narrow reflow conditions
  - account for content extremes and language expansion
  - preserve RTL and LTR meaning and order where applicable
  - do not hide meaningful content solely to make a viewport fit
```

## `EV4-A11Y-MOTION-001` — Motion restraint and alternative

```yaml
strength: REQUIRED_DEFAULT
applies_when:
  - animation, autoplay, parallax, transition, moving background, or motion-triggered interaction exists
requirement:
  - use motion only when it supports understanding or feedback
  - provide reduced or removed nonessential motion when required
  - avoid motion that blocks task completion or creates avoidable disorientation
  - preserve equivalent information and control when motion is reduced
```

# D. Visual system and layout defaults

## `EV4-UI-SPACING-001` — Tokenized 4/8 spacing rhythm

```yaml
strength: PREFERRED_DEFAULT
applies_when:
  - margin, padding, gap, control size, section rhythm, or component spacing is selected
default_scale:
  fine_step: 4
  primary_step: 8
example_values:
  - 4
  - 8
  - 12
  - 16
  - 24
  - 32
  - 48
  - 64
requirement:
  - use a small named spacing scale instead of arbitrary unrelated values
  - prefer parent-owned gap for repeated sibling spacing
  - prefer boundary-owned padding for internal inset
  - allow optical, typographic, intrinsic, or evidence-based exceptions
not_a_rule:
  - font sizes, intrinsic media dimensions, responsive widths, and all geometry do not need to be multiples of 8
failure_effect:
  - no automatic block
```

## `EV4-UI-TOKENS-001` — Named reusable design values

```yaml
strength: REQUIRED_DEFAULT
applies_when:
  - a color, spacing, typography, radius, duration, elevation, or other value is intentionally reused or centrally governed
requirement:
  - use a named reusable token or accepted EV4 Variable mechanism
  - distinguish semantic tokens from raw values
  - preserve a bounded local value when reuse is not intended
  - do not create a global token merely because two values happen to match once
compatibility_note:
  - a future token artifact may align with the Design Tokens Community Group format
  - this policy does not require a specific tool implementation
```

## `EV4-UI-SIZING-001` — Content-resilient sizing before arbitrary fixed values

```yaml
strength: REQUIRED_DEFAULT
applies_when:
  - width, height, minimum, maximum, aspect ratio, truncation, or overflow is selected
requirement:
  - identify fixed, intrinsic, fill, parent-relative, viewport-relative, or bounded-fluid intent first
  - prefer content-resilient behavior for variable meaningful content
  - use min/max bounds when continuous adaptation requires protection
  - do not copy an exact fixed size from one screenshot without a justified invariance requirement
```

## `EV4-UI-RESPONSIVE-001` — Responsive preservation of meaning

```yaml
strength: REQUIRED_DEFAULT
applies_when:
  - layout or interaction changes across viewport, direction, input mode, or content state
requirement:
  - preserve content priority and semantic order
  - define reflow before hiding
  - preserve access to essential actions
  - distinguish preview evidence from runtime evidence
  - validate actual viewport behavior rather than assuming device labels prove it
```

# E. Performance and evidence integrity

## `EV4-UX-PERFORMANCE-001` — Avoid inherently wasteful UI architecture

```yaml
strength: REQUIRED_DEFAULT
applies_when:
  - nesting, repeated content, media, loading, animation, or custom mechanisms can affect editor or runtime cost
requirement:
  - avoid wrappers without a distinct responsibility
  - preserve stable media geometry where practical
  - avoid architecture that inherently causes avoidable layout shift
  - keep repeated-content strategy proportionate
  - treat measured performance outcomes as downstream evidence
```

## `EV4-UX-EVIDENCE-001` — Claim only what the evidence proves

```yaml
strength: HARD_GATE
applies_when:
  - any rule satisfaction, project capability, saved state, runtime behavior, accessibility result, usability result, or readiness is reported
requirement:
  - public documentation proves only documented public behavior within its scope
  - target-project capability requires target-project evidence
  - saved configuration proves only saved configuration
  - runtime behavior requires runtime observation
  - a schema-valid evaluation record does not prove semantic or runtime correctness
  - selected-rule success does not establish complete standards conformance
```

---

## 6. Minimum Architect evaluation record

When the current Architect contract permits extension fields, use an equivalent structure:

```yaml
ux_ui_policy_evaluation:
  policy_id: EV4-TEMP-CROSS-REPO-UX-UI-STANDARDS-POLICY-r001
  policy_revision: r001

  applicable_rules:
    - rule_id: EV4-UX-STATUS-001
      status: satisfied
      evidence_refs:
        - candidate-C02.state_model
      rationale: Loading, success, and recoverable error states are defined.

    - rule_id: EV4-A11Y-KEYBOARD-FOCUS-001
      status: downstream_validation_required
      next_owner: EV4-Responsive-Architect
      test_obligation: Validate keyboard order, visible focus, and focus obstruction.

    - rule_id: EV4-UI-SPACING-001
      status: exception
      rationale: A 6px optical correction is required between the icon and Persian label.
      risk: low
```

Do not add this structure when it would violate the current canonical output schema.

When the schema does not allow it:

- preserve the evaluation internally;
- map material constraints into existing accepted fields;
- record only schema-supported evidence gaps and downstream obligations;
- do not invent a wrapper artifact solely to claim compliance.

---

## 7. Lightweight validation profile

A temporary validator may check only deterministic properties:

```text
□ policy_id and revision are recognized
□ every referenced Rule ID exists
□ every rule status is allowed
□ every exception has a reason
□ every unresolved item has an owner
□ every downstream validation item has a test obligation
□ HARD_GATE is not silently downgraded
□ HEURISTIC and PREFERRED_DEFAULT are not treated as automatic blockers
□ Project Gate does not make design selections
□ architecture evidence is not promoted to runtime evidence
□ selected checks are not reported as full WCAG or ISO conformance
```

A lightweight validator must not claim:

```text
design quality proven
usability proven
accessibility conformance proven
runtime behavior proven
production readiness proven
```

---

## 8. Adoption instructions for repositories

### 8.1 Recommended repository placement

Use the same exact bytes and filename in each temporary consumer repository:

```text
policies/EV4_TEMP_CROSS_REPO_UX_UI_STANDARDS_POLICY_r001.md
```

Do not edit the copies independently.

If a local repository needs a role-specific note, add a small adapter that references the exact Policy ID and digest. Do not duplicate or rewrite Rule meanings.

### 8.2 Minimal startup instruction

Repositories may add this concise instruction to their normal startup guidance:

```text
Use `policies/EV4_TEMP_CROSS_REPO_UX_UI_STANDARDS_POLICY_r001.md`
as a temporary supplemental shared UX/UI rule profile.

Apply only materially applicable rules.
Preserve repository authority, role boundaries, locked artifacts, schemas,
validators, and explicit current user decisions.

Do not treat heuristics or preferred defaults as hard gates.
Do not claim runtime behavior or complete standards conformance without the
required evidence.
```

### 8.3 Digest pinning

For cross-repository consistency, each consumer should record:

```yaml
policy_id: EV4-TEMP-CROSS-REPO-UX-UI-STANDARDS-POLICY-r001
revision: r001
sha256: <exact_file_sha256>
```

A mismatch should produce:

```text
TEMP_UX_UI_POLICY_IDENTITY_MISMATCH
```

It should not automatically prove product failure, but the evaluation must not be treated as consistently pinned until the mismatch is resolved.

---

## 9. Source and interpretation register

This section records source families and claim boundaries. It is not a substitute for the source documents.

### `SRC-UX-001` — WCAG 2.2

- Publisher: W3C Web Accessibility Initiative
- Type: W3C Recommendation / web standard
- Reference: `https://www.w3.org/TR/WCAG22/`
- Used for:
  - selected testable accessibility constraints;
  - conformance-claim boundaries;
  - focus, target, reflow, contrast, keyboard, and related requirements.
- Cannot prove:
  - target-project conformance;
  - complete Level A, AA, or AAA conformance from selected rules.

### `SRC-UX-002` — ACT Rules Format 1.1

- Publisher: W3C
- Type: W3C Recommendation, published 2026-02-05
- Reference: `https://www.w3.org/TR/act-rules-format/`
- Used for:
  - inspiration for explicit applicability, expectations, outcomes, and rule transparency.
- Boundary:
  - this EV4 policy is not an ACT-conformant rule suite;
  - ACT test rules are informative relative to WCAG conformance.

### `SRC-UX-003` — ISO 9241-110:2020 public metadata

- Publisher: ISO
- Type: International Standard
- Reference: `https://www.iso.org/standard/75258.html`
- Used for:
  - confirming that general interaction principles can support design and evaluation across interactive systems.
- Copyright boundary:
  - this file does not reproduce ISO normative text;
  - internal EV4 wording is independently written;
  - no ISO conformance is claimed.

### `SRC-UX-004` — Nielsen usability heuristics

- Publisher: Nielsen Norman Group
- Reference: `https://www.nngroup.com/articles/ten-usability-heuristics/`
- Used for:
  - broad professional heuristic families such as visible status, consistency, user control, error prevention, recognition, and recovery.
- Boundary:
  - heuristics are broad rules of thumb, not specific normative requirements.

### `SRC-UX-005` — Design Tokens Format Module 2025.10

- Publisher: Design Tokens Community Group
- Reference: `https://www.w3.org/community/reports/design-tokens/CG-FINAL-format-20251028/`
- Used for:
  - future-compatible vocabulary for named and exchangeable design values.
- Boundary:
  - it is a stable Community Group Final Report;
  - it is not a W3C Standard and is not on the W3C Standards Track.

### `SRC-UX-006` — Platform design guidance

- Examples:
  - Material Design
  - Apple Human Interface Guidelines
- Used for:
  - platform conventions, component behavior, spacing examples, and implementation guidance.
- Boundary:
  - platform guidance is not a universal standard;
  - project and platform context determine applicability.

---

## 10. Known limitations

This temporary policy:

- is not a complete UX body of knowledge;
- is not a complete accessibility test suite;
- does not replace user research or usability testing;
- does not prove target-project capability;
- does not define every component pattern;
- does not define final design tokens;
- does not automatically modify repository schemas;
- does not create Kernel authority;
- does not authorize Project Gate to design;
- does not allow Builder to invent architecture;
- does not convert Domain research JSONs into direct operational authorities;
- requires explicit future migration into a Kernel-owned Rule Pack.

---

## 11. Final policy state

```text
EV4_TEMP_CROSS_REPO_UX_UI_STANDARDS_POLICY_READY
```
