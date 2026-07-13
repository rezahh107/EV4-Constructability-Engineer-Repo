# AI Governance Adoption

Version: 1.1.0  
Target standard: `AI Authority Deterministic Governance — Source of Truth v1.0.2`

## Authorities

- AI makes bounded technical decisions.
- Repository and tool evidence determine factual truth.
- `STATUS.md` remains the sole mutable repository-status authority.
- `governance/AI_AUTHORITY_PROFILE.yml` defines the active versioned governance and security profile.
- `planning/GOVERNANCE_SCOPE_STATE.yml` defines Scope Projection, Capability Memory, Progress Gate, and review/merge predicates.

## Scope Gate

The governance validator rejects missing long-term capabilities, incompatible lifecycle dispositions, capability-memory drift, unknown IDs, silent capability deletion, and authored technical-approval fields.

It computes `scope-change-disclosure.json` from validated canonical sets and binds it to the exact tested PR head SHA.

## Progress Gate

Every required governance artifact must exist, be a regular non-empty repository file, and receive a computed SHA-256 record. Missing or empty carriers fail closed before evidence emission.

`completion-receipt.json` and `governance-gate-evidence.json` distinguish repository/tool evidence from authoritative final GitHub CI status. Evidence generated inside the currently running job is not labelled `CI_CONFIRMED`; final workflow success must be verified from GitHub after the job completes.

## Independent Review Boundary

Free-form review dictionaries, verdict strings, protocol hashes, caller-supplied booleans, and self-declared session-separation fields cannot authorize merge.

The canonical review-bundle adapter requires these exact artifacts:

```text
review-package.json
DECISION_PROJECTION.json
artifact-manifest.json
```

It recomputes canonical and final-file hashes and verifies exact repository, PR, head, scope revision, protocol version, review session, finding count, Inspector repository, and Inspector commit identities. Bundle integrity alone is still insufficient.

A merge recommendation can consume only an opaque capability created through the official `pr_inspector.official_review.VerifiedReviewCompletion` boundary from a live checkout of the declared `rezahh107/PR-Inspector` commit and a live GitHub PR-head recheck. Any missing provenance, stale head, stale scope, missing session ID, or unavailable live verifier fails closed.

## Security Profile

The active profile is:

```text
personal_ai_operated_strong_governance_minimum_security@v1.0.0
```

The exact versioned identities of minimum controls, intentional exclusions, and activation triggers are enforced with uniqueness. Deletion, substitution, and duplicate padding fail validation. No unrelated enterprise control is added.

## Merge Boundary

Normal implementation CI intentionally stops at:

```text
IMPLEMENTED_PENDING_REREVIEW
```

A merge recommendation additionally requires authoritative final exact-head CI confirmation and a fresh official PR Inspector completion with zero blocking findings. User Merge remains an administrative action, not technical approval.

## Validation

```bash
python -m pip install -e '.[dev]'
pytest -q
python scripts/validate-ai-governance.py \
  --head-sha <exact_pr_head> \
  --pr-number <pr_number> \
  --ci-context .governance-ci-context.json \
  --emit-dir .governance-evidence
```
