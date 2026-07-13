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
    emit_evidence,
    evaluate_merge_gate,
    load_json,
    validate_repository_state,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate CE AI-governance profile, scope, progress, and review gates."
    )
    parser.add_argument("--profile", default=str(DEFAULT_PROFILE))
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--emit-dir", default=".governance-evidence")
    parser.add_argument("--review-package")
    parser.add_argument("--implementer-session-id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = validate_repository_state(
        profile_path=args.profile,
        state_path=args.state,
        schema_path=args.schema,
    )
    if not result["passed"]:
        payload = {
            "passed": False,
            "status": "FAIL-CLOSED",
            "errors": result["errors"],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 1

    emitted = emit_evidence(
        state=result["state"],
        head_sha=args.head_sha,
        output_dir=args.emit_dir,
    )

    review_package = load_json(args.review_package) if args.review_package else None
    merge_gate = evaluate_merge_gate(
        state=result["state"],
        head_sha=args.head_sha,
        review_package=review_package,
        exact_head_ci_passed=True,
        scope_gate_passed=True,
        progress_gate_passed=True,
        blocking_findings=0,
        implementer_session_id=args.implementer_session_id,
    )

    payload = {
        "passed": True,
        "status": merge_gate["status"],
        "profile_id": result["profile"]["profile_id"],
        "plan_id": result["state"]["plan"]["plan_id"],
        "scope_revision": result["state"]["scope_projection"]["scope_revision"],
        "reviewed_head_sha": args.head_sha,
        "emitted": emitted,
        "merge_gate": merge_gate,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    # Missing independent review is the expected pre-review state and does not fail implementation CI.
    if review_package is None:
        return 0
    return 0 if merge_gate["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
