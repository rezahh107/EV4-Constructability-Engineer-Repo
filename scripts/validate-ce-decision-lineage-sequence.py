#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_LINEAGE_FIELDS = (
    "decision_family",
    "decision_card_ref",
    "selected_option",
    "rejected_options",
    "evidence_refs",
    "evidence_state",
    "consumer_stage",
)
VALID_EVIDENCE_STATES = {"observed", "validated", "resolved", "derived", "proposed", "unverified", "insufficient_evidence"}
DIAGNOSTIC_MISSING_LINEAGE = "CE_LINEAGE_REQUIRED"
DIAGNOSTIC_INCOMPLETE_LINEAGE = "CE_LINEAGE_INCOMPLETE"
DIAGNOSTIC_LINEAGE_REPLACED = "CE_LINEAGE_REPLACED"
DIAGNOSTIC_LINEAGE_DROPPED = "CE_LINEAGE_DROPPED"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


def _load(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _lineage_key(item: dict[str, Any]) -> tuple[str, str]:
    return (str(item.get("decision_family", "")), str(item.get("decision_card_ref", "")))


def _validate_lineage_item(item: Any, path: str) -> list[Diagnostic]:
    if not isinstance(item, dict):
        return [Diagnostic(DIAGNOSTIC_INCOMPLETE_LINEAGE, path, "decision lineage entries must be objects.")]
    diagnostics: list[Diagnostic] = []
    for field in REQUIRED_LINEAGE_FIELDS:
        if field not in item:
            diagnostics.append(Diagnostic(DIAGNOSTIC_INCOMPLETE_LINEAGE, f"{path}.{field}", "required decision lineage field is missing."))
    for field in ("decision_family", "decision_card_ref", "selected_option", "consumer_stage"):
        if field in item and not _is_nonempty_string(item.get(field)):
            diagnostics.append(Diagnostic(DIAGNOSTIC_INCOMPLETE_LINEAGE, f"{path}.{field}", "decision lineage field must be a non-empty string."))
    if "rejected_options" in item and not isinstance(item.get("rejected_options"), list):
        diagnostics.append(Diagnostic(DIAGNOSTIC_INCOMPLETE_LINEAGE, f"{path}.rejected_options", "rejected_options must be an array, even when empty."))
    if "evidence_refs" in item:
        refs = item.get("evidence_refs")
        if not isinstance(refs, list) or not refs or not all(_is_nonempty_string(ref) for ref in refs):
            diagnostics.append(Diagnostic(DIAGNOSTIC_INCOMPLETE_LINEAGE, f"{path}.evidence_refs", "evidence_refs must contain at least one non-empty evidence reference."))
    if "evidence_state" in item and item.get("evidence_state") not in VALID_EVIDENCE_STATES:
        diagnostics.append(Diagnostic(DIAGNOSTIC_INCOMPLETE_LINEAGE, f"{path}.evidence_state", "evidence_state is not an allowed explicit evidence state."))
    return diagnostics


def _lineage_entries(container: dict[str, Any], path: str) -> tuple[list[tuple[int, dict[str, Any]]], list[Diagnostic]]:
    raw = container.get("decision_lineage")
    if not isinstance(raw, list) or not raw:
        return [], [Diagnostic(DIAGNOSTIC_MISSING_LINEAGE, f"{path}.decision_lineage", "CE intake/output must carry non-empty upstream Kernel decision lineage.")]
    diagnostics: list[Diagnostic] = []
    entries: list[tuple[int, dict[str, Any]]] = []
    for index, item in enumerate(raw):
        diagnostics.extend(_validate_lineage_item(item, f"{path}.decision_lineage[{index}]"))
        if isinstance(item, dict):
            entries.append((index, item))
    return entries, diagnostics


def validate_sequence(document: dict[str, Any]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    intake = document.get("ce_intake")
    output = document.get("ce_output")
    if not isinstance(intake, dict):
        diagnostics.append(Diagnostic(DIAGNOSTIC_MISSING_LINEAGE, "$.ce_intake", "sequence fixture must contain a CE intake object."))
        intake = {}
    if not isinstance(output, dict):
        diagnostics.append(Diagnostic(DIAGNOSTIC_MISSING_LINEAGE, "$.ce_output", "sequence fixture must contain a CE output object."))
        output = {}

    intake_entries, intake_diags = _lineage_entries(intake, "$.ce_intake")
    output_entries, output_diags = _lineage_entries(output, "$.ce_output")
    diagnostics.extend(intake_diags)
    diagnostics.extend(output_diags)
    if intake_diags or output_diags:
        return diagnostics

    output_by_key = {_lineage_key(item): (output_index, item) for output_index, item in output_entries}
    for intake_index, upstream in intake_entries:
        key = _lineage_key(upstream)
        downstream_pair = output_by_key.get(key)
        if downstream_pair is None:
            diagnostics.append(Diagnostic(DIAGNOSTIC_LINEAGE_DROPPED, f"$.ce_intake.decision_lineage[{intake_index}]", "CE output dropped an upstream decision lineage entry."))
            continue
        output_index, downstream = downstream_pair
        for field in REQUIRED_LINEAGE_FIELDS:
            if downstream.get(field) != upstream.get(field):
                diagnostics.append(Diagnostic(DIAGNOSTIC_LINEAGE_REPLACED, f"$.ce_output.decision_lineage[{output_index}].{field}", "CE output must preserve upstream decision lineage fields exactly; attach CE proof separately."))
    return diagnostics


def validate_file(path: Path) -> dict[str, Any]:
    value = _load(path)
    diagnostics = validate_sequence(value if isinstance(value, dict) else {})
    expected = (value or {}).get("expected", {}) if isinstance(value, dict) else {}
    passed = not diagnostics
    return {
        "path": str(path),
        "passed": passed,
        "expected_pass": expected.get("validation_pass"),
        "matches_expected": expected.get("validation_pass") is None or passed is bool(expected.get("validation_pass")),
        "diagnostics": [d.to_dict() for d in diagnostics],
    }


def iter_fixture_paths(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for path in paths:
        if path.is_dir():
            out.extend(sorted(p for p in path.rglob("*") if p.suffix.lower() in {".json", ".yaml", ".yml"}))
        else:
            out.append(path)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate CE intake-to-output Kernel decision lineage preservation sequence fixtures.")
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("fixtures/decision-lineage")])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    results = [validate_file(path) for path in iter_fixture_paths(args.paths)]
    failed = [r for r in results if not r["matches_expected"]]
    if args.json:
        print(json.dumps({"passed": not failed, "results": results}, indent=2, ensure_ascii=False))
    else:
        print("PASS" if not failed else "FAIL-CLOSED")
        for result in results:
            print(f"{result['path']}: passed={result['passed']} expected={result['expected_pass']} matches={result['matches_expected']}")
            for diagnostic in result["diagnostics"]:
                print(f"  - {diagnostic['code']} at {diagnostic['path']}: {diagnostic['message']}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
