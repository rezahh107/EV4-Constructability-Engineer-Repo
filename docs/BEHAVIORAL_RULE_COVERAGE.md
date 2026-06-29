# Behavioral Rule Coverage

Version: 0.1.0  
Status: active  
Scope: high-risk LLM behavioral gates in the Constructability Engineer repo

---

## Purpose

This document tracks whether high-risk behavioral rules are only written as prose or are backed by executable enforcement carriers.

In an LLM-executed repository, prompts, protocols, schemas, validators, fixtures, and CI workflows act as behavioral source code. Prose is useful for human and model understanding, but prose alone is not an enforcement mechanism.

The goal is not to turn every instruction into machinery. The goal is to ensure that Critical and High behavioral gates cannot be silently ignored by a downstream LLM agent.

---

## Core Failure Pattern

### Enforcement-Free Behavioral Gate

An Enforcement-Free Behavioral Gate is a rule that is intended to constrain LLM behavior, but exists only as markdown prose, examples, role guidance, or prompt instructions.

Short name:

```text
EFBG
```

Risk:

```text
The model may understand the rule conceptually but skip it operationally.
```

A rule is not considered enforced merely because the model was told to follow it.

---

## Semantic Illusion

Field presence is not semantic enforcement.

A shallow field such as:

```json
{
  "reference_paradigm_lock": true
}
```

may satisfy a weak contract while failing to preserve the intended behavior. Critical rules require minimum semantic children: structured fields that force the output to represent the actual concept rather than merely appear compliant.

Example minimum semantic children for a visual reference paradigm lock:

```text
source_reference_id
paradigm_locked
layout_paradigm
primary_anchor
distribution_model
repeated_unit_form
connector_model
spatial_symmetry
completion_signature
paradigm_to_structure_map
first_batch_requirements
```

---

## Risk Levels

| risk | definition | enforcement expectation |
|---|---|---|
| `Critical` | Ignoring the rule can cause architecture drift, visual paradigm drift, class-name drift, unsafe Builder decisions, invalid package emission, false readiness, or expensive rework. | Must not remain `prose_only` or shallow `schema_backed`. Requires validator, invalid fixture, and CI enforcement. |
| `High` | Ignoring the rule can cause significant ambiguity, layout drift, wrong implementation strategy, or unsupported assumptions. | Should reach at least `validator_backed`; preferably `fixture_tested`. |
| `Medium` | Ignoring the rule can reduce quality or clarity but does not directly break architecture, package safety, or downstream execution. | Schema or prose may be acceptable. |
| `Low` | Tone, style, formatting, or low-risk guidance. | Prose is usually sufficient. |

This file should normally track only `Critical` and `High` rules.

---

## Enforcement Status Levels

| status | meaning |
|---|---|
| `prose_only` | The rule exists only in markdown, prompt text, examples, or role guidance. |
| `schema_backed` | The rule has a schema field or typed structure, but no validator logic or failing fixture proves behavior. |
| `validator_backed` | A validator checks the rule, but fixture coverage may be incomplete. |
| `fixture_tested` | The rule has valid or invalid fixtures proving validator behavior. |
| `ci_enforced` | CI runs the relevant validator or tests automatically. |
| `downstream_contract_enforced` | The downstream consumer rejects missing or invalid carriers. |

Recommended thresholds:

```text
Critical -> fixture_tested minimum; ci_enforced preferred; downstream_contract_enforced final target
High     -> validator_backed minimum; fixture_tested preferred
Medium   -> schema_backed or prose may be acceptable
Low      -> prose is usually acceptable
```

---

## Coverage Matrix

| rule_id | concept | risk | prose_source | schema_carrier | validator_rule | valid_fixture | invalid_fixture | CI_step | downstream_contract | status |
|---|---|---:|---|---|---|---|---|---|---|---|
| `R-CE-PAR-01` | Visual references must be lowered into a locked paradigm contract before Builder-ready output. | Critical | `protocols/REFERENCE_PARADIGM_LOCK.md` | `reference_paradigm_lock`, `paradigm_to_structure_map` | `validator.reference_paradigm_lock`, `R29, R31, R32` | `tests/valid/center_anchored_symmetric_pill_cards.json` | `tests/invalid/missing_structure_map.json` | `pytest -q`, `npm run test:reference-paradigm-lock` | Builder intake pending | `ci_enforced` |
| `R-CE-PAR-02` | Unknown visual paradigm must block Builder-ready visual-parity output. | Critical | `protocols/REFERENCE_PARADIGM_LOCK.md` | `layout_paradigm` | `R30_REFERENCE_PARADIGM_UNKNOWN_BLOCKS_BUILDER_READY` | `tests/valid/center_anchored_symmetric_pill_cards.json` | `tests/invalid/unknown_layout_paradigm_marked_builder_ready.json` | `pytest -q`, `npm run test:reference-paradigm-lock` | Builder intake pending | `ci_enforced` |
| `R-CE-GEO-01` | Geometry-dependent actions require a proof object, not only a boolean flag. | Critical | `README.md`, `docs/FAILURE_PATTERN_LIBRARY.md` | `geometry_required`, `geometry_proven`, `geometry_proof` | `R03`, `R24` | existing valid geometry fixture | geometry proof missing fixture/test | `pytest -q` | Builder must not infer geometry | `fixture_tested` |
| `R-CE-OVR-01` | Overlay and decorative layers require explicit containment, positioning, and z-index strategy. | Critical | `README.md`, `docs/FAILURE_PATTERN_LIBRARY.md` | `overlay_strategy_required`, `overlay_strategy_proven`, `overlay_strategy` | `R05`, `R25` | existing valid overlay fixture | overlay strategy missing fixture/test | `pytest -q` | Builder must not choose overlay containment | `fixture_tested` |
| `R-CE-ISM-01` | Implementation strategy map must leave zero Builder decisions. | Critical | `docs/IMPLEMENTATION_STRATEGY_GATE.md` | `implementation_strategy_map.strategies[*].builder_decisions_required` | `R33` | `fixtures/valid/v03_six_independent_connectors_ready.yaml` | `fixtures/invalid/i10_strategy_map_requires_builder_decision.yaml` | `pytest -q` | Builder must not choose strategy | `ci_enforced` |
| `R-CE-BEP-01` | Non-executable review must not emit Builder package. | Critical | `docs/VALIDATION_MODEL.md` | `constructability_status`, `builder_executable_package` | `R17-R21` | validation mode fixtures | blocked review with package fixture | `pytest -q` | Builder receives package only from executable review | `ci_enforced` |
| `R-CE-LOCK-01` | Selected candidate must remain locked. | Critical | `docs/ROLE_BOUNDARIES.md` | `architect_contract.selected_candidate_id` | `R22`, `R23` | architect contract valid test | selected candidate mismatch test | `pytest -q` | Builder must not change selected candidate | `ci_enforced` |
| `R-CE-LOCK-02` | Approved class names must not be added or removed by Builder package. | Critical | `docs/ROLE_BOUNDARIES.md` | `architect_contract.approved_class_names` | `R22`, `R23` | architect contract valid test | class addition/removal test | `pytest -q` | Builder class entry constrained | `ci_enforced` |
| `R-CE-DYN-01` | Dynamic Loop approval requires an explicit binding map. | High | `docs/FAILURE_PATTERN_LIBRARY.md` | `dynamic_loop_approved`, `dynamic_loop_binding_map` | `R08`, `R26` | existing proof-object test path | dynamic loop map missing test | `pytest -q` | Builder must not infer Dynamic Loop | `fixture_tested` |
| `R-CE-UI-01` | Exact Elementor UI control paths require evidence object. | High | `docs/FAILURE_PATTERN_LIBRARY.md` | `ui_control_evidence_present`, `ui_control_evidence` | `R10`, `R27` | existing proof-object test path | UI evidence missing test | `pytest -q` | Builder must not invent UI paths | `fixture_tested` |
| `R-CE-QA-01` | `production_ready: true` requires full QA evidence and QA matrix. | Critical | `docs/QUALITY_BAR.md` | `qa_status.full_qa_evidence_present`, `qa_matrix` | `R12`, `R28` | QA valid fixture pending | QA matrix missing test | `pytest -q` | Downstream must keep `production_ready` false | `fixture_tested` |
| `R-CE-BATCH-01` | First Builder batch must not hide unresolved decisions in action parameters. | High | `docs/ROLE_BOUNDARIES.md`, Builder Package Gate | `first_safe_builder_batch.actions[*].parameters` | `R34` | existing valid package fixtures | `fixtures/invalid/i11_batch_parameters_hide_decision.yaml` | `pytest -q` | Builder should execute, not decide | `ci_enforced` |

---

## Interpretation Rules

A Critical rule with status `prose_only` or `schema_backed` is an open enforcement gap.

A High rule with status `prose_only` should be scheduled for schema or validator work.

A rule can be `ci_enforced` and still not fully safe if the downstream consumer accepts invalid or missing data. Final target for cross-agent handoffs is `downstream_contract_enforced`.

---

## Maintenance Rules

This file is intentionally small.

Do not add rules for tone, style, minor formatting, low-risk writing guidance, or non-blocking preferences.

Add a rule only if violation may cause:

```text
architecture drift
visual paradigm drift
class-name drift
unsafe Builder decision
invalid downstream package
false production readiness
irreversible or expensive rework
security or instruction/data boundary failure
```

Every new Critical behavioral rule must answer:

```text
What field carries it?
What validator checks it?
What invalid fixture proves it fails?
What CI step runs it?
What downstream consumer rejects it?
```

If these questions cannot be answered, the rule is not yet enforced.

---

## Audit Patterns

Candidate prose-only gates can be found by searching markdown and prompt files for imperative language.

English patterns:

```text
must
must not
should
should not
never
always
only
shall
required
forbidden
blocked
allowed only
do not
cannot
```

Persian patterns:

```text
باید
نباید
هرگز
همیشه
فقط
مجاز نیست
الزامی است
اجباری است
مسدود
متوقف شود
```

Red flags:

```text
A rule says "must" but no schema field exists.
A rule says "must not" but no invalid fixture exists.
A rule blocks Builder behavior but Builder intake does not reject missing data.
A rule depends on model memory or good faith.
A rule uses vague terms such as preserve, match, respect, or same as reference without minimum semantic children.
A rule requires proof but the proof object has no required shape.
A rule says fail closed but missing data passes validation.
A rule says production ready but QA evidence is not structured.
```

---

## Governance

A prompt/protocol repository for LLM agents should be treated as behavioral source code.

Prose explains intent. Schemas, validators, fixtures, CI, and downstream contracts enforce intent.

For high-risk behavior, the system must move from:

```text
model should remember
```

to:

```text
system fails closed if missing or invalid
```
