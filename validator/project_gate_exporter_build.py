from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .project_gate_export import (
    CE_REPOSITORY,
    load_json,
)
from .project_gate_exporter_core import (
    EXPECTED_PROJECT_GATE_COMMIT,
    EXPECTED_STAGE_BUNDLE_SHA256,
    EXPORTER_ID,
    EXPORTER_VERSION,
    HANDOFF_TARGET,
    PRODUCER_EXPORT_SCHEMA_ID,
    STAGE_BUNDLE_SCHEMA_ID,
    ZERO_SHA256,
    ExportDiagnostic,
    ExporterError,
    GitProvenance,
    _artifact_ref,
    _hash_record,
    _json_hash,
    _relative_if_inside,
)


def _map_evidence_item(item: dict[str, Any], index: int, synthetic: bool) -> dict[str, Any]:
    allowed_kinds = {"document", "schema", "fixture", "validator", "screenshot", "report", "other"}
    raw_kind = str(item.get("kind") or "other")
    kind = raw_kind if raw_kind in allowed_kinds else "other"
    raw_state = str(item.get("state") or "unverified")
    allowed_states = {"observed", "exported", "validated", "resolved", "derived", "proposed", "unverified", "insufficient_evidence"}
    state = raw_state if raw_state in allowed_states else ("unverified" if synthetic else "observed")
    source = item.get("source") if isinstance(item.get("source"), dict) else {}
    reference = str(source.get("reference") or source.get("path") or f"ce_payload.evidence_register[{index}]")
    raw_type = str(source.get("type") or "")
    allowed_types = {"repo_path", "workflow", "manual_observation", "synthetic_fixture"}
    if raw_type in allowed_types:
        source_type = raw_type
    elif synthetic:
        source_type = "synthetic_fixture"
    elif reference.startswith(("fixtures/", "schemas/", "docs/", "contracts/", "validator/", "scripts/")):
        source_type = "repo_path"
    else:
        source_type = "manual_observation"
    return {
        "id": str(item.get("id") or f"ce-evidence-{index + 1}"),
        "kind": kind,
        "state": state,
        "description": str(item.get("description") or "CE evidence record."),
        "artifact_hash": _hash_record(_json_hash(item)),
        "source": {"type": source_type, "reference": reference},
    }


def _contains_synthetic_evidence(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("synthetic") is True:
            return True
        if value.get("classification") == "synthetic":
            return True
        if value.get("state") == "synthetic":
            return True
        if value.get("fact_class") == "synthetic_fixture":
            return True
        if value.get("source_type") == "synthetic_fixture":
            return True
        if value.get("type") == "synthetic_fixture":
            return True
        return any(_contains_synthetic_evidence(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_synthetic_evidence(child) for child in value)
    return False


def _missing_evidence(payload: dict[str, Any], intake: dict[str, Any]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for index, item in enumerate(payload.get("unresolved_evidence") or []):
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "id": str(item.get("unresolved_id") or item.get("id") or f"ce-unresolved-{index + 1}"),
                "owner": str(item.get("owner") or "unresolved"),
                "reason": str(item.get("reason") or "Required CE evidence is unresolved."),
            }
        )
    if not result:
        for index, item in enumerate(intake.get("missing_evidence") or []):
            if not isinstance(item, dict):
                continue
            result.append(
                {
                    "id": str(item.get("missing_id") or f"architect-missing-{index + 1}"),
                    "owner": str(item.get("current_evidence_owner") or "unresolved"),
                    "reason": str(item.get("required_source") or "Accepted intake evidence is incomplete."),
                }
            )
    return result


def _stage_status_for_review(review_status: str | None) -> str:
    if review_status in {"executable_ready", "executable_with_logged_assumption"}:
        return "complete"
    if review_status in {"needs_user_evidence", "needs_architect_amendment"}:
        return "insufficient_evidence"
    if review_status == "blocked":
        return "blocked"
    return "invalid"


def _output(ref: str, value: Any, *, present: bool = True, scope: str = "canonical_json") -> dict[str, Any]:
    if not present:
        return {"present": False}
    digest = _json_hash(value) if scope == "canonical_json" else str(value)
    return {"present": True, "artifact_ref": ref, "artifact_hash": _hash_record(digest, scope)}


def _stage_manifest(
    payload: dict[str, Any],
    source_intake_path: Path,
    source_intake_hash: dict[str, str],
    output_path: Path,
    repo_root: Path,
) -> list[dict[str, Any]]:
    payload_id = str(payload["payload_identity"]["payload_id"])
    review = payload.get("constructability_review") if isinstance(payload.get("constructability_review"), dict) else {}
    reviewed_nodes = review.get("reviewed_nodes") if isinstance(review.get("reviewed_nodes"), list) else []
    dependencies = review.get("blocking_dependencies") if isinstance(review.get("blocking_dependencies"), list) else []
    strategy = payload.get("implementation_strategy_map")
    emitted = payload.get("builder_package_emitted") is True
    unresolved = payload.get("unresolved_evidence") if isinstance(payload.get("unresolved_evidence"), list) else []
    review_stage_status = _stage_status_for_review(review.get("constructability_status"))
    missing_status = "insufficient_evidence" if unresolved or payload.get("payload_status") == "insufficient_evidence" else "blocked"

    return [
        {
            "stage_id": "architect_intake_validation",
            "stage_version": "1.0.0",
            "ordinal": 1,
            "mandatory": True,
            "status": "complete",
            "output": {
                "present": True,
                "artifact_ref": _artifact_ref(source_intake_path, repo_root),
                "artifact_hash": source_intake_hash,
            },
            "blockers": [],
            "unknowns": [],
        },
        {
            "stage_id": "identity_lock_validation",
            "stage_version": "1.0.0",
            "ordinal": 2,
            "mandatory": True,
            "status": "complete",
            "output": _output(f"ce-payload:{payload_id}#architecture_identity", payload["architecture_identity"]),
            "blockers": [],
            "unknowns": [],
        },
        {
            "stage_id": "node_action_interrogation",
            "stage_version": "1.0.0",
            "ordinal": 3,
            "mandatory": True,
            "status": "complete" if reviewed_nodes else "insufficient_evidence",
            "output": _output(f"ce-payload:{payload_id}#constructability_review.reviewed_nodes", reviewed_nodes),
            "blockers": [] if reviewed_nodes else [{"code": "CE_EXPORT_REVIEWED_NODES_MISSING"}],
            "unknowns": [] if reviewed_nodes else [{"code": "CE_EXPORT_REVIEWED_NODES_MISSING"}],
        },
        {
            "stage_id": "hidden_dependency_classification",
            "stage_version": "1.0.0",
            "ordinal": 4,
            "mandatory": True,
            "status": "complete",
            "output": _output(f"ce-payload:{payload_id}#constructability_review.blocking_dependencies", dependencies),
            "blockers": [],
            "unknowns": [],
        },
        {
            "stage_id": "constructability_review",
            "stage_version": "1.0.0",
            "ordinal": 5,
            "mandatory": True,
            "status": review_stage_status,
            "output": _output(f"ce-payload:{payload_id}#constructability_review", review),
            "blockers": [{"code": str(value)} for value in dependencies] if review_stage_status == "blocked" else [],
            "unknowns": list(unresolved) if review_stage_status == "insufficient_evidence" else [],
        },
        {
            "stage_id": "implementation_strategy_determination",
            "stage_version": "1.0.0",
            "ordinal": 6,
            "mandatory": True,
            "status": "complete" if isinstance(strategy, dict) else missing_status,
            "output": _output(f"ce-payload:{payload_id}#implementation_strategy_map", strategy if strategy is not None else {"absence_reason": payload.get("builder_package_not_emitted_reason")}),
            "blockers": [] if isinstance(strategy, dict) else [{"code": "CE_EXPORT_STRATEGY_NOT_AVAILABLE"}],
            "unknowns": list(unresolved) if not isinstance(strategy, dict) else [],
        },
        {
            "stage_id": "builder_package_gate",
            "stage_version": "1.0.0",
            "ordinal": 7,
            "mandatory": True,
            "status": "complete" if emitted else missing_status,
            "output": _output(
                f"ce-payload:{payload_id}#builder_executable_package",
                payload.get("builder_executable_package") if emitted else {"not_emitted_reason": payload.get("builder_package_not_emitted_reason")},
            ),
            "blockers": [] if emitted else [{"code": "CE_EXPORT_BUILDER_PACKAGE_NOT_EMITTED"}],
            "unknowns": list(unresolved) if not emitted else [],
        },
        {
            "stage_id": "project_gate_export",
            "stage_version": "1.0.0",
            "ordinal": 8,
            "mandatory": True,
            "status": "complete",
            "output": {
                "present": True,
                "artifact_ref": _artifact_ref(output_path, repo_root),
                "artifact_hash": _hash_record(ZERO_SHA256),
            },
            "blockers": [],
            "unknowns": [],
        },
    ]


def _handoff_diagnostics(
    payload: dict[str, Any],
    intake: dict[str, Any],
    source_bundle: dict[str, Any],
    provenance: GitProvenance,
) -> list[ExportDiagnostic]:
    diagnostics: list[ExportDiagnostic] = []
    review = payload.get("constructability_review") if isinstance(payload.get("constructability_review"), dict) else {}
    status = review.get("constructability_status")
    if intake.get("intake_status") == "insufficient_evidence":
        diagnostics.append(ExportDiagnostic("CE_EXPORT_INTAKE_INSUFFICIENT_EVIDENCE", "handoff_gate", "Accepted Architect intake remains insufficient_evidence.", "$.intake_status", "architect_or_project_gate"))
    if payload.get("payload_status") == "insufficient_evidence":
        diagnostics.append(ExportDiagnostic("CE_EXPORT_PAYLOAD_INSUFFICIENT_EVIDENCE", "handoff_gate", "CE Stage Payload remains insufficient_evidence.", "$.payload_status"))
    if payload.get("unresolved_evidence"):
        diagnostics.append(ExportDiagnostic("CE_EXPORT_UNRESOLVED_EVIDENCE", "handoff_gate", "CE Stage Payload contains unresolved evidence.", "$.unresolved_evidence"))
    if status not in {"executable_ready", "executable_with_logged_assumption"}:
        diagnostics.append(ExportDiagnostic("CE_EXPORT_CONSTRUCTABILITY_NOT_EXECUTABLE", "handoff_gate", f"Constructability status {status!r} is not eligible for Builder handoff.", "$.constructability_review.constructability_status"))
    if payload.get("builder_package_emitted") is not True:
        diagnostics.append(ExportDiagnostic("CE_EXPORT_BUILDER_PACKAGE_NOT_EMITTED", "handoff_gate", "CE did not emit an eligible Builder Executable Package.", "$.builder_package_emitted"))
    source_is_synthetic = (
        _contains_synthetic_evidence(payload)
        or _contains_synthetic_evidence(intake)
        or _contains_synthetic_evidence(source_bundle)
    )
    if source_is_synthetic:
        diagnostics.append(ExportDiagnostic("CE_EXPORT_SYNTHETIC_EVIDENCE_BLOCKED", "handoff_gate", "Synthetic evidence cannot authorize Builder handoff.", "$.final_stage_bundle.synthetic"))
    if provenance.dirty:
        diagnostics.append(ExportDiagnostic("CE_EXPORT_DIRTY_WORKTREE_BLOCKS_HANDOFF", "git_provenance", "Dirty repository state blocks an allowed handoff.", "$.producer.commit_sha", "repository_owner"))
    return diagnostics


def _build_stage_bundle(
    payload: dict[str, Any],
    intake: dict[str, Any],
    source_bundle: dict[str, Any],
    provenance: GitProvenance,
    payload_path: Path,
    source_intake_path: Path,
    repo_root: Path,
) -> tuple[dict[str, Any], str]:
    synthetic = (
        _contains_synthetic_evidence(payload)
        or _contains_synthetic_evidence(intake)
        or _contains_synthetic_evidence(source_bundle)
    )
    evidence = [
        {
            "id": f"ce-payload:{payload['payload_identity']['payload_id']}",
            "kind": "document",
            "state": "validated",
            "description": "Official CE Stage Payload validated for Producer Gate Export.",
            "artifact_hash": _hash_record(_json_hash(payload)),
            "source": {
                "type": "repo_path" if _relative_if_inside(payload_path, repo_root) else "manual_observation",
                "reference": _artifact_ref(payload_path, repo_root),
            },
        },
        {
            "id": f"ce-source-intake:{intake.get('source_repository_ref', {}).get('bundle_id', 'unknown')}",
            "kind": "document",
            "state": "validated",
            "description": "Accepted Architect-to-CE intake validated with source bundle binding.",
            "artifact_hash": _hash_record(_json_hash(intake)),
            "source": {
                "type": "repo_path" if _relative_if_inside(source_intake_path, repo_root) else "manual_observation",
                "reference": _artifact_ref(source_intake_path, repo_root),
            },
        },
    ]
    for index, item in enumerate(payload.get("evidence_register") or []):
        if isinstance(item, dict):
            evidence.append(_map_evidence_item(item, index, synthetic))
    missing = _missing_evidence(payload, intake)
    bundle: dict[str, Any] = {
        "schema_version": STAGE_BUNDLE_SCHEMA_ID,
        "bundle_id": "",
        "stage": "ce",
        "payload_schema": {
            "id": "ev4-ce-stage-payload@1.0.0",
            "version": "1.0.0",
            "owner_repository": CE_REPOSITORY,
        },
        "produced_by": {
            "repository": provenance.repository,
            "ref": provenance.ref,
            "commit_sha": provenance.commit_sha,
        },
        "evidence_status": "insufficient_evidence" if missing or payload.get("payload_status") == "insufficient_evidence" else "complete",
        "payload": {"schema_id": "ev4-ce-stage-payload@1.0.0", "data": payload},
        "evidence": evidence,
        "provenance": {
            "source": "operator_supplied_ce_stage_payload",
            "created_by": f"{EXPORTER_ID}@{EXPORTER_VERSION}",
        },
        "synthetic": synthetic,
    }
    if bundle["evidence_status"] == "insufficient_evidence":
        bundle["missing_evidence"] = missing or [{"id": "ce-missing-evidence", "owner": "unresolved", "reason": "CE payload is insufficient_evidence."}]
    seed_hash = _json_hash(bundle)
    bundle["bundle_id"] = f"ce-stage-bundle-{seed_hash}"
    return bundle, _json_hash(bundle)


def validate_stage_bundle_lock(repo_root: Path) -> None:
    lock_path = repo_root / "contracts/project-gate/stage-bundle.v1.lock.json"
    schema_path = repo_root / "contracts/project-gate/stage-bundle.v1.schema.json"
    lock = load_json(lock_path)
    observed_hash = hashlib.sha256(schema_path.read_bytes()).hexdigest()
    canonical = lock.get("canonical") if isinstance(lock.get("canonical"), dict) else {}
    vendored = lock.get("vendored") if isinstance(lock.get("vendored"), dict) else {}
    verification = lock.get("verification") if isinstance(lock.get("verification"), dict) else {}
    expected = {
        "lock_schema": "project-gate-common-contract-lock.v1",
        "contract_owner": "rezahh107/EV4-Project-Gate",
        "contract_id": STAGE_BUNDLE_SCHEMA_ID,
        "contract_version": "1.0.0",
    }
    invalid = any(lock.get(key) != value for key, value in expected.items())
    invalid = invalid or canonical != {
        "repository": "rezahh107/EV4-Project-Gate",
        "path": "schemas/stage-bundle/stage-bundle.v1.schema.json",
        "commit_sha": EXPECTED_PROJECT_GATE_COMMIT,
        "file_sha256": EXPECTED_STAGE_BUNDLE_SHA256,
    }
    invalid = invalid or vendored != {
        "repository": CE_REPOSITORY,
        "path": "contracts/project-gate/stage-bundle.v1.schema.json",
        "file_sha256": EXPECTED_STAGE_BUNDLE_SHA256,
        "local_copy_authoritative": False,
    }
    invalid = invalid or verification != {
        "byte_equality_required": True,
        "compare_against_moving_default_branch": False,
    }
    invalid = invalid or observed_hash != EXPECTED_STAGE_BUNDLE_SHA256
    if invalid:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_STAGE_BUNDLE_LOCK_INVALID",
                "stage_bundle_contract_lock",
                "Vendored Stage Evidence Bundle contract or immutable lock does not match the Project Gate pin.",
                str(lock_path),
                "repository_owner",
            )
        )


def validate_stage_bundle_schema(repo_root: Path, bundle: dict[str, Any]) -> None:
    validate_stage_bundle_lock(repo_root)
    schema = load_json(repo_root / "contracts/project-gate/stage-bundle.v1.schema.json")
    errors = sorted(Draft202012Validator(schema).iter_errors(bundle), key=lambda error: tuple(str(part) for part in error.absolute_path))
    if errors:
        error = errors[0]
        path = "$" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path)
        raise ExporterError(ExportDiagnostic("CE_EXPORT_STAGE_BUNDLE_SCHEMA_INVALID", "stage_bundle_validation", error.message, path))


def _export_identity_hash(export: dict[str, Any]) -> str:
    normalized = deepcopy(export)
    normalized["export_id"] = ""
    normalized["stage_manifest"][-1]["output"]["artifact_hash"]["value"] = ZERO_SHA256
    return _json_hash(normalized)


def verify_export_identity(export: dict[str, Any]) -> bool:
    identity_hash = _export_identity_hash(export)
    return (
        export.get("export_id") == f"ce-project-gate-export-{identity_hash}"
        and export.get("stage_manifest", [])[-1].get("output", {}).get("artifact_hash", {}).get("value") == identity_hash
    )

