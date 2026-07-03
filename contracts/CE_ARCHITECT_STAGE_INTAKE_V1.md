# CE Architect Stage Intake v1

Status: canonical_new_architect_facing_intake  
Contract identity: `ev4-ce-architect-stage-intake@1.0.0`  
Owner: `rezahh107/EV4-Constructability-Engineer-Repo`  
Accepted source: `ev4-architect-stage-payload@1.0.0`

## Purpose

This contract defines the CE-owned intake package produced from validated Architect-owned evidence.

It is the canonical Architect-facing CE intake for new Project Gate work.

The intake is not a constructability review, implementation strategy, Builder executable package, Builder runtime intake, Responsive completion package, or production release claim.

```text
Architect Stage Payload v1
→ CE Architect Stage Intake v1
→ CE processing
→ constructability review / implementation strategy / Builder authorization only after CE work
```

## Legacy compatibility

The previous intake surface remains available only for compatibility:

```text
contracts/ARCHITECT_TO_CE_INPUT_MAPPING_V1.md
schemas/architect_ce_input_package.v1.schema.json
```

Those legacy files target `ev4-architect-output-contract@1.0.0` and `/builder-feed-export`. They must not be used as the preferred target for new Architect Stage Payload v1 transitions.

## Intake boundary

The intake may contain only:

- validated Architect-owned evidence;
- deterministic representation conversions;
- deterministic structural projections;
- source identity;
- provenance;
- evidence references;
- unresolved evidence;
- negative downstream-readiness assertions;
- CE processing prerequisites.

The intake must not contain positive CE-owned conclusions.

Forbidden at intake:

```text
constructability_proven
ce_approved
implementation_strategy_selected
elementor_feasibility_proven
proof_state_resolved
ce_review_complete
builder_ready
builder_executable
builder_action_authorized
builder_runtime_intake_authorized
production_ready
responsive_complete
```

Also forbidden at intake:

```text
ce_review_units[].action_proposed
constructability findings
implementation actions
Elementor control paths
proof-state conclusions
identity consistency verdicts
pre-ingestion verdicts
Builder executable package
```

CE may produce those only after intake.

## Stable rule IDs

| rule_id | meaning |
|---|---|
| `CE-I01` | source must be `ev4-architect-stage-payload@1.0.0` |
| `CE-I02` | selected candidate identity must be preserved |
| `CE-I03` | architecture and structure identity must remain traceable |
| `CE-I04` | unresolved evidence must be preserved |
| `CE-I05` | Architect evidence states must not be upgraded |
| `CE-I06` | CE-owned conclusions are forbidden at intake |
| `CE-I07` | Builder readiness and execution claims are forbidden |
| `CE-I08` | provenance and evidence references must be preserved |
| `CE-I09` | unsupported source fields must not be silently mapped |
| `CE-I10` | deterministic mapping order must be defined |
| `CE-I11` | insufficient evidence must remain distinct from invalid input |
| `CE-I12` | legacy Architect contracts are compatibility-only |

Do not reuse a rule ID for a different meaning.

## Insufficient evidence

`intake_status: insufficient_evidence` is schema-valid only when `missing_evidence[]` states the missing evidence, affected CE conclusion, required source, current evidence owner, and whether CE processing can partially continue.

Insufficient evidence is not a failed repair opportunity and must not be converted into approval.

## Real fixture policy

```yaml
real_cross_repository_validation: not_available
```

Synthetic fixtures prove contract behavior only. They are not real Architect exports and do not prove real cross-repository compatibility.

## Validation

```bash
python scripts/validate-ce-architect-stage-intake.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_ce_architect_stage_intake.py
```

The validator enforces top-level type validation, schema validation, then semantic validation only after schema compatibility succeeds.
