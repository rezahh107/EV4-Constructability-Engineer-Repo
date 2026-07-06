from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

EXPECTED_PROJECT_GATE_COMMIT = "ea19c22c32458068e167b267da8b819e9263cdf7"
EXPECTED_PRODUCER_EXPORT_SHA256 = "c556bb9deeccdcafeb885a1c8b3dbd660e4e06f452b8ac3c7040d21377465fcc"
EXPECTED_STAGE_BUNDLE_SHA256 = "fc1ec6d3f7aecbabaeb0a3455d9eb42788779d2fa1531e8c7b2cb3bde706a886"
PIPELINE_ID = "ev4-ce-project-gate-producer-pipeline"
CE_REPOSITORY = "rezahh107/EV4-Constructability-Engineer-Repo"
PROJECT_GATE_REPOSITORY = "rezahh107/EV4-Project-Gate"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


def _reject_non_json_constant(value: str) -> None:
    raise ValueError(f"Non-standard JSON numeric constant is forbidden: {value}")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle, parse_constant=_reject_non_json_constant)
    if not isinstance(data, dict):
        raise TypeError(f"Expected JSON object in {path}")
    return data


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _schema_errors(schema: dict[str, Any], document: dict[str, Any], prefix: str) -> list[Diagnostic]:
    validator = Draft202012Validator(schema)
    diagnostics: list[Diagnostic] = []
    for error in sorted(validator.iter_errors(document), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or prefix
        diagnostics.append(Diagnostic("CE_PG_SCHEMA_INVALID", location, error.message))
    return diagnostics


def validate_project_gate_lock(repo_root: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    lock_path = repo_root / "contracts/project-gate/producer-gate-export.v1.lock.json"
    vendored_path = repo_root / "contracts/project-gate/producer-gate-export.v1.schema.json"

    if not lock_path.is_file():
        return [Diagnostic("CE_PG_LOCK_MISSING", str(lock_path), "Project Gate contract lock is missing.")]
    if not vendored_path.is_file():
        return [Diagnostic("CE_PG_VENDORED_CONTRACT_MISSING", str(vendored_path), "Vendored Producer Gate Export contract is missing.")]

    lock = load_json(lock_path)
    vendored_hash = sha256_file(vendored_path)

    expected = {
        "lock_schema": "project-gate-common-contract-lock.v1",
        "contract_owner": PROJECT_GATE_REPOSITORY,
        "contract_id": "producer-gate-export.v1",
        "contract_version": "1.0.0",
    }
    for key, expected_value in expected.items():
        if lock.get(key) != expected_value:
            diagnostics.append(Diagnostic("CE_PG_LOCK_FIELD_MISMATCH", key, f"Expected {expected_value!r}."))

    canonical = lock.get("canonical") if isinstance(lock.get("canonical"), dict) else {}
    vendored = lock.get("vendored") if isinstance(lock.get("vendored"), dict) else {}
    verification = lock.get("verification") if isinstance(lock.get("verification"), dict) else {}

    if canonical.get("repository") != PROJECT_GATE_REPOSITORY:
        diagnostics.append(Diagnostic("CE_PG_LOCK_OWNER_DRIFT", "canonical.repository", "Canonical owner must remain Project Gate."))
    if canonical.get("path") != "contracts/common/producer-gate-export.v1.schema.json":
        diagnostics.append(Diagnostic("CE_PG_LOCK_PATH_DRIFT", "canonical.path", "Canonical path drifted."))
    if canonical.get("commit_sha") != EXPECTED_PROJECT_GATE_COMMIT:
        diagnostics.append(Diagnostic("CE_PG_MOVING_REF_FORBIDDEN", "canonical.commit_sha", "Canonical commit must be the immutable Prompt 0 merge commit."))
    if canonical.get("file_sha256") != EXPECTED_PRODUCER_EXPORT_SHA256:
        diagnostics.append(Diagnostic("CE_PG_LOCK_HASH_DRIFT", "canonical.file_sha256", "Canonical SHA-256 does not match Prompt 0 pin."))
    if vendored.get("repository") != CE_REPOSITORY:
        diagnostics.append(Diagnostic("CE_PG_LOCK_VENDOR_REPO_DRIFT", "vendored.repository", "Vendored repository must be CE."))
    if vendored.get("path") != "contracts/project-gate/producer-gate-export.v1.schema.json":
        diagnostics.append(Diagnostic("CE_PG_LOCK_VENDOR_PATH_DRIFT", "vendored.path", "Vendored path drifted."))
    if vendored.get("file_sha256") != vendored_hash:
        diagnostics.append(Diagnostic("CE_PG_VENDORED_HASH_MISMATCH", "vendored.file_sha256", "Vendored lock hash does not match local file bytes."))
    if vendored_hash != EXPECTED_PRODUCER_EXPORT_SHA256:
        diagnostics.append(Diagnostic("CE_PG_VENDORED_BYTES_MISMATCH", str(vendored_path), "Vendored file bytes do not match the immutable Project Gate contract hash."))
    if vendored.get("local_copy_authoritative") is not False:
        diagnostics.append(Diagnostic("CE_PG_LOCAL_COPY_NOT_AUTHORITATIVE", "vendored.local_copy_authoritative", "Local copy must not be authoritative."))
    if verification.get("byte_equality_required") is not True:
        diagnostics.append(Diagnostic("CE_PG_BYTE_EQUALITY_REQUIRED", "verification.byte_equality_required", "Exact byte equality must be required."))
    if verification.get("compare_against_moving_default_branch") is not False:
        diagnostics.append(Diagnostic("CE_PG_MOVING_DEFAULT_BRANCH_FORBIDDEN", "verification.compare_against_moving_default_branch", "Moving default branch comparison is forbidden."))
    return diagnostics


def validate_pipeline_manifest(repo_root: Path) -> list[Diagnostic]:
    schema = load_json(repo_root / "schemas/ce_pipeline_manifest.v1.schema.json")
    manifest = load_json(repo_root / "manifests/ce_pipeline_manifest.v1.json")
    diagnostics = _schema_errors(schema, manifest, "ce_pipeline_manifest")
    stages = manifest.get("project_execution_stages", [])
    if not isinstance(stages, list):
        return diagnostics

    ids = [stage.get("stage_id") for stage in stages if isinstance(stage, dict)]
    ordinals = [stage.get("ordinal") for stage in stages if isinstance(stage, dict)]
    if len(ids) != len(set(ids)):
        diagnostics.append(Diagnostic("CE_PIPELINE_DUPLICATE_STAGE_ID", "project_execution_stages", "Stage IDs must be unique."))
    if len(ordinals) != len(set(ordinals)):
        diagnostics.append(Diagnostic("CE_PIPELINE_DUPLICATE_ORDINAL", "project_execution_stages", "Stage ordinals must be unique."))
    if ordinals != sorted(ordinals):
        diagnostics.append(Diagnostic("CE_PIPELINE_NON_DETERMINISTIC_ORDER", "project_execution_stages", "Stages must be sorted by ordinal."))
    if ids[-1:] != ["project_gate_export"]:
        diagnostics.append(Diagnostic("CE_PIPELINE_EXPORT_NOT_FINAL", "project_execution_stages[-1].stage_id", "Project Gate export must be the final stage."))
    for index, stage in enumerate(stages):
        if not isinstance(stage, dict):
            continue
        outputs = stage.get("required_outputs")
        if stage.get("mandatory") is True and not outputs:
            diagnostics.append(Diagnostic("CE_PIPELINE_MANDATORY_OUTPUT_REQUIRED", f"project_execution_stages[{index}].required_outputs", "Mandatory stages require explicit outputs."))
    return diagnostics


def validate_ce_stage_payload(repo_root: Path, payload: dict[str, Any]) -> list[Diagnostic]:
    schema = load_json(repo_root / "schemas/ce_stage_payload.v1.schema.json")
    diagnostics = _schema_errors(schema, payload, "ce_stage_payload")
    review = payload.get("constructability_review") if isinstance(payload.get("constructability_review"), dict) else {}
    emitted = payload.get("builder_package_emitted") is True
    status = review.get("constructability_status")
    if status in {"blocked", "needs_user_evidence", "needs_architect_amendment"} and emitted:
        diagnostics.append(Diagnostic("CE_PAYLOAD_BLOCKED_BUILDER_PACKAGE", "builder_package_emitted", "Blocked CE outcomes must not emit Builder packages."))
    identity = payload.get("architecture_identity") if isinstance(payload.get("architecture_identity"), dict) else {}
    if identity.get("selected_candidate_id_unchanged") is not True:
        diagnostics.append(Diagnostic("CE_PAYLOAD_SELECTED_CANDIDATE_CHANGED", "architecture_identity.selected_candidate_id_unchanged", "selected_candidate_id must remain unchanged."))
    if identity.get("build_tree_identity_preserved") is not True:
        diagnostics.append(Diagnostic("CE_PAYLOAD_BUILD_TREE_NOT_PRESERVED", "architecture_identity.build_tree_identity_preserved", "Build Tree identity must remain preserved."))
    return diagnostics


def validate_stage_bundle(bundle: dict[str, Any]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if bundle.get("schema_version") != "stage-evidence-bundle.v1":
        diagnostics.append(Diagnostic("CE_STAGE_BUNDLE_SCHEMA_VERSION_INVALID", "final_stage_bundle.schema_version", "Stage Bundle v1 must be reused."))
    if bundle.get("stage") != "ce":
        diagnostics.append(Diagnostic("CE_STAGE_BUNDLE_WRONG_STAGE", "final_stage_bundle.stage", "Stage Bundle stage must be ce."))
    payload_schema = bundle.get("payload_schema") if isinstance(bundle.get("payload_schema"), dict) else {}
    if payload_schema.get("id") != "ev4-ce-stage-payload@1.0.0":
        diagnostics.append(Diagnostic("CE_STAGE_BUNDLE_PAYLOAD_SCHEMA_INVALID", "final_stage_bundle.payload_schema.id", "Final Stage Bundle must carry CE Stage Payload v1."))
    produced_by = bundle.get("produced_by") if isinstance(bundle.get("produced_by"), dict) else {}
    if produced_by.get("repository") != CE_REPOSITORY:
        diagnostics.append(Diagnostic("CE_STAGE_BUNDLE_PRODUCER_INVALID", "final_stage_bundle.produced_by.repository", "Stage Bundle producer must be CE."))
    if bundle.get("synthetic") is not True and produced_by.get("commit_sha") is None:
        diagnostics.append(Diagnostic("CE_STAGE_BUNDLE_COMMIT_REQUIRED", "final_stage_bundle.produced_by.commit_sha", "Non-synthetic bundles require producer commit evidence."))
    payload = bundle.get("payload") if isinstance(bundle.get("payload"), dict) else {}
    if payload.get("schema_id") != "ev4-ce-stage-payload@1.0.0":
        diagnostics.append(Diagnostic("CE_STAGE_BUNDLE_PAYLOAD_ID_INVALID", "final_stage_bundle.payload.schema_id", "Stage payload schema_id must be CE Stage Payload v1."))
    return diagnostics


def validate_producer_gate_export(repo_root: Path, export: dict[str, Any]) -> list[Diagnostic]:
    schema = load_json(repo_root / "contracts/project-gate/producer-gate-export.v1.schema.json")
    diagnostics = _schema_errors(schema, export, "producer_gate_export")
    diagnostics.extend(validate_project_gate_lock(repo_root))
    diagnostics.extend(validate_pipeline_manifest(repo_root))

    producer = export.get("producer") if isinstance(export.get("producer"), dict) else {}
    if producer.get("stage") != "ce" or producer.get("repository") != CE_REPOSITORY:
        diagnostics.append(Diagnostic("CE_PG_EXPORT_PRODUCER_INVALID", "producer", "Producer identity must be CE."))
    acquisition = export.get("acquisition_mode") if isinstance(export.get("acquisition_mode"), dict) else {}
    if acquisition.get("silent_fallback_allowed") is not False:
        diagnostics.append(Diagnostic("CE_PG_SILENT_FALLBACK_FORBIDDEN", "acquisition_mode.silent_fallback_allowed", "Silent fallback is forbidden."))
    if acquisition.get("mode") != "producer_emitted_gate_artifact":
        diagnostics.append(Diagnostic("CE_PG_ACQUISITION_MODE_INVALID", "acquisition_mode.mode", "Producer-emitted gate artifact mode is mandatory."))

    stage_manifest = export.get("stage_manifest") if isinstance(export.get("stage_manifest"), list) else []
    if not stage_manifest or stage_manifest[-1].get("stage_id") != "project_gate_export":
        diagnostics.append(Diagnostic("CE_PG_EXPORT_STAGE_NOT_FINAL", "stage_manifest", "Project Gate export stage must be final."))
    for index, stage in enumerate(stage_manifest):
        if isinstance(stage, dict) and stage.get("status") == "complete":
            output = stage.get("output") if isinstance(stage.get("output"), dict) else {}
            if output.get("present") is not True or not output.get("artifact_ref"):
                diagnostics.append(Diagnostic("CE_PG_COMPLETE_STAGE_OUTPUT_REQUIRED", f"stage_manifest[{index}].output", "Complete stages require a real output reference."))

    handoff = export.get("handoff") if isinstance(export.get("handoff"), dict) else {}
    if handoff.get("allowed") is True:
        if handoff.get("status") not in {"successful", "successful_with_flags"}:
            diagnostics.append(Diagnostic("CE_PG_HANDOFF_ALLOWED_STATUS_INVALID", "handoff.status", "Allowed handoff requires successful status."))
        if handoff.get("blocking_diagnostics"):
            diagnostics.append(Diagnostic("CE_PG_HANDOFF_ALLOWED_WITH_BLOCKERS", "handoff.blocking_diagnostics", "Allowed handoff requires zero blocking diagnostics."))
    else:
        if not handoff.get("failure_reasons"):
            diagnostics.append(Diagnostic("CE_PG_HANDOFF_FAILURE_REASON_REQUIRED", "handoff.failure_reasons", "Disallowed handoff requires structured failure reasons."))

    bundle = export.get("final_stage_bundle") if isinstance(export.get("final_stage_bundle"), dict) else {}
    diagnostics.extend(validate_stage_bundle(bundle))
    payload_data = ((bundle.get("payload") or {}).get("data") if isinstance(bundle.get("payload"), dict) else None)
    if isinstance(payload_data, dict):
        diagnostics.extend(validate_ce_stage_payload(repo_root, payload_data))
    else:
        diagnostics.append(Diagnostic("CE_PG_PAYLOAD_DATA_MISSING", "final_stage_bundle.payload.data", "Final Stage Bundle must include CE payload data."))

    return sorted(diagnostics, key=lambda item: (item.code, item.path, item.message))


def validate_repository(repo_root: Path) -> dict[str, Any]:
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(validate_project_gate_lock(repo_root))
    diagnostics.extend(validate_pipeline_manifest(repo_root))
    for fixture in sorted((repo_root / "fixtures/project_gate_export").glob("*.json")):
        data = load_json(fixture)
        expected = data.get("expected") if isinstance(data.get("expected"), dict) else {}
        document = data.get("document") if isinstance(data.get("document"), dict) else data
        if "producer" in document and "final_stage_bundle" in document:
            fixture_diagnostics = validate_producer_gate_export(repo_root, document)
        elif document.get("schema_id") == "ev4-ce-stage-payload@1.0.0":
            fixture_diagnostics = validate_ce_stage_payload(repo_root, document)
        else:
            fixture_diagnostics = []
        expected_pass = expected.get("validation_pass")
        passed = not fixture_diagnostics
        if expected_pass is not None and passed is not bool(expected_pass):
            diagnostics.append(Diagnostic("CE_PG_FIXTURE_EXPECTATION_MISMATCH", str(fixture), f"Fixture expected validation_pass={expected_pass}, got {passed}."))
        expected_rules = set(expected.get("rules_violated") or [])
        actual_rules = {item.code for item in fixture_diagnostics}
        missing = sorted(expected_rules - actual_rules)
        for code in missing:
            diagnostics.append(Diagnostic("CE_PG_EXPECTED_RULE_MISSING", str(fixture), f"Expected diagnostic was not emitted: {code}."))
    return {
        "passed": not diagnostics,
        "diagnostics": [item.as_dict() for item in diagnostics],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate CE Project Gate producer adoption artifacts.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = validate_repository(Path(args.repo_root))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
    else:
        print("PASS" if result["passed"] else "FAIL-CLOSED")
        for diagnostic in result["diagnostics"]:
            print(f"- {diagnostic['code']} {diagnostic['path']}: {diagnostic['message']}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
