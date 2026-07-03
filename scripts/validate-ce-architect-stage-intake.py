#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

Severity = Literal["error","warning","info","insufficient_evidence"]
ORDER = {"error":0,"insufficient_evidence":1,"warning":2,"info":3}
SCHEMAS = {
    "ev4-ce-architect-stage-intake@1.0.0": "schemas/ce_architect_stage_intake.v1.schema.json",
    "ev4-ce-architect-stage-intake@1.1.0": "schemas/ce_architect_stage_intake.v1_1.schema.json",
}
TRANSITION_TRACE_REQUIREMENTS = {
    "$.project_gate_transition.executed": ("deterministic_derived_metadata", "CE-MAP-A2C-01", "1.0.0"),
    "$.project_gate_transition.transition_id": ("deterministic_derived_metadata", "CE-MAP-A2C-01", "1.0.0"),
    "$.project_gate_transition.transition_version": ("deterministic_derived_metadata", "CE-MAP-A2C-01", "1.0.0"),
    "$.project_gate_transition.producer_repository": ("deterministic_derived_metadata", "CE-MAP-A2C-01", "1.0.0"),
    "$.project_gate_transition.source_bundle_id": ("direct_evidence_copy", None, None),
    "$.project_gate_transition.source_bundle_hash": ("deterministic_derived_metadata", "CE-MAP-A2C-02", "1.0.0"),
}
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

def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",",":")).encode("utf-8")

def _missing_required_property(error: ValidationError) -> str | None:
    if error.validator != "required":
        return None
    text = error.message
    if text.startswith("'") and "' is a required property" in text:
        return text.split("'", 2)[1]
    return None

def _is_ce_i11_missing_evidence_schema_error(error: ValidationError, value: Any) -> bool:
    if not isinstance(value, dict) or value.get("intake_status") != "insufficient_evidence":
        return False
    schema_path = list(error.absolute_schema_path)
    if "allOf" not in schema_path or "then" not in schema_path:
        return False
    data_path = list(error.absolute_path)
    if error.validator == "required":
        return data_path == [] and isinstance(error.validator_value, list) and "missing_evidence" in error.validator_value
    if error.validator == "minItems":
        return data_path == ["missing_evidence"] and error.validator_value == 1
    return False

def _is_mapping_trace_item_error(error: ValidationError) -> bool:
    return len(list(error.absolute_path)) >= 2 and list(error.absolute_path)[0] == "mapping_trace"

def _schema_diagnostic(error: ValidationError, value: Any) -> Diagnostic:
    if _is_ce_i11_missing_evidence_schema_error(error, value):
        return D("CE_I11_MISSING_EVIDENCE_REQUIRED","error","Insufficient-evidence intake must declare non-empty missing_evidence.","$.missing_evidence","CE-I11",schema_validator=error.validator)
    if isinstance(value, dict) and value.get("schema_id") == "ev4-ce-architect-stage-intake@1.1.0":
        path = jp(list(error.absolute_path))
        validator = error.validator
        if _is_mapping_trace_item_error(error):
            if validator == "required" and _missing_required_property(error) == "derivation_rule":
                return D("CE_I21_DERIVATION_RULE_INVALID","error","Derived transition metadata must declare the exact derivation rule and version.",path + ".derivation_rule","CE-I21",schema_validator=validator)
            if validator == "not":
                return D("CE_I21_UNDOCUMENTED_DERIVATION_RULE","error","Non-derived mapping trace rows must not declare derivation_rule.",path + ".derivation_rule","CE-I21",schema_validator=validator)
        if validator == "required" and list(error.absolute_path) == [] and "project_gate_transition" in as_list(error.validator_value):
            return D("CE_I13_TRANSITION_RECORD_REQUIRED","error","Project Gate-produced v1.1 intake must include project_gate_transition.","$.project_gate_transition","CE-I13",schema_validator=validator)
        if path in {"$.project_gate_transition.executed","$.project_gate_transition.transition_id","$.project_gate_transition.transition_version","$.project_gate_transition.producer_repository"}:
            return D("CE_I14_TRANSITION_IDENTITY_INVALID","error","Project Gate transition identity and producer must be exact.","$.project_gate_transition","CE-I14",schema_validator=validator)
        missing_required = _missing_required_property(error)
        if path.startswith("$.project_gate_transition.source_bundle"):
            return D("CE_I15_SOURCE_BUNDLE_TRACE_MISSING","error","Project Gate transition must preserve source bundle identity and hash.","$.project_gate_transition","CE-I15",schema_validator=validator)
        if validator == "required" and list(error.absolute_path) == ["project_gate_transition"]:
            if missing_required in {"executed","transition_id","transition_version","producer_repository"}:
                return D("CE_I14_TRANSITION_IDENTITY_INVALID","error","Project Gate transition identity and producer must be exact.","$.project_gate_transition","CE-I14",schema_validator=validator,missing_property=missing_required)
            if missing_required in {"source_bundle_id","source_bundle_hash"}:
                return D("CE_I15_SOURCE_BUNDLE_TRACE_MISSING","error","Project Gate transition must preserve source bundle identity and hash.","$.project_gate_transition","CE-I15",schema_validator=validator,missing_property=missing_required)
        if path == "$.ce_processing_prerequisites.intake_contains_ce_conclusions":
            return D("CE_I16_CE_REVIEW_NOT_EXECUTED_AT_INTAKE","error","Transition execution does not mean CE review has executed.","$.ce_processing_prerequisites.intake_contains_ce_conclusions","CE-I16",schema_validator=validator)
        if path == "$.ce_processing_prerequisites.intake_contains_builder_authorization":
            return D("CE_I17_BUILDER_AUTH_NOT_GRANTED_AT_INTAKE","error","Transition execution does not authorize Builder execution.","$.ce_processing_prerequisites.intake_contains_builder_authorization","CE-I17",schema_validator=validator)
        if path == "$.ce_processing_prerequisites.real_cross_repository_validation_available":
            return D("CE_I18_REAL_ELEMENTOR_VALIDATION_UNAVAILABLE","error","Real Elementor validation must remain unavailable unless proven separately.","$.ce_processing_prerequisites.real_cross_repository_validation_available","CE-I18",schema_validator=validator)
        if path.startswith("$.negative_boundary_assertions."):
            key = path.rsplit(".", 1)[-1]
            rule = FORBIDDEN_POSITIVE.get(key)
            if rule:
                return D("CE_OWNED_POSITIVE_CLAIM_FORBIDDEN","error","CE-owned or downstream readiness claim is forbidden at intake.",path,rule,schema_validator=validator,claim=key)
    return D("SCHEMA_VALIDATION_FAILED","error",error.message,jp(list(error.path)))

def _format_text_result(result: dict[str, Any]) -> str:
    lines = [f"status: {result['status']}"]
    for diag in result.get("diagnostics", []):
        lines.append(f"[{diag['severity'].upper()}] {diag['code']} at {diag['path']}: {diag['message']}")
    return "\n".join(lines)

def validate_source_bundle_binding(intake: dict[str, Any], source_bundle: dict[str, Any]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not isinstance(intake, dict):
        return [D("CE_I21_SOURCE_BUNDLE_BINDING_INPUT_INVALID","error","Intake must be an object for source-bundle binding verification.","$","CE-I21")]
    if not isinstance(source_bundle, dict):
        return [D("CE_I21_SOURCE_BUNDLE_BINDING_INPUT_INVALID","error","Source bundle must be an object for binding verification.","$","CE-I21")]
    transition = as_dict(intake.get("project_gate_transition"))
    expected_bundle_id = transition.get("source_bundle_id")
    observed_bundle_id = source_bundle.get("bundle_id")
    if observed_bundle_id != expected_bundle_id:
        diagnostics.append(D("CE_I21_SOURCE_BUNDLE_ID_MISMATCH","error","source bundle_id must match project_gate_transition.source_bundle_id.","$.project_gate_transition.source_bundle_id","CE-I21",expected=expected_bundle_id,observed=observed_bundle_id))
    expected_hash = as_dict(transition.get("source_bundle_hash")).get("value")
    observed_hash = hashlib.sha256(canonical_json_bytes(source_bundle)).hexdigest()
    if observed_hash != expected_hash:
        diagnostics.append(D("CE_I21_SOURCE_BUNDLE_HASH_MISMATCH","error","source_bundle_hash must match canonical SHA-256 of the explicitly supplied source bundle.","$.project_gate_transition.source_bundle_hash.value","CE-I21",expected=expected_hash,observed=observed_hash))
    return diagnostics

class CEArchitectStageIntakeValidator:
    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root)
        self.schemas: dict[str, Any] = {}
        self.validators: dict[str, Draft202012Validator] = {}
        for schema_id, rel_path in SCHEMAS.items():
            path = self.repo_root / rel_path
            if not path.exists():
                continue
            with path.open(encoding="utf-8") as f:
                schema = json.load(f)
            Draft202012Validator.check_schema(schema)
            self.schemas[schema_id] = schema
            self.validators[schema_id] = Draft202012Validator(schema)

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
        schema_id = value.get("schema_id")
        validator = self.validators.get(schema_id)
        if validator is None:
            return self._result(value, [D("UNSUPPORTED_SCHEMA_ID","error","Unsupported CE Architect-stage intake schema_id.","$.schema_id",observed_schema_id=schema_id)])
        schema_diags = [_schema_diagnostic(e, value) for e in sorted(validator.iter_errors(value), key=lambda e:(jp(list(e.path)), e.validator, jp(list(e.schema_path))))]
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
        seen_pairs = set()
        seen_targets = {}
        for i, item in enumerate(trace):
            if not isinstance(item, dict): continue
            pair = (item.get("source_path"), item.get("target_path"))
            target = item.get("target_path")
            if pair in seen_pairs:
                out.append(D("CE_I10_DUPLICATE_MAPPING_TRACE","error","Mapping trace entries must be unique.",f"$.mapping_trace[{i}]","CE-I10"))
            seen_pairs.add(pair)
            if isinstance(target, str):
                seen_targets.setdefault(target, []).append((i, item))
            if item.get("classification") != "deterministic_derived_metadata" and item.get("derivation_rule") is not None:
                out.append(D("CE_I21_UNDOCUMENTED_DERIVATION_RULE","error","Non-derived mapping trace rows must not declare derivation_rule.",f"$.mapping_trace[{i}].derivation_rule","CE-I21",target_path=target))
            if item.get("classification") == "deterministic_derived_metadata" and item.get("derivation_rule") is None:
                out.append(D("CE_I21_DERIVATION_RULE_INVALID","error","Derived transition metadata must declare the exact derivation rule and version.",f"$.mapping_trace[{i}].derivation_rule","CE-I21",target_path=target))
            if item.get("classification") == "deterministic_structural_projection" and item.get("ordering_rule") not in {"sort_by_id","sort_by_source_path_then_target_path"}:
                out.append(D("CE_I10_MAPPING_ORDER_NOT_DETERMINISTIC","error","Structural projections require deterministic ordering.",f"$.mapping_trace[{i}].ordering_rule","CE-I10"))
        if value.get("schema_id") == "ev4-ce-architect-stage-intake@1.1.0":
            out.extend(self._transition_semantics(value, seen_targets))
        return out

    def _transition_semantics(self, value: dict[str, Any], seen_targets: dict[str, list[tuple[int, dict[str, Any]]]]) -> list[Diagnostic]:
        out: list[Diagnostic] = []
        transition = as_dict(value.get("project_gate_transition"))
        source = as_dict(value.get("source_repository_ref"))
        if transition.get("source_bundle_id") != source.get("bundle_id"):
            out.append(D("CE_I15_SOURCE_BUNDLE_TRACE_MISMATCH","error","source_bundle_id must match source_repository_ref.bundle_id.","$.project_gate_transition.source_bundle_id","CE-I15"))
        if as_dict(transition.get("source_bundle_hash")).get("scope") != "source_bundle":
            out.append(D("CE_I15_SOURCE_BUNDLE_HASH_SCOPE_INVALID","error","source_bundle_hash scope must be source_bundle.","$.project_gate_transition.source_bundle_hash.scope","CE-I15"))
        prereq = as_dict(value.get("ce_processing_prerequisites"))
        if prereq.get("intake_contains_ce_conclusions") is not False:
            out.append(D("CE_I16_CE_REVIEW_NOT_EXECUTED_AT_INTAKE","error","Transition execution does not mean CE review has executed.","$.ce_processing_prerequisites.intake_contains_ce_conclusions","CE-I16"))
        if prereq.get("intake_contains_builder_authorization") is not False:
            out.append(D("CE_I17_BUILDER_AUTH_NOT_GRANTED_AT_INTAKE","error","Transition execution does not authorize Builder execution.","$.ce_processing_prerequisites.intake_contains_builder_authorization","CE-I17"))
        if prereq.get("real_cross_repository_validation_available") is not False:
            out.append(D("CE_I18_REAL_ELEMENTOR_VALIDATION_UNAVAILABLE","error","Real Elementor validation must remain unavailable unless proven separately.","$.ce_processing_prerequisites.real_cross_repository_validation_available","CE-I18"))
        out.extend(self._validate_transition_trace(seen_targets))
        return out

    def _validate_transition_trace(self, seen_targets: dict[str, list[tuple[int, dict[str, Any]]]]) -> list[Diagnostic]:
        out: list[Diagnostic] = []
        for target_path, (expected_class, expected_rule, expected_version) in TRANSITION_TRACE_REQUIREMENTS.items():
            rows = seen_targets.get(target_path, [])
            if len(rows) != 1:
                code = "CE_I21_TRANSITION_TRACE_MISSING" if not rows else "CE_I21_TRANSITION_TRACE_DUPLICATE"
                out.append(D(code,"error","Mapping trace must contain exactly one row for each Project Gate transition metadata target.",target_path,"CE-I21",target_path=target_path,observed_count=len(rows)))
                continue
            index, row = rows[0]
            if row.get("classification") != expected_class:
                out.append(D("CE_I21_TRANSITION_TRACE_CLASSIFICATION_INVALID","error","Project Gate transition metadata mapping trace uses the wrong classification.",f"$.mapping_trace[{index}].classification","CE-I21",target_path=target_path,expected=expected_class,observed=row.get("classification")))
            rule = row.get("derivation_rule")
            if expected_rule is None:
                if rule is not None:
                    out.append(D("CE_I21_UNDOCUMENTED_DERIVATION_RULE","error","Direct transition evidence copy must not declare a derivation rule.",f"$.mapping_trace[{index}].derivation_rule","CE-I21",target_path=target_path))
            else:
                if not isinstance(rule, dict) or rule.get("id") != expected_rule or rule.get("version") != expected_version:
                    out.append(D("CE_I21_DERIVATION_RULE_INVALID","error","Derived transition metadata must declare the exact derivation rule and version.",f"$.mapping_trace[{index}].derivation_rule","CE-I21",target_path=target_path,expected_rule=expected_rule,expected_version=expected_version))
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
    if isinstance(parts[-1], int):
        cur[parts[-1]] = new
    else:
        cur[parts[-1]] = new
def _delete(value, path):
    cur = value; parts = _tokens(path)
    for p in parts[:-1]: cur = cur[p]
    if isinstance(parts[-1], int):
        del cur[parts[-1]]
    else:
        del cur[parts[-1]]

def _load_cases(repo_root: Path, cases_file: Path, expected: str, validator: CEArchitectStageIntakeValidator):
    data = json.loads(cases_file.read_text(encoding="utf-8"))
    base = json.loads((cases_file.parent / data["base_fixture"]).resolve().read_text(encoding="utf-8"))
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
    roots = [repo_root / "fixtures/architect-stage-intake", repo_root / "fixtures/architect-stage-intake-v1-1"]
    validator = CEArchitectStageIntakeValidator(repo_root)
    failures = 0; reports = []
    for base in roots:
        if not base.exists():
            continue
        for dirname, expected in [("valid","valid"),("invalid","invalid"),("insufficient-evidence","insufficient_evidence")]:
            folder = base/dirname
            if not folder.exists():
                continue
            for path in sorted(folder.glob("*.json")):
                if path.name.startswith("cases"):
                    f, r = _load_cases(repo_root, path, expected, validator); failures += f; reports.extend(r); continue
                result = validator.validate_file(path); ok = result["status"] == expected
                failures += 0 if ok else 1
                reports.append({"fixture": str(path.relative_to(repo_root)), "expected": expected, "actual": result["status"], "ok": ok, "diagnostic_codes": [d["code"] for d in result["diagnostics"]]})
    return failures, reports

def _read_json_file(path: Path) -> tuple[Any, list[Diagnostic]]:
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f), []
    except json.JSONDecodeError as exc:
        return None, [D("MALFORMED_JSON","error","File is not valid JSON.","$",line=exc.lineno,column=exc.colno)]
    except OSError as exc:
        return None, [D("FILE_READ_ERROR","error","File could not be read.","$",error_type=type(exc).__name__)]

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=Path.cwd())
    parser.add_argument("--file", type=Path)
    parser.add_argument("--source-bundle", type=Path)
    parser.add_argument("--expect", choices=["valid","invalid","insufficient_evidence"])
    parser.add_argument("--format", choices=["text","json"], default="text")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    if args.file:
        validator = CEArchitectStageIntakeValidator(root)
        intake_path = args.file if args.file.is_absolute() else root / args.file
        result = validator.validate_file(intake_path)
        if args.source_bundle and result["status"] != "invalid":
            source_path = args.source_bundle if args.source_bundle.is_absolute() else root / args.source_bundle
            source_bundle, source_diags = _read_json_file(source_path)
            intake_value, intake_diags = _read_json_file(intake_path)
            extra = source_diags or intake_diags or validate_source_bundle_binding(intake_value, source_bundle)
            if extra:
                result = validator._result({}, [D(d["code"], d["severity"], d["message"], d["path"], d.get("rule_id"), **d.get("details", {})) for d in result.get("diagnostics", [])] + extra)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",",":")) if args.format == "json" else _format_text_result(result))
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
