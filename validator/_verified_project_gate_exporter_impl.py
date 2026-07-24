from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .ce_validation_transaction import (
    JsonSnapshot,
    assert_snapshot_unchanged,
    capture_json_snapshot,
    safe_output_path,
)
from .engine import validate_document
from .project_gate_export import (
    CE_REPOSITORY,
    PIPELINE_ID,
    _producer_export_schema_for_local_validation,
    canonical_bytes,
    load_json,
    validate_pipeline_manifest,
    validate_project_gate_lock,
)
from .project_gate_exporter_build import _handoff_diagnostics, _stage_manifest
from .project_gate_exporter_core import (
    BUILDER_PACKAGE_SCHEMA_ID,
    EXPORTER_ID,
    EXPORTER_VERSION,
    HANDOFF_TARGET,
    PRODUCER_EXPORT_SCHEMA_ID,
    STAGE_BUNDLE_SCHEMA_ID,
    ZERO_SHA256,
    ExportDiagnostic,
    ExportResult,
    ExporterError,
    GitProvenance,
    _artifact_ref,
    _hash_record,
    _json_hash,
    inspect_git_provenance,
    validate_builder_package,
    validate_identity_preservation,
    verify_source_intake_binding,
)
from .project_gate_exporter_orchestration import (
    _atomic_write,
    _private_validation_snapshots,
    run_official_intake_validation,
)
from .project_gate_exporter_validation import (
    _export_identity_hash,
    validate_stage_bundle_schema,
    verify_export_identity,
)
from .project_gate_synthetic import derive_stage_bundle_synthetic
from .verified_constructability import (
    CLAIM_POLICIES,
    RESOLVER_ID,
    RESOLVER_VERSION,
    VERIFIED_PAYLOAD_SCHEMA_ID,
    VERIFIED_PAYLOAD_SCHEMA_VERSION,
    CapabilityError,
    DraftValidationError,
    EvidenceVerificationError,
    VerifiedCEStagePayload,
    assemble_verified_ce_stage_payload,
    verified_payload_data,
    verify_architect_intake,
    verify_source_bundle,
)

VERIFIED_EXPORTER_ID = "ev4-ce-verified-project-gate-exporter"
VERIFIED_EXPORTER_VERSION = "1.1.0"


def _schema_path(error: Any) -> str:
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}"
        for part in error.absolute_path
    )


def _validate_verified_payload_schema(
    repo_root: Path,
    payload: dict[str, Any],
) -> list[ExportDiagnostic]:
    payload_schema = load_json(repo_root / "schemas/ce_stage_payload.v1_1.schema.json")
    review_schema = load_json(repo_root / "schemas/constructability_review.v1_1.schema.json")
    alias = "https://ev4.local/schemas/ce/constructability_review.v1_1.schema.json"
    registry = Registry().with_resource(alias, Resource.from_contents(review_schema))
    diagnostics: list[ExportDiagnostic] = []
    for error in sorted(
        Draft202012Validator(payload_schema, registry=registry).iter_errors(payload),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    ):
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_PAYLOAD_SCHEMA_INVALID",
                "verified_payload_validation",
                error.message,
                _schema_path(error),
            )
        )
    return diagnostics


def _normalized(value: Any) -> Any:
    return json.loads(canonical_bytes(value))


def _resolution_map(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for item in payload.get("authority_resolution") or []:
        if not isinstance(item, dict):
            continue
        subject_ref = item.get("subject_ref")
        claim_id = item.get("claim_id")
        if isinstance(subject_ref, str) and isinstance(claim_id, str):
            result[(subject_ref, claim_id)] = item
    return result


def _derived_claim_value(
    interrogation: dict[str, Any],
    claim_id: str,
) -> bool | str | None:
    field_map: dict[str, str] = {
        "geometry": "geometry_proven",
        "overlay_strategy": "overlay_strategy_proven",
        "responsive_behavior": "responsive_behavior",
        "ui_control_path": "ui_control_evidence_present",
        "accessibility": "accessibility_evidenced",
        "dynamic_loop_approval": "dynamic_loop_approved",
        "interaction_approval": "interaction_approved",
        "asset_source": "asset_source_present",
        "placeholder_policy": "placeholder_policy_present",
    }
    field = field_map.get(claim_id)
    return interrogation.get(field) if field else None


def _expected_derived_value(claim_id: str, state: str) -> bool | str:
    if claim_id == "responsive_behavior":
        return "evidence_backed" if state == "VERIFIED" else "blocked"
    return state in {"VERIFIED", "ATTRIBUTED_SUPPORTED"}


def validate_verified_payload_authority(
    repo_root: Path,
    payload: dict[str, Any],
) -> list[ExportDiagnostic]:
    diagnostics = _validate_verified_payload_schema(repo_root, payload)
    if diagnostics:
        return diagnostics
    if payload.get("schema_id") != VERIFIED_PAYLOAD_SCHEMA_ID:
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_PAYLOAD_SCHEMA_ID_REQUIRED",
                "verified_payload_validation",
                "Builder authorization requires the verified successor Payload Schema.",
                "$.schema_id",
            )
        )
        return diagnostics

    contract = payload.get("validation_contract")
    if not isinstance(contract, dict) or contract != {
        "validator_id": RESOLVER_ID,
        "validator_version": RESOLVER_VERSION,
        "legacy_payload_validation_supported": True,
        "legacy_payload_authorization_supported": False,
        "successor_verified_payload_required_for_handoff": True,
    }:
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_RESOLVER_CONTRACT_INVALID",
                "verified_payload_validation",
                "Verified Payload resolver identity or legacy authorization boundary is invalid.",
                "$.validation_contract",
            )
        )

    resolution = payload.get("authority_resolution")
    if not isinstance(resolution, list):
        resolution = []
    expected_digest = hashlib.sha256(canonical_bytes(resolution)).hexdigest()
    if payload.get("authority_resolution_digest") != expected_digest:
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_RESOLUTION_DIGEST_MISMATCH",
                "verified_payload_validation",
                "Authority resolution digest does not match canonical resolution bytes.",
                "$.authority_resolution_digest",
            )
        )

    payload_id = (
        payload.get("payload_identity", {}).get("payload_id")
        if isinstance(payload.get("payload_identity"), dict)
        else None
    )
    allowed_producers = {
        "CE_VERIFIED_ADAPTER",
        "CE_TOOL_EXECUTION_ADAPTER",
        "CE_ATTRIBUTION_ADAPTER",
        "CE_OBLIGATION_ADAPTER",
    }
    evidence_register = payload.get("evidence_register")
    if not isinstance(evidence_register, list):
        evidence_register = []
    for index, evidence in enumerate(evidence_register):
        path = f"$.evidence_register[{index}]"
        if not isinstance(evidence, dict):
            diagnostics.append(
                ExportDiagnostic(
                    "CE_VERIFIED_EVIDENCE_RECORD_INVALID",
                    "verified_payload_validation",
                    "Runtime Evidence Register entries must be structured records.",
                    path,
                )
            )
            continue
        producer = evidence.get("producer")
        binding = evidence.get("target_binding")
        verification = evidence.get("verification")
        assurance = evidence.get("assurance_kind")
        if not isinstance(producer, dict) or producer.get("kind") not in allowed_producers:
            diagnostics.append(
                ExportDiagnostic(
                    "CE_VERIFIED_EVIDENCE_PRODUCER_INVALID",
                    "verified_payload_validation",
                    "Evidence was not produced by an official CE adapter.",
                    f"{path}.producer",
                )
            )
        if not isinstance(binding, dict) or binding.get("payload_id") != payload_id:
            diagnostics.append(
                ExportDiagnostic(
                    "CE_VERIFIED_EVIDENCE_PAYLOAD_BINDING_INVALID",
                    "verified_payload_validation",
                    "Evidence is not bound to this exact verified Payload.",
                    f"{path}.target_binding",
                )
            )
        status = verification.get("status") if isinstance(verification, dict) else None
        expected_status = {
            "VERIFIED_ARTIFACT": "VERIFIED",
            "VERIFIED_TOOL_EXECUTION": "VERIFIED",
            "VERIFIED_ARCHITECT_DECISION": "VERIFIED",
            "ATTRIBUTED_ENGINEERING_JUDGMENT": "ATTRIBUTED",
            "DOWNSTREAM_TEST_OBLIGATION": "UNPROVEN",
        }.get(str(assurance))
        if status != expected_status:
            diagnostics.append(
                ExportDiagnostic(
                    "CE_VERIFIED_EVIDENCE_ASSURANCE_STATUS_INVALID",
                    "verified_payload_validation",
                    "Evidence assurance kind and verification state are incompatible.",
                    f"{path}.verification.status",
                )
            )
        source = evidence.get("source")
        if assurance in {
            "VERIFIED_ARTIFACT",
            "VERIFIED_TOOL_EXECUTION",
            "VERIFIED_ARCHITECT_DECISION",
        }:
            digest = source.get("bytes_sha256") if isinstance(source, dict) else None
            if not isinstance(digest, str) or len(digest) != 64:
                diagnostics.append(
                    ExportDiagnostic(
                        "CE_VERIFIED_EVIDENCE_SOURCE_DIGEST_REQUIRED",
                        "verified_payload_validation",
                        "Verified evidence requires the digest of its authoritative source or result.",
                        f"{path}.source.bytes_sha256",
                    )
                )

    resolution_by_key = _resolution_map(payload)
    for index, item in enumerate(resolution):
        path = f"$.authority_resolution[{index}]"
        if not isinstance(item, dict):
            diagnostics.append(
                ExportDiagnostic(
                    "CE_VERIFIED_RESOLUTION_RECORD_INVALID",
                    "verified_payload_validation",
                    "Claim resolution entries must be structured records.",
                    path,
                )
            )
            continue
        claim_id = item.get("claim_id")
        state = item.get("resolved_state")
        policy = CLAIM_POLICIES.get(str(claim_id))
        if policy is None:
            diagnostics.append(
                ExportDiagnostic(
                    "CE_VERIFIED_CLAIM_POLICY_UNKNOWN",
                    "verified_payload_validation",
                    f"Unknown claim policy: {claim_id!r}.",
                    f"{path}.claim_id",
                )
            )
            continue
        if _normalized(item.get("policy")) != _normalized(policy):
            diagnostics.append(
                ExportDiagnostic(
                    "CE_VERIFIED_CLAIM_POLICY_DRIFT",
                    "verified_payload_validation",
                    "Carried claim policy differs from the canonical CE registry.",
                    f"{path}.policy",
                )
            )
        evidence_ids = item.get("verified_evidence")
        if state in {"VERIFIED", "ATTRIBUTED_SUPPORTED"} and (
            not isinstance(evidence_ids, list) or not evidence_ids
        ):
            diagnostics.append(
                ExportDiagnostic(
                    "CE_VERIFIED_RESOLVED_CLAIM_EVIDENCE_REQUIRED",
                    "verified_payload_validation",
                    "Authority-bearing claim state requires verifier-created evidence.",
                    f"{path}.verified_evidence",
                )
            )
        if state not in {"VERIFIED", "ATTRIBUTED_SUPPORTED"} and evidence_ids:
            diagnostics.append(
                ExportDiagnostic(
                    "CE_VERIFIED_UNRESOLVED_CLAIM_CARRIES_AUTHORITY",
                    "verified_payload_validation",
                    "Unresolved claim cannot carry authority-bearing evidence IDs.",
                    f"{path}.verified_evidence",
                )
            )

    review = payload.get("constructability_review")
    nodes = review.get("reviewed_nodes") if isinstance(review, dict) else []
    if not isinstance(nodes, list):
        nodes = []
    for node_index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        node_id = node.get("node_id")
        interrogation = node.get("interrogation_result")
        if not isinstance(node_id, str) or not isinstance(interrogation, dict):
            continue
        for (subject_ref, claim_id), item in resolution_by_key.items():
            if subject_ref != node_id:
                continue
            observed = _derived_claim_value(interrogation, claim_id)
            expected = _expected_derived_value(claim_id, str(item.get("resolved_state")))
            if observed != expected:
                diagnostics.append(
                    ExportDiagnostic(
                        "CE_VERIFIED_DERIVED_CLAIM_STATE_MISMATCH",
                        "verified_payload_validation",
                        f"Derived {claim_id} output does not match resolved evidence state.",
                        f"$.constructability_review.reviewed_nodes[{node_index}].interrogation_result",
                    )
                )

    unresolved = payload.get("unresolved_evidence")
    if not isinstance(unresolved, list):
        unresolved = []
    authority_ready = all(
        isinstance(item, dict)
        and item.get("resolved_state") in {"VERIFIED", "ATTRIBUTED_SUPPORTED"}
        and bool(CLAIM_POLICIES[str(item.get("claim_id"))]["may_authorize_builder_handoff"])
        for item in resolution
        if isinstance(item, dict) and str(item.get("claim_id")) in CLAIM_POLICIES
    )
    builder_emitted = payload.get("builder_package_emitted") is True
    status = review.get("constructability_status") if isinstance(review, dict) else None
    expected_emitted = authority_ready and not unresolved and status == "executable_ready"
    expected_emitted = expected_emitted and isinstance(payload.get("implementation_strategy_map"), dict)
    if builder_emitted != expected_emitted:
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_BUILDER_ELIGIBILITY_DERIVATION_MISMATCH",
                "verified_payload_validation",
                "Builder package emission does not equal runtime-derived eligibility.",
                "$.builder_package_emitted",
            )
        )
    if builder_emitted and payload.get("payload_status") != "complete":
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_PAYLOAD_STATUS_DERIVATION_MISMATCH",
                "verified_payload_validation",
                "Authorized Builder handoff requires derived payload_status=complete.",
                "$.payload_status",
            )
        )
    return diagnostics


def _stage_evidence_item(
    evidence: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    assurance = evidence.get("assurance_kind")
    source = evidence.get("source") if isinstance(evidence.get("source"), dict) else {}
    kind = {
        "VERIFIED_ARTIFACT": "document",
        "VERIFIED_TOOL_EXECUTION": "validator",
        "VERIFIED_ARCHITECT_DECISION": "document",
        "ATTRIBUTED_ENGINEERING_JUDGMENT": "report",
        "DOWNSTREAM_TEST_OBLIGATION": "report",
    }.get(str(assurance), "other")
    state = {
        "VERIFIED_ARTIFACT": "validated",
        "VERIFIED_TOOL_EXECUTION": "validated",
        "VERIFIED_ARCHITECT_DECISION": "validated",
        "ATTRIBUTED_ENGINEERING_JUDGMENT": "observed",
        "DOWNSTREAM_TEST_OBLIGATION": "insufficient_evidence",
    }.get(str(assurance), "unverified")
    source_type = {
        "repo_path": "repo_path",
        "tool_execution": "workflow",
        "architect_intake": "repo_path",
        "attributed_judgment": "manual_observation",
        "downstream_obligation": "manual_observation",
    }.get(str(source.get("type")), "manual_observation")
    return {
        "id": str(evidence.get("evidence_id") or f"ce-runtime-evidence-{index + 1}"),
        "kind": kind,
        "state": state,
        "description": (
            f"{assurance} integrity carrier; claim authority remains in the "
            "CE-owned verified Payload evidence record."
        ),
        "artifact_hash": _hash_record(_json_hash(evidence)),
        "source": {
            "type": source_type,
            "reference": str(source.get("reference") or evidence.get("subject_ref") or "unknown"),
        },
    }


def _missing_evidence(payload: dict[str, Any]) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for index, item in enumerate(payload.get("unresolved_evidence") or []):
        if not isinstance(item, dict):
            continue
        missing.append(
            {
                "id": str(item.get("unresolved_id") or f"ce-unresolved-{index + 1}"),
                "owner": str(item.get("owner") or "claim_policy_owner"),
                "reason": str(item.get("reason") or "Verified claim evidence remains unresolved."),
            }
        )
    return missing


def _build_verified_stage_bundle(
    *,
    payload: dict[str, Any],
    intake: dict[str, Any],
    source_bundle: dict[str, Any],
    provenance: GitProvenance,
    source_intake_path: Path,
    source_intake_hash: dict[str, str],
) -> tuple[dict[str, Any], str]:
    synthetic = any(
        value.get("synthetic") is True
        for value in (payload, intake, source_bundle)
        if isinstance(value, dict)
    )
    evidence: list[dict[str, Any]] = [
        {
            "id": f"ce-verified-payload:{payload['payload_identity']['payload_id']}",
            "kind": "document",
            "state": "validated",
            "description": "Verifier-created CE Stage Payload capability projected to canonical JSON.",
            "artifact_hash": _hash_record(_json_hash(payload)),
            "source": {
                "type": "manual_observation",
                "reference": f"verified-capability:{payload['payload_identity']['payload_id']}",
            },
        },
        {
            "id": f"ce-source-intake:{intake.get('project_gate_transition', {}).get('source_bundle_id', 'unknown')}",
            "kind": "document",
            "state": "validated",
            "description": "Accepted Architect intake verified against exact snapshot bytes and source bundle.",
            "artifact_hash": source_intake_hash,
            "source": {
                "type": "repo_path",
                "reference": _artifact_ref(source_intake_path, source_intake_path.parent),
            },
        },
    ]
    for index, item in enumerate(payload.get("evidence_register") or []):
        if isinstance(item, dict):
            evidence.append(_stage_evidence_item(item, index))
    missing = _missing_evidence(payload)
    bundle: dict[str, Any] = {
        "schema_version": STAGE_BUNDLE_SCHEMA_ID,
        "bundle_id": "",
        "stage": "ce",
        "payload_schema": {
            "id": VERIFIED_PAYLOAD_SCHEMA_ID,
            "version": VERIFIED_PAYLOAD_SCHEMA_VERSION,
            "owner_repository": CE_REPOSITORY,
        },
        "produced_by": {
            "repository": provenance.repository,
            "ref": provenance.ref,
            "commit_sha": provenance.commit_sha,
        },
        "evidence_status": "insufficient_evidence" if missing else "complete",
        "payload": {"schema_id": VERIFIED_PAYLOAD_SCHEMA_ID, "data": payload},
        "evidence": evidence,
        "provenance": {
            "source": "verified_ce_stage_payload_capability",
            "created_by": f"{VERIFIED_EXPORTER_ID}@{VERIFIED_EXPORTER_VERSION}",
        },
        "synthetic": synthetic,
    }
    if missing:
        bundle["missing_evidence"] = missing
    seed_hash = _json_hash(bundle)
    bundle["bundle_id"] = f"ce-stage-bundle-{seed_hash}"
    return bundle, _json_hash(bundle)


def _outer_schema_diagnostics(
    repo_root: Path,
    export: dict[str, Any],
) -> list[ExportDiagnostic]:
    schema = _producer_export_schema_for_local_validation(
        load_json(repo_root / "contracts/project-gate/producer-gate-export.v1.schema.json")
    )
    diagnostics: list[ExportDiagnostic] = []
    for error in sorted(
        Draft202012Validator(schema).iter_errors(export),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    ):
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_EXPORT_SCHEMA_INVALID",
                "producer_export_validation",
                error.message,
                _schema_path(error),
            )
        )
    for item in validate_project_gate_lock(repo_root) + validate_pipeline_manifest(repo_root):
        diagnostics.append(
            ExportDiagnostic(item.code, "producer_export_validation", item.message, item.path)
        )
    producer = export.get("producer") if isinstance(export.get("producer"), dict) else {}
    if producer.get("stage") != "ce" or producer.get("repository") != CE_REPOSITORY:
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_EXPORT_PRODUCER_INVALID",
                "producer_export_validation",
                "Producer identity must remain CE.",
                "$.producer",
            )
        )
    acquisition = export.get("acquisition_mode")
    if not isinstance(acquisition, dict) or acquisition != {
        "mode": "producer_emitted_gate_artifact",
        "silent_fallback_allowed": False,
    }:
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_EXPORT_ACQUISITION_INVALID",
                "producer_export_validation",
                "Verified exporter must use producer-emitted mode with no silent fallback.",
                "$.acquisition_mode",
            )
        )
    handoff = export.get("handoff") if isinstance(export.get("handoff"), dict) else {}
    if handoff.get("allowed") is True and (
        handoff.get("status") not in {"successful", "successful_with_flags"}
        or handoff.get("blocking_diagnostics")
        or handoff.get("failure_reasons")
    ):
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_EXPORT_HANDOFF_CONTRADICTION",
                "producer_export_validation",
                "Allowed handoff cannot contain failure or blocking surfaces.",
                "$.handoff",
            )
        )
    bundle = export.get("final_stage_bundle")
    if not isinstance(bundle, dict):
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_STAGE_BUNDLE_MISSING",
                "producer_export_validation",
                "Verified export requires a final CE Stage Bundle.",
                "$.final_stage_bundle",
            )
        )
        return diagnostics
    if bundle.get("payload_schema", {}).get("id") != VERIFIED_PAYLOAD_SCHEMA_ID:
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_STAGE_BUNDLE_PAYLOAD_SCHEMA_INVALID",
                "producer_export_validation",
                "Stage Bundle must carry the verified CE successor Payload identity.",
                "$.final_stage_bundle.payload_schema.id",
            )
        )
    if derive_stage_bundle_synthetic(bundle) and handoff.get("allowed") is True:
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_SYNTHETIC_EVIDENCE_BLOCKS_HANDOFF",
                "producer_export_validation",
                "Synthetic evidence cannot authorize Builder handoff.",
                "$.final_stage_bundle.synthetic",
            )
        )
    payload = bundle.get("payload", {}).get("data") if isinstance(bundle.get("payload"), dict) else None
    if isinstance(payload, dict):
        diagnostics.extend(validate_verified_payload_authority(repo_root, payload))
    else:
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_PAYLOAD_DATA_MISSING",
                "producer_export_validation",
                "Final Stage Bundle must carry verified CE Payload data.",
                "$.final_stage_bundle.payload.data",
            )
        )
    return diagnostics


def validate_verified_transaction_artifact(
    repo_root: Path,
    export: dict[str, Any],
) -> list[ExportDiagnostic]:
    diagnostics = _outer_schema_diagnostics(repo_root, export)
    handoff = export.get("handoff") if isinstance(export.get("handoff"), dict) else {}
    if handoff.get("allowed") is not True:
        return diagnostics
    bundle = export.get("final_stage_bundle") if isinstance(export.get("final_stage_bundle"), dict) else {}
    payload = bundle.get("payload", {}).get("data") if isinstance(bundle.get("payload"), dict) else {}
    if not isinstance(payload, dict):
        return diagnostics
    if payload.get("schema_id") != VERIFIED_PAYLOAD_SCHEMA_ID:
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_TRX_CAPABILITY_PAYLOAD_REQUIRED",
                "handoff_recomputation",
                "Allowed handoff requires the verified successor Payload.",
                "$.final_stage_bundle.payload.data.schema_id",
            )
        )
    if payload.get("payload_status") != "complete" or payload.get("unresolved_evidence"):
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_TRX_UNRESOLVED_AUTHORITY",
                "handoff_recomputation",
                "Allowed handoff requires complete, fully resolved CE authority state.",
                "$.final_stage_bundle.payload.data",
            )
        )
    review = payload.get("constructability_review")
    package = payload.get("builder_executable_package")
    if not isinstance(review, dict) or review.get("constructability_status") != "executable_ready":
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_TRX_CONSTRUCTABILITY_NOT_EXECUTABLE",
                "handoff_recomputation",
                "Allowed handoff requires derived constructability_status=executable_ready.",
                "$.final_stage_bundle.payload.data.constructability_review.constructability_status",
            )
        )
    if (
        payload.get("builder_package_emitted") is not True
        or not isinstance(package, dict)
        or package.get("schema") != BUILDER_PACKAGE_SCHEMA_ID
        or package.get("builder_package_status") != "executable_ready"
        or package.get("builder_decisions_required") != 0
        or package.get("blocking_dependencies") != []
    ):
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_TRX_BUILDER_PACKAGE_NOT_ELIGIBLE",
                "handoff_recomputation",
                "Allowed handoff requires the derived compatible Builder package.",
                "$.final_stage_bundle.payload.data.builder_executable_package",
            )
        )
    stages = export.get("stage_manifest") if isinstance(export.get("stage_manifest"), list) else []
    if any(
        not isinstance(stage, dict)
        or (stage.get("mandatory") is True and stage.get("status") != "complete")
        for stage in stages
    ):
        diagnostics.append(
            ExportDiagnostic(
                "CE_VERIFIED_TRX_MANDATORY_STAGE_INCOMPLETE",
                "handoff_recomputation",
                "All mandatory transaction stages must be complete.",
                "$.stage_manifest",
            )
        )
    return diagnostics


def secure_build_export(
    *,
    repo_root: Path,
    verified_payload: VerifiedCEStagePayload,
    source_intake_path: Path,
    source_bundle_path: Path,
    output_path: Path,
    provenance: GitProvenance,
) -> tuple[dict[str, Any], dict[str, Any], tuple[ExportDiagnostic, ...]]:
    if type(verified_payload) is not VerifiedCEStagePayload:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_VERIFIED_PAYLOAD_CAPABILITY_REQUIRED",
                "verified_payload_boundary",
                "Official export accepts only an exact verifier-created VerifiedCEStagePayload capability.",
                "$.verified_payload",
            )
        )
    intake_snapshot = capture_json_snapshot(
        source_intake_path,
        label="source Architect intake",
        read_error_code="CE_EXPORT_SOURCE_INTAKE_READ_FAILED",
        changed_error_code="CE_EXPORT_SOURCE_INTAKE_CHANGED_DURING_EXPORT",
    )
    bundle_snapshot = capture_json_snapshot(
        source_bundle_path,
        label="source Architect bundle",
        read_error_code="CE_EXPORT_SOURCE_BUNDLE_READ_FAILED",
        changed_error_code="CE_EXPORT_SOURCE_BUNDLE_CHANGED_DURING_EXPORT",
    )
    try:
        payload = verified_payload_data(
            verified_payload,
            repo_root=repo_root,
            source_intake_bytes=intake_snapshot.raw_bytes,
            source_bundle_bytes=bundle_snapshot.raw_bytes,
        )
    except (CapabilityError, OSError, RuntimeError) as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_VERIFIED_PAYLOAD_CAPABILITY_INVALID",
                "verified_payload_boundary",
                str(exc),
                "$.verified_payload",
            )
        ) from exc
    intake = intake_snapshot.value
    source_bundle = bundle_snapshot.value
    with _private_validation_snapshots(
        intake_snapshot.raw_bytes,
        bundle_snapshot.raw_bytes,
    ) as (validator_intake_path, validator_bundle_path):
        intake_report = run_official_intake_validation(
            repo_root,
            validator_intake_path,
            validator_bundle_path,
        )
    source_hash = verify_source_intake_binding(
        payload,
        intake,
        source_intake_path,
        intake_snapshot.raw_bytes,
    )
    authority_diagnostics = validate_verified_payload_authority(repo_root, payload)
    if authority_diagnostics:
        raise ExporterError(authority_diagnostics[0])
    semantic = validate_document(payload, repo_root=repo_root, mode="full")
    if not semantic.get("passed"):
        first = (semantic.get("schema_errors") or semantic.get("violations") or [None])[0]
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_VERIFIED_SEMANTIC_VALIDATION_FAILED",
                "ce_semantic_validation",
                str(first or "Verified CE semantic validation failed."),
                "$.verified_payload",
            )
        )
    validate_identity_preservation(payload, intake)
    builder_package_hash = validate_builder_package(payload)
    handoff_diagnostics = _handoff_diagnostics(
        payload,
        intake,
        source_bundle,
        provenance,
    )
    handoff_allowed = not handoff_diagnostics
    status = "successful" if handoff_allowed else "blocked"
    bundle, bundle_hash = _build_verified_stage_bundle(
        payload=payload,
        intake=intake,
        source_bundle=source_bundle,
        provenance=provenance,
        source_intake_path=source_intake_path,
        source_intake_hash=source_hash,
    )
    validate_stage_bundle_schema(repo_root, bundle)
    manifest = _stage_manifest(
        payload,
        source_intake_path,
        source_hash,
        output_path,
        repo_root,
    )
    if intake_report.get("status") != "valid":
        manifest[0]["status"] = "insufficient_evidence"
        manifest[0]["blockers"] = [{"code": "CE_EXPORT_INTAKE_INSUFFICIENT_EVIDENCE"}]
        manifest[0]["unknowns"] = list(intake.get("missing_evidence") or [])
        handoff_allowed = False
        status = "insufficient_evidence"
    export: dict[str, Any] = {
        "schema_version": PRODUCER_EXPORT_SCHEMA_ID,
        "export_id": "",
        "producer": {
            "stage": "ce",
            "repository": provenance.repository,
            "ref": provenance.ref,
            "commit_sha": provenance.commit_sha,
        },
        "pipeline_id": PIPELINE_ID,
        "run_id": payload["payload_identity"]["run_id"],
        "stage_manifest": manifest,
        "final_stage_bundle": bundle,
        "handoff": {
            "target": HANDOFF_TARGET,
            "status": status,
            "allowed": handoff_allowed,
            "failure_reasons": [item.as_dict() for item in handoff_diagnostics],
            "blocking_diagnostics": [item.as_dict() for item in handoff_diagnostics],
            "unresolved_evidence": list(payload.get("unresolved_evidence") or []),
        },
        "validation": {
            "schema_valid": True,
            "semantic_valid": True,
            "validator_id": VERIFIED_EXPORTER_ID,
            "validator_version": VERIFIED_EXPORTER_VERSION,
            "diagnostics": [],
        },
        "acquisition_mode": {
            "mode": "producer_emitted_gate_artifact",
            "silent_fallback_allowed": False,
        },
    }
    identity_hash = _export_identity_hash(export)
    export["export_id"] = f"ce-project-gate-export-{identity_hash}"
    export["stage_manifest"][-1]["output"]["artifact_hash"]["value"] = identity_hash
    diagnostics = _outer_schema_diagnostics(repo_root, export)
    diagnostics.extend(validate_verified_transaction_artifact(repo_root, export))
    if diagnostics:
        raise ExporterError(diagnostics[0])
    if not verify_export_identity(export):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_IDENTITY_SELF_CHECK_FAILED",
                "hash_self_verification",
                "Verified export identity hash self-check failed.",
            )
        )
    for snapshot in (intake_snapshot, bundle_snapshot):
        assert_snapshot_unchanged(snapshot)
    summary = {
        "export_id": export["export_id"],
        "source_intake_hash": source_hash["value"],
        "source_intake_hash_scope": source_hash["scope"],
        "source_bundle_hash": _json_hash(source_bundle),
        "ce_payload_hash": _json_hash(payload),
        "source_intake_snapshot_sha256": hashlib.sha256(intake_snapshot.raw_bytes).hexdigest(),
        "source_bundle_snapshot_sha256": hashlib.sha256(bundle_snapshot.raw_bytes).hexdigest(),
        "builder_executable_package_hash": builder_package_hash,
        "bundle_hash": bundle_hash,
        "export_identity_hash": identity_hash,
        "export_hash": _json_hash(export),
        "producer_commit": provenance.commit_sha,
        "producer_ref": provenance.ref,
        "repository_dirty": provenance.dirty,
        "dirty_paths": list(provenance.dirty_paths),
        "handoff_target": HANDOFF_TARGET,
        "intake_validation_status": intake_report["status"],
        "artifact_integrity_status": "valid",
        "semantic_validation_status": "valid",
        "authorization_valid": handoff_allowed,
        "verified_payload_schema": VERIFIED_PAYLOAD_SCHEMA_ID,
    }
    return export, summary, tuple(handoff_diagnostics)


def _read_prior_owned_output(path: Path) -> bytes | None:
    if not path.exists():
        return None
    try:
        value = load_json(path)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_OUTPUT_NOT_OWNED",
                "output_safety",
                f"Existing output is not a valid CE-owned artifact: {exc}",
                str(path),
                "repository_owner",
            )
        ) from exc
    producer = value.get("producer") if isinstance(value.get("producer"), dict) else {}
    if (
        value.get("schema_version") != PRODUCER_EXPORT_SCHEMA_ID
        or value.get("pipeline_id") != PIPELINE_ID
        or producer.get("repository") != CE_REPOSITORY
    ):
        raise ExporterError(
            ExportDiagnostic(
                "CE_EXPORT_OUTPUT_NOT_OWNED",
                "output_safety",
                "Refusing to replace an output not owned by the CE exporter.",
                str(path),
                "repository_owner",
            )
        )
    return path.read_bytes()


def _failure_result(
    output_path: Path,
    diagnostic: ExportDiagnostic,
) -> ExportResult:
    return ExportResult(
        status="invalid",
        output_path=str(output_path),
        output_written=False,
        handoff_allowed=False,
        diagnostics=(diagnostic,),
        summary={
            "output_valid": False,
            "artifact_must_not_be_consumed": True,
            "artifact_integrity_status": "invalid",
            "semantic_validation_status": "invalid_or_not_run",
            "authorization_valid": False,
        },
    )


def export_verified_review_file(
    *,
    repo_root: Path,
    review_draft_path: Path,
    source_intake_path: Path,
    source_bundle_path: Path,
    output_path: Path,
    overwrite: bool = False,
) -> ExportResult:
    safe_output: Path | None = None
    prior_output_bytes: bytes | None = None
    try:
        root = repo_root.resolve(strict=True)
        draft_snapshot = capture_json_snapshot(
            review_draft_path,
            label="CE Review Draft",
            read_error_code="CE_EXPORT_REVIEW_DRAFT_READ_FAILED",
            changed_error_code="CE_EXPORT_REVIEW_DRAFT_CHANGED_DURING_EXPORT",
        )
        intake_snapshot = capture_json_snapshot(
            source_intake_path,
            label="source Architect intake",
            read_error_code="CE_EXPORT_SOURCE_INTAKE_READ_FAILED",
            changed_error_code="CE_EXPORT_SOURCE_INTAKE_CHANGED_DURING_EXPORT",
        )
        bundle_snapshot = capture_json_snapshot(
            source_bundle_path,
            label="source Architect bundle",
            read_error_code="CE_EXPORT_SOURCE_BUNDLE_READ_FAILED",
            changed_error_code="CE_EXPORT_SOURCE_BUNDLE_CHANGED_DURING_EXPORT",
        )
        safe_output = safe_output_path(
            root,
            output_path,
            overwrite,
            protected_inputs=(
                review_draft_path,
                source_intake_path,
                source_bundle_path,
            ),
        )
        prior_output_bytes = _read_prior_owned_output(safe_output) if safe_output.exists() else None
        provenance = inspect_git_provenance(
            root,
            ignored_paths=(
                review_draft_path,
                source_intake_path,
                source_bundle_path,
                safe_output,
            ),
        )
        verified_intake = verify_architect_intake(
            intake=intake_snapshot.value,
            intake_bytes=intake_snapshot.raw_bytes,
            source_ref=str(source_intake_path),
        )
        verified_bundle = verify_source_bundle(
            source_bundle=bundle_snapshot.value,
            source_bundle_bytes=bundle_snapshot.raw_bytes,
            verified_intake=verified_intake,
            source_ref=str(source_bundle_path),
        )
        verified_payload = assemble_verified_ce_stage_payload(
            draft=draft_snapshot.value,
            verified_intake=verified_intake,
            verified_source_bundle=verified_bundle,
            repo_root=root,
        )
        export, summary, diagnostics = secure_build_export(
            repo_root=root,
            verified_payload=verified_payload,
            source_intake_path=source_intake_path,
            source_bundle_path=source_bundle_path,
            output_path=safe_output,
            provenance=provenance,
        )
        assert_snapshot_unchanged(draft_snapshot)
        data = canonical_bytes(export) + b"\n"
        _atomic_write(safe_output, data)
        try:
            reread_bytes = safe_output.read_bytes()
            if reread_bytes != data:
                raise ExporterError(
                    ExportDiagnostic(
                        "CE_EXPORT_POST_WRITE_BYTE_MISMATCH",
                        "post_write_validation",
                        "Re-read output bytes differ from validated publication bytes.",
                        str(safe_output),
                    )
                )
            reread = load_json(safe_output)
            validate_stage_bundle_schema(root, reread["final_stage_bundle"])
            post_diagnostics = validate_verified_transaction_artifact(root, reread)
            if post_diagnostics or not verify_export_identity(reread):
                raise ExporterError(
                    post_diagnostics[0]
                    if post_diagnostics
                    else ExportDiagnostic(
                        "CE_EXPORT_POST_WRITE_IDENTITY_INVALID",
                        "post_write_validation",
                        "Post-write export identity validation failed.",
                        str(safe_output),
                    )
                )
        except Exception:
            if prior_output_bytes is None:
                safe_output.unlink(missing_ok=True)
            else:
                _atomic_write(safe_output, prior_output_bytes)
            raise
        return ExportResult(
            status="successful" if export["handoff"]["allowed"] else export["handoff"]["status"],
            output_path=str(safe_output),
            output_written=True,
            handoff_allowed=bool(export["handoff"]["allowed"]),
            diagnostics=diagnostics,
            summary={
                **summary,
                "output_valid": True,
                "artifact_state": (
                    "valid_authorized_export"
                    if export["handoff"]["allowed"]
                    else "valid_blocked_export"
                ),
                "artifact_must_not_be_consumed": False,
            },
        )
    except ExporterError as exc:
        return _failure_result(safe_output or output_path, exc.diagnostic)
    except (CapabilityError, DraftValidationError, EvidenceVerificationError, OSError, ValueError, TypeError) as exc:
        return _failure_result(
            safe_output or output_path,
            ExportDiagnostic(
                "CE_EXPORT_VERIFIED_REVIEW_ASSEMBLY_FAILED",
                "verified_payload_assembly",
                str(exc),
                str(review_draft_path),
            ),
        )


def reject_legacy_payload_export(
    *,
    repo_root: Path,
    payload_path: Path,
    source_intake_path: Path,
    source_bundle_path: Path,
    output_path: Path,
    overwrite: bool = False,
) -> ExportResult:
    del repo_root, payload_path, source_intake_path, source_bundle_path, overwrite
    return _failure_result(
        output_path,
        ExportDiagnostic(
            "CE_EXPORT_LEGACY_PAYLOAD_AUTHORIZATION_FORBIDDEN",
            "legacy_preview_boundary",
            "Raw ev4-ce-stage-payload@1.0.0 artifacts may be validated or migrated, but cannot authorize Builder handoff.",
            "$.payload_path",
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Assemble a verified CE Review Draft and produce the official Project Gate export."
    )
    parser.add_argument("--review-draft", required=True, type=Path)
    parser.add_argument("--source-intake", required=True, type=Path)
    parser.add_argument("--source-bundle", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("ce-project-gate.json"))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    result = export_verified_review_file(
        repo_root=args.repo_root,
        review_draft_path=args.review_draft,
        source_intake_path=args.source_intake,
        source_bundle_path=args.source_bundle,
        output_path=args.output,
        overwrite=args.overwrite,
    )
    print(
        json.dumps(
            result.as_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )
    if result.status == "invalid":
        return 1
    return 0 if result.handoff_allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())
