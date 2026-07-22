# EV4 Temporary Cross-Repository UX/UI Standards Policy

**Policy ID:** `EV4-TEMP-CROSS-REPO-UX-UI-STANDARDS-POLICY-r002`  
**Status:** `READY_FOR_TEMPORARY_CROSS_REPOSITORY_USE`  
**Revision:** `r002`  
**Language:** English for rules and identifiers; repositories may explain results to the user in Persian  
**Intended consumers:**  
- `EV4-Architect-Repo`
- `EV4-Constructability-Engineer-Repo`
- `EV4-Builder-Assistant-Repo`
- `EV4-Responsive-Architect`
- `EV4-Project-Gate`

**Artifact role:** Temporary, shared, role-neutral UX/UI guidance and evaluation profile  
**Operating mode:** Concise internal rule routing with material findings represented through repository-supported carriers  
**Primary objective:** Make a small set of clear, common, high-value UX/UI rules consistently available to EV4 roles until a Kernel-owned rule pack is implemented.

---

## 0. Temporary authority, precedence, and revision boundary

This file is a temporary supplemental policy.

It does not replace, supersede, activate, weaken, or reinterpret:

- system or platform authority;
- repository-level `AGENTS.md` or nested instructions;
- active overrides;
- canonical contracts and schemas;
- validators and fixtures;
- locked Architect identity or `selected_candidate_id`;
- accepted Project Gate transitions;
- security boundaries and evidence requirements;
- CE constructability authority;
- Builder execution boundaries;
- Responsive runtime evidence;
- required external validation;
- future EV4 Decision Kernel authority.

Use this scope-aware precedence order:

```text
system and platform authority
→ repository instructions and active overrides
→ canonical contracts, schemas, validators, and locked artifacts
→ explicit current user decisions within the user's authorized decision scope
→ this temporary shared policy
→ external platform guidance, professional heuristics, and examples
```

An explicit user choice remains authoritative only inside its legitimate decision surface.

```yaml
authorized_user_decision_scope:
  - business intent
  - product intent
  - brand preference
  - approved content
  - explicit task scope
  - owner-selected trade-offs
  - authorized risk acceptance where repository policy permits it

user_decision_must_not_override:
  - system or platform authority
  - repository instructions
  - active overrides
  - canonical contracts
  - schemas
  - validators
  - locked artifacts
  - security boundaries
  - evidence requirements
  - role ownership
  - required external validation
```

This boundary preserves the owner's legitimate authority over business, brand, content, scope, and permitted trade-offs without converting owner preference into technical proof or authorization outside the owner's decision surface.

### 0.1 Revision and migration record

```yaml
revision_history:
  r001:
    state: historical_once_distributed
    active_for_repository: only_when_that_repository_still_explicitly_pins_r001
  r002:
    state: active_temporary_revision_after_explicit_repository_adoption
    supersedes: r001_for_that_repository_only

r002_changes:
  - scopes user authority so it cannot override repository authority
  - requires material blockers and obligations to remain visible or artifact-backed
  - strengthens exact-byte digest pinning
  - formalizes minimal role adapters
```

`r001` remains immutable historical material. `r002` becomes active only in repositories that explicitly adopt and pin `r002`. Repositories that still pin `r001` are not `r002` consumers. Mixed revisions must be reported and must not be silently accepted as one consistently pinned policy set.

When a future Kernel UX/UI Rule Pack is released and explicitly adopted:

```text
future pinned Kernel Rule Pack
→ supersedes the currently adopted temporary revision
→ requires an explicit migration record
→ the replaced temporary revision becomes historical_non_authoritative
```

No repository may silently fork the meaning or strength of a Rule ID defined here.

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

### 2.1 Silent routing without hidden material failures

Rule routing and detailed internal evaluation remain hidden by default.

```yaml
hidden_by_default:
  - internal rule routing
  - full applicability checklist
  - detailed source register
  - nonmaterial evaluation notes
  - internal comparison of heuristics

must_be_represented_when_material:
  - HARD_GATE failure
  - material exception
  - unresolved requirement
  - downstream validation obligation
  - missing evidence that blocks continuation
  - authority conflict
  - prohibited conformance claim
```

Material findings must be represented through the first repository-supported carrier that applies:

1. the canonical Stage Artifact, when its active Schema permits;
2. existing accepted evidence-gap, blocker, exception, unresolved-item, or downstream-obligation fields;
3. a concise visible status summary when the user must act or understand why continuation is blocked.

Do not invent a wrapper Artifact or unsupported Schema extension merely to expose internal policy evaluation.

If the current Schema cannot represent a material issue:

- use the nearest repository-supported field;
- report the representation limitation accurately;
- route the issue to the correct owner;
- provide a concise visible status when continuation, authorization, or owner action is affected;
- do not claim that the issue was stored invisibly.

User-facing responses should remain concise and practical. Concision must not hide a material continuation condition, authority conflict, or required owner action.

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
  policy_id: EV4-TEMP-CROSS-REPO-UX-UI-STANDARDS-POLICY-r002
  policy_revision: r002

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

When the Schema does not allow the example structure:

- keep nonmaterial routing internal;
- map material constraints into the nearest existing accepted fields;
- represent blockers, exceptions, unresolved items, evidence gaps, and downstream obligations when they affect continuation or owner action;
- report any representation limitation accurately;
- route the issue to the correct owner;
- do not invent a wrapper Artifact, unsupported extension, or hidden-storage claim solely to claim compliance.

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

## 8. Adoption, byte identity, and role adapters

### 8.1 Exact cross-repository identity

Every repository that claims adoption of this revision must use the exact filename and exact bytes:

```yaml
cross_repository_identity:
  exact_filename_match: required
  exact_policy_id_match: required
  exact_revision_match: required
  exact_byte_identity: required
  sha256_pin: required
```

```text
policies/EV4_TEMP_CROSS_REPO_UX_UI_STANDARDS_POLICY_r002.md
```

Do not edit repository copies independently. A local repository may define only its consumption adapter and external pin; it must not rewrite shared Rule meanings or strengths.

### 8.2 External digest pinning

The Policy file must not contain its own computed SHA-256. That would create a self-referential digest problem.

Record the digest in an external repository-supported location, preferring an existing native mechanism such as:

- the repository's existing policy adapter;
- an existing manifest;
- an existing status or pinning file;
- another already-authoritative configuration location.

Each adopting repository must record an equivalent pin:

```yaml
policy_pin:
  policy_id: EV4-TEMP-CROSS-REPO-UX-UI-STANDARDS-POLICY-r002
  revision: r002
  filename: EV4_TEMP_CROSS_REPO_UX_UI_STANDARDS_POLICY_r002.md
  sha256: <computed_sha256_of_exact_r002_bytes>
```

A filename, Policy ID, revision, byte, or SHA-256 mismatch must produce:

```text
TEMP_UX_UI_POLICY_IDENTITY_MISMATCH
```

```yaml
identity_mismatch_effect:
  product_failure_proven: false
  policy_consistency_proven: false
  policy_evaluation_accepted_as_consistently_pinned: false
  required_action: restore_exact_expected_policy_identity
```

Do not claim cross-repository identity for a repository that was not inspected and byte-verified.

### 8.3 Minimal repository-native role adapters

Use a small local adapter only when no equivalent repository-native mechanism already exists. Prefer the repository's existing startup, policy-registration, manifest, or authority file.

The adapter must remain concise and include:

```yaml
adapter_required_fields:
  - policy_id
  - revision
  - filename
  - sha256
  - repository_role
  - local_consumption_scope
  - role_must
  - role_must_not
```

The adapter must not:

- copy the full Policy;
- redefine Rule meanings;
- change Rule strength;
- create local forks of Rule IDs;
- elevate this temporary Policy above repository authority;
- add a parallel pipeline or approval layer;
- claim Kernel adoption.

Role adapters map shared rules into the repository's existing authority boundary. They do not create new authority.

### 8.4 Required role mapping intent

#### Architect

```yaml
repository_role: architect
role_must:
  - identify materially applicable shared rules
  - express architecture intent and constraints
  - transfer runtime-only proof as downstream obligations
  - preserve semantic, source-order, responsive and content-resilience intent
role_must_not:
  - claim constructability
  - claim runtime validation
  - invent exact target-project controls
  - promote heuristics into hard gates
```

#### Constructability Engineer

```yaml
repository_role: constructability_engineer
role_must:
  - prove a feasible strategy for applicable hard gates and required defaults
  - preserve locked architecture
  - verify target-project capability when strategy depends on it
  - transfer runtime-only outcomes as explicit tests
role_must_not:
  - redesign for implementation convenience
  - silently downgrade a hard gate
  - claim runtime proof from editor or saved-state evidence
```

#### Builder

```yaml
repository_role: builder
role_must:
  - implement the accepted strategy
  - preserve applicable semantics, states, focus, responsive and recovery behavior
  - report implementation blockers with evidence
  - use accepted tokens and mechanisms where available
role_must_not:
  - select a competing architecture
  - reinterpret locked intent
  - claim runtime behavior without observation
  - let aesthetic preference override accessibility or content requirements
```

#### Responsive Architect

```yaml
repository_role: responsive_architect
role_must:
  - validate actual rendered behavior
  - test viewport, content, direction, input and state conditions
  - distinguish observation from inference
  - verify source order, focus order, reflow, obstruction and target usability
role_must_not:
  - treat device labels as proof of behavior
  - claim unobserved viewport results
  - replace upstream semantic intent
```

#### Project Gate

```yaml
repository_role: project_gate
role_must:
  - verify policy identity and revision
  - validate referenced Rule IDs and allowed states
  - require reasons, owners and test obligations where applicable
  - reject unsupported conformance and evidence-boundary claims
role_must_not:
  - select visual design
  - replace Architect, CE, Builder or Responsive judgment
  - treat Schema validity as proof of product quality
  - promote architecture evidence into runtime evidence
```

### 8.5 Adoption and mixed-revision behavior

A repository becomes an `r002` consumer only after its active repository-native adapter or pin references the exact `r002` identity and SHA-256.

```yaml
adoption_states:
  pins_r001: historical_or_r001_consumer
  pins_r002_with_verified_bytes: active_r002_consumer
  missing_or_mismatched_pin: identity_mismatch
  mixed_revision_claim: report_and_reject_as_consistently_pinned
```

Do not delete `r001` merely to activate `r002`. Preserve historical revisions unless repository instructions explicitly require removal.

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
EV4_TEMP_CROSS_REPO_UX_UI_STANDARDS_POLICY_R002_READY
```
