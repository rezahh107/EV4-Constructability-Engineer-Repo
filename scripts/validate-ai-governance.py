from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validator.ai_governance import (
    DEFAULT_PROFILE,
    DEFAULT_SCHEMA,
    DEFAULT_STATE,
    derive_gate_evidence,
    emit_evidence,
    evaluate_merge_gate,
    inspect_canonical_review_bundle,
    record_ci_context,
    validate_repository_state,
    verify_pr_inspector_review_bundle,
)


def _print(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate CE AI-governance profile, scope, progress, and review gates."
    )
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--emit-dir", default=".governance-evidence")
    parser.add_argument("--ci-context")
    parser.add_argument("--record-ci-context")
    parser.add_argument("--review-bundle-dir")
    parser.add_argument("--inspector-source-dir")
    parser.add_argument("--implementer-session-id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = validate_repository_state(
            profile_path=args.profile,
            state_path=args.state,
            schema_path=args.schema,
            repository_root=ROOT,
        )
        if not result["passed"]:
            _print(
                {
                    "passed": False,
                    "status": "FAIL-CLOSED",
                    "diagnostics": result["diagnostics"],
                }
            )
            return 1
        verification = result["verification"]

        if args.record_ci_context:
            context = record_ci_context(
                verification,
                head_sha=args.head_sha,
                pr_number=args.pr_number,
                output_path=args.record_ci_context,
            )
            _print(
                {
                    "passed": True,
                    "status": "CI_EXECUTION_CONTEXT_RECORDED",
                    "context": context,
                    "output": args.record_ci_context,
                }
            )
            return 0

        gate_evidence = derive_gate_evidence(
            verification,
            head_sha=args.head_sha,
            pr_number=args.pr_number,
            ci_context_path=args.ci_context,
        )

        review_capability = None
        review_bundle_evidence = None
        if args.review_bundle_dir:
            profile_review = result["profile"]["review_protocol"]
            review_bundle_evidence = inspect_canonical_review_bundle(
                args.review_bundle_dir,
                expected_repository=result["state"]["repository"]["name"],
                expected_pr_number=args.pr_number,
                expected_head_sha=args.head_sha,
                expected_scope_revision=result["state"]["scope_projection"]["scope_revision"],
                minimum_protocol_version=profile_review["minimum_protocol_version"],
                expected_inspector_repository=profile_review["inspector_repository"],
                implementer_session_id=args.implementer_session_id,
            )
            if not args.inspector_source_dir:
                raise ValueError(
                    "--inspector-source-dir is required for authoritative official completion"
                )
            review_capability = verify_pr_inspector_review_bundle(
                review_bundle_evidence,
                inspector_source_directory=args.inspector_source_dir,
            )

        merge_gate = evaluate_merge_gate(
            gate_evidence=gate_evidence,
            review_capability=review_capability,
        )
        emitted = emit_evidence(
            gate_evidence=gate_evidence,
            output_dir=args.emit_dir,
            review_capability=review_capability,
        )
        payload: dict[str, object] = {
            "passed": True,
            "implementation_status": "implemented_pending_rereview",
            "status": merge_gate["status"],
            "profile_id": result["profile"]["profile_id"],
            "profile_version": result["profile"]["profile_version"],
            "plan_id": result["state"]["plan"]["plan_id"],
            "scope_revision": result["state"]["scope_projection"]["scope_revision"],
            "reviewed_head_sha": args.head_sha,
            "gate_evidence": {
                "scope_gate_passed": gate_evidence.scope_gate_passed,
                "progress_gate_passed": gate_evidence.progress_gate_passed,
                "exact_head_context_verified": gate_evidence.exact_head_context_verified,
                "exact_head_ci_passed": gate_evidence.exact_head_ci_passed,
                "evidence_state": gate_evidence.evidence_state,
                "diagnostics": list(gate_evidence.diagnostics),
            },
            "review_bundle_verified": review_bundle_evidence is not None,
            "authoritative_review_capability": review_capability is not None,
            "emitted": emitted,
            "merge_gate": merge_gate,
            "merge_performed": False,
            "approval_performed": False,
            "deployment_performed": False,
        }
        _print(payload)

        if args.review_bundle_dir:
            return 0 if merge_gate["passed"] else 1
        return 0
    except Exception as exc:
        _print(
            {
                "passed": False,
                "status": "FAIL-CLOSED",
                "diagnostics": [
                    {
                        "stage": "runtime",
                        "path": "$",
                        "message": str(exc),
                    }
                ],
                "merge_performed": False,
                "approval_performed": False,
                "deployment_performed": False,
            }
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
