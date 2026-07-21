#!/usr/bin/env python3
"""Fail-closed CE bootstrap validator and integrated router."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from ce_bootstrap_spec import *
from ce_bootstrap_validation import *
from ce_bootstrap_routing import *

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--request-json", type=Path)
    parser.add_argument("--message")
    parser.add_argument("--operating-mode", choices=sorted(OPERATING_MODES), default="auto")
    parser.add_argument("--active-ce-run", action="store_true")
    parser.add_argument("--attachment", action="append", type=Path, default=[])
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    routing_requested = args.request_json is not None or args.message is not None or args.active_ce_run or bool(args.attachment)
    if routing_requested:
        if args.request_json:
            request_path = args.request_json if args.request_json.is_absolute() else args.root / args.request_json
            request = RoutingRequest.from_value(strict_load_json(request_path))
        else:
            request = RoutingRequest(args.message or "", args.operating_mode, args.active_ce_run, tuple(args.attachment))
        result = route_request(args.root, request)
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        else:
            for key in ("activation_authorized", "operating_mode", "route", "pipeline_execution", "authorization_reason", "diagnostic_code"):
                if key in result:
                    print(f"{key}: {result[key]}")
        return 0 if result["route"] in {"architect_intake_validation", "waiting_for_ce_input", "repository_maintenance", "no_bootstrap_authorization"} else 1

    result = validate_repository(args.root)
    print("CE bootstrap semantic validation passed.")
    print(f"Contract: {result['contract']}")
    print(f"Trigger: {result['trigger']}")
    print(f"Routing cases: {result['routing_cases']}")
    print(f"Stable forbidden operations: {result['forbidden_operations']}")
    print(f"First stage: {result['first_stage']}")
    print(f"Source binding: {result['source_binding']}")
    print(f"Receipt validation: {result['receipt_validation']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"CE bootstrap semantic validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
