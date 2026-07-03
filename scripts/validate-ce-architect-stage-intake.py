#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from jsonschema import Draft202012Validator

Severity = Literal["error","warning","info","insufficient_evidence"]
ORDER = {"error":0,"insufficient_evidence":1,"warning":2,"info":3}
FORBIDDEN_POSITIVE = {
    "constructability_proven":"CE-I06","ce_approved":"CE-I06","implementation_strategy_selected":"CE-I06",
    "elementor_feasibility_proven":"CE-I06","proof_state_resolved":"CE-I06","ce_review_complete":"CE-I06",
    "builder_ready":"CE-I07","builder_executable":"CE-I07","builder_action_authorized":"CE-I07",
    "builder_runtime_intake_authorized":"CE-I07","production_ready":"CE-I07","responsive_complete":"CE-I07",
}
FORBIDDEN_KEYS = {"ce_review_units":"CE-I06","action_proposed":"CE-I06","proof_states":"CE-I06","constructability_review":"CE-I06","implementation_strategy_map":"CE-I06","builder_executable_package":"CE-I07","first_safe_builder_batch":"CE-I07","confirmation_request":"CE-I07"}

@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    path: str = "$"
    rule_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    def key(self): return (self.path, ORDER[self.severity], self.rule_id or "", self.code, self.message)
    def to_dict(self):
        out = {"code": self.code, "severity": self.severity, "message": self.message, "path": self.path}
        if self.rule_id: out["rule_id"] = self.rule_id
        if self.details: out["details"] = self.details
        return out

def D(code, severity, message, path="$", rule_id=None, **details): return Diagnostic(code, severity, message, path, rule_id, details)
def jp(parts):
    out = "$"
    for part in parts: out += f"[{part}]" if isinstance(part, int) else f".{part}"
    return out
def as_list(value): return value if isinstance(value, list) else []
def as_dict(value): return value if isinstance(value, dict) else {}

class CEArchitectStageIntakeValidator:
    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root)
        with (self.repo_root / "schemas/ce_architect_stage_intake.v1.schema.json").open(encoding="utf-8") as f:
            self.schema = json.load(f)
        Draft202012Validator.check_schema(self.schema)
        self.validator = Draft202012Validator(self.schema)

    def validate_file(self, path: str | Path) -> dict[str, Any]:
        try:
            with Path(path).open(encoding="utf-8") as f:
                value = json.load(f)
        except json.JSONDecodeError as exc:
            return self._result(None, [D("MALFORMED_JSON","error","File is not valid JSON.","$",line=exc.lineno,column=exc.colno)])
        except OSError as exc:
            return self._result(None, [D("FILE_READ_ERROR","error","File could not be read.","$",error_type=type(exc).__name__)])
        return self.validate_value(value)

    def validate_value(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return self._result(value, [D("INPUT_NOT_OBJECT","error","CE Architect-stage intake must be a JSON object.","$",observed_type=type(value).__name__)])
        schema_diags = [D("SCHEMA_VALIDATION_FAILED","error",e.message,jp(list(e.path))) for e in sorted(self.validator.iter_errors(value), key=lambda e:(jp(list(e.path)), e.message))]
        if schema_diags:
            return self._result(value, schema_diags)
        return self._result(value, self._semantic(value))

    def _semantic(self, value: dict[str, Any]) -> list[Diagnostic]:
        out = self._forbidden(value)
        evidence = {e.get("evidence_id"): e for e in as_list(value.get("evidence_register")) if isinstance(e, dict) and isinstance(e.get("evidence_id"), str)}
        nodes = {n.get("source_node_id") for n in as_list(as_dict(value.get("structure_projection")).get("nodes")) if isinstance(n, dict) and isinstance(n.get("source_node_id"), str)}
        selected = as_dict(value.get("selected_architecture"))
        if as_dict(value.get("source_repository_ref")).get("ref") == "/builder-feed-export":
            out.append(D("CE_I12_LEGACY_SOURCE_STAGE_FORBIDDEN","error","/builder-feed-export is legacy compatibility-only, not canonical intake source.","$.source_repository_ref.ref","CE-I12"))
        if selected.get("approved_structure_ref") not in nodes:
            out.append(D("CE_I03_APPROVED_STRUCTURE_REF_MISSING","error","Approved structure reference must point to a preserved node.","$.selected_architecture.approved_structure_ref","CE-I03"))
        for i, ref in enumerate(as_list(selected.get("decision_source_refs"))):
            if ref not in evidence:
                out.append(D("CE_I08_UNKNOWN_DECISION_EVIDENCE_REF","error","Decision evidence reference is not preserved.","$.selected_architecture.decision_source_refs[%d]" % i,"CE-I08",missing_ref=ref))
        for i, node in enumerate(as_list(as_dict(value.get("structure_projection")).get("nodes"))):
            if not isinstance(node, dict): continue
            for j, ref in enumerate(as_list(node.get("evidence_refs"))):
                if ref not in evidence:
                    out.append(D("CE_I03_UNKNOWN_STRUCTURE_EVIDENCE_REF","error","Structure evidence reference is not preserved.",f"$.structure_projection.nodes[{i}].evidence_refs[{j}]","CE-I03",missing_ref=ref))
        for i, item in enumerate(as_list(value.get("unresolved_evidence"))):
            if isinstance(item, dict) and item.get("state") != "insufficient_evidence":
                out.append(D("CE_I04_UNRESOLVED_STATE_CHANGED","error","Unresolved evidence must remain insufficient_evidence.",f"$.unresolved_evidence[{i}].state","CE-I04"))
        for i, item in enumerate(as_list(value.get("evidence_register"))):
            if isinstance(item, dict) and item.get("state") == "validated" and item.get("fact_class") in {"unresolved_unknown","synthetic_fixture"}:
                out.append(D("CE_I05_EVIDENCE_STATE_UPGRADED","error","Architect evidence state was upgraded without evidence.",f"$.evidence_register[{i}].state","CE-I05"))
        trace = as_list(value.get("mapping_trace"))
        seen = set()
        for i, item in enumerate(trace):
            if not isinstance(item, dict): continue
            pair = (item.get("source_path"), item.get("target_path"))
            if pair in seen:
                out.append(D("CE_I10_DUPLICATE_MAPPING_TRACE","error","Mapping trace entries must be unique.",f"$.mapping_trace[{i}]","CE-I10"))
            seen.add(pair)
            if item.get("classification") == "deterministic_structural_projection" and item.get("ordering_rule") not in {"sort_by_id","sort_by_source_path_then_target_path"}:
                out.append(D("CE_I10_MAPPING_ORDER_NOT_DETERMINISTIC","error","Structural projections require deterministic ordering.",f"$.mapping_trace[{i}].ordering_rule","CE-I10"))
        if value.get("intake_status") == "insufficient_evidence" and not as_list(value.get("missing_evidence")):
            out.append(D("CE_I11_MISSING_EVIDENCE_REQUIRED","error","Insufficient-evidence intake must declare missing evidence.","$.missing_evidence","CE-I11"))
        return out

    def _forbidden(self, value: Any, path="$") -> list[Diagnostic]:
        out = []
        if isinstance(value, dict):
            for k, child in value.items():
                p = f"{path}.{k}"
                if k in FORBIDDEN_POSITIVE and child is not False:
                    out.append(D("CE_OWNED_POSITIVE_CLAIM_FORBIDDEN","error","CE-owned or downstream readiness claim is forbidden at intake.",p,FORBIDDEN_POSITIVE[k],claim=k))
                if k in FORBIDDEN_KEYS:
                    out.append(D("CE_OWNED_SECTION_FORBIDDEN_AT_INTAKE","error","CE-owned processing section is forbidden at intake.",p,FORBIDDEN_KEYS[k],key=k))
                out.extend(self._forbidden(child,p))
        elif isinstance(value, list):
            for i, child in enumerate(value): out.extend(self._forbidden(child,f"{path}[{i}]"))
        return out

    def _result(self, value: Any, diags: list[Diagnostic]) -> dict[str, Any]:
        ordered = sorted(diags, key=lambda d:d.key())
        status = "invalid" if any(d.severity=="error" for d in ordered) else "insufficient_evidence" if isinstance(value, dict) and value.get("intake_status")=="insufficient_evidence" else "valid"
        return {"status": status, "diagnostics": [d.to_dict() for d in ordered]}

def _tokens(path): return [int(p) if p.isdigit() else p for p in path.split(".") if p]
def _set(value, path, new):
    cur = value; parts = _tokens(path)
    for p in parts[:-1]: cur = cur[p]
    cur[parts[-1]] = new
def _delete(value, path):
    cur = value; parts = _tokens(path)
    for p in parts[:-1]: cur = cur[p]
    del cur[parts[-1]]

def _load_cases(repo_root: Path, cases_file: Path, expected: str):
    data = json.loads(cases_file.read_text(encoding="utf-8"))
    base = json.loads((cases_file.parent / data["base_fixture"]).resolve().read_text(encoding="utf-8"))
    validator = CEArchitectStageIntakeValidator(repo_root)
    failures = 0; reports = []
    for case in data["cases"]:
        payload = copy.deepcopy(base)
        for mutation in case.get("mutations", []):
            if mutation["op"] == "set": _set(payload, mutation["path"], mutation["value"])
            elif mutation["op"] == "delete": _delete(payload, mutation["path"])
            else: raise ValueError(f"Unsupported mutation op: {mutation['op']}")
        result = validator.validate_value(payload)
        ok = result["status"] == expected
        failures += 0 if ok else 1
        reports.append({"fixture": f"{cases_file.relative_to(repo_root)}#{case['case_id']}", "expected": expected, "actual": result["status"], "ok": ok, "diagnostic_codes": [d["code"] for d in result["diagnostics"]]})
    return failures, reports

def validate_fixture_suite(repo_root: Path):
    base = repo_root / "fixtures/architect-stage-intake"
    validator = CEArchitectStageIntakeValidator(repo_root)
    failures = 0; reports = []
    for dirname, expected in [("valid","valid"),("invalid","invalid"),("insufficient-evidence","insufficient_evidence")]:
        for path in sorted((base/dirname).glob("*.json")):
            if path.name == "cases.v1.json":
                f, r = _load_cases(repo_root, path, expected); failures += f; reports.extend(r); continue
            result = validator.validate_file(path); ok = result["status"] == expected
            failures += 0 if ok else 1
            reports.append({"fixture": str(path.relative_to(repo_root)), "expected": expected, "actual": result["status"], "ok": ok, "diagnostic_codes": [d["code"] for d in result["diagnostics"]]})
    return failures, reports

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=Path.cwd())
    parser.add_argument("--file", type=Path)
    parser.add_argument("--expect", choices=["valid","invalid","insufficient_evidence"])
    parser.add_argument("--format", choices=["text","json"], default="text")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    validator = CEArchitectStageIntakeValidator(root)
    if args.file:
        result = validator.validate_file(args.file if args.file.is_absolute() else root / args.file)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",",":")) if args.format == "json" else f"status: {result['status']}")
        if args.expect: return 0 if result["status"] == args.expect else 1
        return 0 if result["status"] == "valid" else 2 if result["status"] == "insufficient_evidence" else 1
    failures, reports = validate_fixture_suite(root)
    if args.format == "json": print(json.dumps({"failures":failures,"reports":reports}, ensure_ascii=False, sort_keys=True, separators=(",",":")))
    else:
        for r in reports: print(f"{'ok' if r['ok'] else 'FAIL'}: {r['fixture']} expected={r['expected']} actual={r['actual']} codes={','.join(r['diagnostic_codes'])}")
        print(f"fixture_failures: {failures}")
    return 0 if failures == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
