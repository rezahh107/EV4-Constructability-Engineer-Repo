# Cross-Repo Role Alignment

Patch: Patch 1 — Cross-Repo Role Alignment  
Repo role: Constructability Engineer / implementation strategy gate  
Shared Contracts status: future-planned only; no canonical schema migration in this patch.

## CE owns

- Constructability review.
- Execution strategy proof.
- Hidden dependency classification.
- Builder package gate.
- `Builder Executable Package` emission only when zero Builder decisions remain.
- `reference_paradigm_lock`.
- `paradigm_to_structure_map`.
- `golden_reference_contract` locking or carrying after evidence review.
- `build_intent_brief` structured execution seed or deterministic rendered brief when a visual-reference build requires it.
- `spatial_lexicon_version_used` pinning for Build Intent output.
- `visual_tolerance_policy` and `visual_parity_build` status.
- Blocked reason when any prerequisite is incomplete.

## CE output modes

```yaml
allowed_output_modes:
  - Constructability Review
  - Builder Executable Package
```

A blocked or evidence-needed review must emit only Constructability Review. It must not include `builder_executable_package`.

## Builder Executable Package gate

A Builder Executable Package may be emitted only when all are true:

```yaml
constructability_status: executable_ready
builder_package_status: executable_ready
builder_decisions_required: 0
blocking_dependencies: []
selected_candidate_locked: true
selected_candidate_id_unchanged: true
approved_class_names_unchanged: true
confirmation_request: present
first_safe_builder_batch: present
```

For visual-reference builds, the executable package must also carry:

```yaml
golden_reference_contract: present
reference_paradigm_lock: present
paradigm_to_structure_map: present
build_intent_brief: present
spatial_lexicon_version_used: present
visual_tolerance_policy: present
visual_parity_build: true
```

Optional/advisory:

```yaml
experience_intent: optional
reference_family: optional unless responsive behavior depends on scoped references
```

## Cross-repo responsibilities

### Architect owns

- `reference_role` at design-intent level.
- `experience_intent` as advisory design intent.
- Desired outcome.
- Design-level source evidence.
- Approved architecture handoff.

### Builder owns

- Runtime intake validation.
- Deterministic Build Intent rendering.
- Action batch execution.
- Checkpoint/evidence loop.
- Visual parity report.
- Completion wording gate.
- No design invention.

### Responsive owns

- Tablet/mobile adaptation review.
- Scoped reference-family extension.
- Responsive evidence gates.
- No raw screenshot authority.

### Future shared owner

A future `EV4-Shared-Contracts` may own schemas, enums, spatial lexicon, build-intent templates, reference-family schema, and compatibility manifest. This patch must not create that repo or move canonical schemas.
