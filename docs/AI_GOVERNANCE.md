# AI Governance Adoption

Version: 1.0.0  
Target standard: `AI Authority Deterministic Governance — Source of Truth v1.0.2`

## Authorities

- AI makes bounded technical decisions.
- Repository and tool evidence determine factual truth.
- `STATUS.md` remains the sole mutable repository-status authority.
- `governance/AI_AUTHORITY_PROFILE.yml` defines the active governance and security profile.
- `planning/GOVERNANCE_SCOPE_STATE.yml` defines Scope Projection, Capability Memory, Progress Gate, and review/merge predicates.

## Scope Gate

The governance validator rejects:

- missing long-term capabilities;
- incompatible lifecycle dispositions;
- capability-memory drift;
- unknown IDs;
- silent capability deletion;
- authored technical-approval fields.

It computes `scope-change-disclosure.json` from canonical sets and binds it to the exact PR head SHA.

## Progress Gate

The validator emits `completion-receipt.json` for the exact tested SHA. The receipt remains `implemented_pending_independent_review` until an independent exact-head PR Inspector review exists.

A green CI run does not prove merge, deployment, production readiness, runtime behavior, repository settings enforcement, or downstream acceptance.

## Independent Review and Merge Gate

A merge recommendation requires all of:

- exact-head CI success;
- passed Scope Gate;
- passed Progress Gate;
- a separate-session PR Inspector review on the same exact head and scope revision;
- no blocking findings.

Any head or scope-revision change invalidates the previous review. User Merge is an administrative action, not technical approval.

## Security Profile

The active profile is:

```text
personal_ai_operated_strong_governance_minimum_security
```

Minimum safety controls remain required. Enterprise controls are intentionally out of scope unless an activation trigger is present. Their absence alone does not block a technical GREEN recommendation.

## Validation

```bash
python -m pip install -e '.[dev]'
pytest -q
python scripts/validate-ai-governance.py \
  --head-sha <exact_pr_head> \
  --emit-dir .governance-evidence
```
