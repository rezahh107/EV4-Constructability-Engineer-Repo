from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

import validator.ce_validation_transaction as transaction_module
import validator.verified_project_gate_exporter as verified_exporter
from exporter_test_support import ROOT, _payload, _real_source_pair, _write_json
from validator.authority_boundary import legacy_payload_authorization_is_closed
from validator.project_gate_export import canonical_bytes, load_json
from validator.verified_constructability import (
    CapabilityError,
    DraftValidationError,
    EvidenceVerificationError,
    VerifiedConstructabilityProof,
    assemble_verified_ce_stage_payload,
    capability_record,
    make_test_only_proof_capability,
    verified_payload_data,
    verify_architect_intake,
    verify_source_bundle,
)
from validator.verified_project_gate_exporter import (
    export_verified_review_file,
    validate_verified_transaction_artifact,
)
from verified_exporter_test_support import (
    _draft,
    _geometry_draft,
    _provenance,
    _write_verified_inputs,
)


@pytest.fixture(autouse=True)
def clean_verified_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        verified_exporter,
        "inspect_git_provenance",
        lambda repo_root, ignored_paths=(): _provenance(dirty=False),
    )


def _cleanup(path: Path) -> None:
    path.unlink(missing_ok=True)
    parent = path.parent
    if parent.name == ".tmp-test-output" and parent.exists() and not any(parent.iterdir()):
        parent.rmdir()


def _capability_inputs(tmp_path: Path, draft: dict):
    intake, source, intake_path, source_path = _real_source_pair(tmp_path)
    verified_intake = verify_architect_intake(
        intake=intake,
        intake_bytes=intake_path.read_bytes(),
        source_ref=str(intake_path),
    )
    verified_bundle = verify_source_bundle(
        source_bundle=source,
        source_bundle_bytes=source_path.read_bytes(),
        verified_intake=verified_intake,
        source_ref=str(source_path),
    )
    return intake, source, intake_path, source_path, verified_intake, verified_bundle


def test_official_runtime_accepts_only_verified_payload_capability() -> None:
    signature = inspect.signature(transaction_module.secure_build_export)
    assert "verified_payload" in signature.parameters
    assert "payload_path" not in signature.parameters
    assert legacy_payload_authorization_is_closed() is True


def test_valid_verified_review_produces_authorized_handoff(tmp_path: Path) -> None:
    _, _, intake_path, source_path, _, draft_path = _write_verified_inputs(tmp_path)
    output_path = ROOT / ".tmp-test-output" / "verified-authorized.json"
    _cleanup(output_path)
    try:
        result = export_verified_review_file(
            repo_root=ROOT,
            review_draft_path=draft_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
        )
        assert result.status == "successful", result.as_dict()
        assert result.output_written is True
        assert result.handoff_allowed is True
        export = load_json(output_path)
        payload = export["final_stage_bundle"]["payload"]["data"]
        assert payload["schema_id"] == "ev4-ce-stage-payload@1.1.0"
        assert payload["builder_package_emitted"] is True
        assert payload["constructability_review"]["constructability_status"] == "executable_ready"
        assert export["handoff"]["allowed"] is True
    finally:
        _cleanup(output_path)


def test_attributed_geometry_judgment_is_valid_without_becoming_tool_evidence(
    tmp_path: Path,
) -> None:
    _, _, intake_path, source_path, _, draft_path = _write_verified_inputs(
        tmp_path,
        geometry=True,
    )
    output_path = ROOT / ".tmp-test-output" / "verified-geometry.json"
    _cleanup(output_path)
    try:
        result = export_verified_review_file(
            repo_root=ROOT,
            review_draft_path=draft_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
        )
        assert result.status == "successful", result.as_dict()
        payload = load_json(output_path)["final_stage_bundle"]["payload"]["data"]
        interrogation = payload["constructability_review"]["reviewed_nodes"][0][
            "interrogation_result"
        ]
        assert interrogation["geometry_proven"] is True
        assert payload["authority_resolution"][0]["resolved_state"] == "ATTRIBUTED_SUPPORTED"
        evidence = payload["evidence_register"][0]
        assert evidence["assurance_kind"] == "ATTRIBUTED_ENGINEERING_JUDGMENT"
        assert evidence["verification"]["status"] == "ATTRIBUTED"
    finally:
        _cleanup(output_path)


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "geometry_proven",
        "overlay_strategy_proven",
        "constructability_status",
        "verification_status",
        "state",
        "source_sha256",
        "run_id",
    ],
)
def test_review_draft_rejects_caller_authored_authority_fields(
    tmp_path: Path,
    forbidden_key: str,
) -> None:
    intake, source, intake_path, source_path = _real_source_pair(tmp_path)
    draft = _draft(intake_path)
    draft["reviewed_nodes"][0][forbidden_key] = True
    verified_intake = verify_architect_intake(
        intake=intake,
        intake_bytes=intake_path.read_bytes(),
        source_ref=str(intake_path),
    )
    verified_bundle = verify_source_bundle(
        source_bundle=source,
        source_bundle_bytes=source_path.read_bytes(),
        verified_intake=verified_intake,
        source_ref=str(source_path),
    )
    with pytest.raises(DraftValidationError):
        assemble_verified_ce_stage_payload(
            draft=draft,
            verified_intake=verified_intake,
            verified_source_bundle=verified_bundle,
            repo_root=ROOT,
        )


def test_plain_dict_cannot_satisfy_verified_proof(tmp_path: Path) -> None:
    intake, source, intake_path, source_path = _real_source_pair(tmp_path)
    draft = _draft(intake_path)
    verified_intake = verify_architect_intake(
        intake=intake,
        intake_bytes=intake_path.read_bytes(),
        source_ref=str(intake_path),
    )
    verified_bundle = verify_source_bundle(
        source_bundle=source,
        source_bundle_bytes=source_path.read_bytes(),
        verified_intake=verified_intake,
        source_ref=str(source_path),
    )
    with pytest.raises(CapabilityError):
        assemble_verified_ce_stage_payload(
            draft=draft,
            verified_intake=verified_intake,
            verified_source_bundle=verified_bundle,
            repo_root=ROOT,
            proofs=[{"mode": "VERIFIED_ARTIFACT"}],
        )


def test_manually_constructed_lookalike_is_rejected(tmp_path: Path) -> None:
    _, _, intake_path, _, verified_intake, verified_bundle = _capability_inputs(
        tmp_path,
        _draft(Path("unused")),
    )
    draft = _draft(intake_path)
    forged = VerifiedConstructabilityProof()
    with pytest.raises(CapabilityError):
        assemble_verified_ce_stage_payload(
            draft=draft,
            verified_intake=verified_intake,
            verified_source_bundle=verified_bundle,
            repo_root=ROOT,
            proofs=[forged],
        )


def test_subclass_spoofing_is_rejected(tmp_path: Path) -> None:
    class SpoofedProof(VerifiedConstructabilityProof):
        pass

    intake, source, intake_path, source_path = _real_source_pair(tmp_path)
    verified_intake = verify_architect_intake(
        intake=intake,
        intake_bytes=intake_path.read_bytes(),
        source_ref=str(intake_path),
    )
    verified_bundle = verify_source_bundle(
        source_bundle=source,
        source_bundle_bytes=source_path.read_bytes(),
        verified_intake=verified_intake,
        source_ref=str(source_path),
    )
    with pytest.raises(CapabilityError):
        assemble_verified_ce_stage_payload(
            draft=_draft(intake_path),
            verified_intake=verified_intake,
            verified_source_bundle=verified_bundle,
            repo_root=ROOT,
            proofs=[SpoofedProof()],
        )


def test_test_only_capability_is_rejected_by_production_assembler(tmp_path: Path) -> None:
    intake, source, intake_path, source_path = _real_source_pair(tmp_path)
    verified_intake = verify_architect_intake(
        intake=intake,
        intake_bytes=intake_path.read_bytes(),
        source_ref=str(intake_path),
    )
    verified_bundle = verify_source_bundle(
        source_bundle=source,
        source_bundle_bytes=source_path.read_bytes(),
        verified_intake=verified_intake,
        source_ref=str(source_path),
    )
    test_capability = make_test_only_proof_capability(
        {
            "mode": "VERIFIED_ARTIFACT",
            "claim_id": "geometry",
            "subject_ref": "node-root",
            "payload_id": "fixture-payload",
        }
    )
    with pytest.raises(CapabilityError):
        assemble_verified_ce_stage_payload(
            draft=_draft(intake_path),
            verified_intake=verified_intake,
            verified_source_bundle=verified_bundle,
            repo_root=ROOT,
            proofs=[test_capability],
        )


def test_capability_copy_and_deepcopy_are_rejected() -> None:
    capability = make_test_only_proof_capability(
        {"mode": "VERIFIED_ARTIFACT", "claim_id": "geometry"}
    )
    with pytest.raises(CapabilityError):
        copy.copy(capability)
    with pytest.raises(CapabilityError):
        copy.deepcopy(capability)


def test_stale_verified_payload_is_rejected_after_source_bytes_change(
    tmp_path: Path,
) -> None:
    intake, source, intake_path, source_path = _real_source_pair(tmp_path)
    verified_intake = verify_architect_intake(
        intake=intake,
        intake_bytes=intake_path.read_bytes(),
        source_ref=str(intake_path),
    )
    verified_bundle = verify_source_bundle(
        source_bundle=source,
        source_bundle_bytes=source_path.read_bytes(),
        verified_intake=verified_intake,
        source_ref=str(source_path),
    )
    payload = assemble_verified_ce_stage_payload(
        draft=_draft(intake_path),
        verified_intake=verified_intake,
        verified_source_bundle=verified_bundle,
        repo_root=ROOT,
    )
    intake_path.write_bytes(intake_path.read_bytes() + b"\n")
    with pytest.raises(CapabilityError):
        verified_payload_data(
            payload,
            repo_root=ROOT,
            source_intake_bytes=intake_path.read_bytes(),
            source_bundle_bytes=source_path.read_bytes(),
        )


def test_nonexistent_repo_artifact_does_not_become_verified_ui_evidence(
    tmp_path: Path,
) -> None:
    intake, source, intake_path, source_path = _real_source_pair(tmp_path)
    draft = _draft(
        intake_path,
        claims=[{"claim_id": "ui_control_path", "required": True}],
    )
    draft["reviewed_nodes"][0]["candidate_source_refs"] = [
        {
            "claim_id": "ui_control_path",
            "mode": "VERIFIED_ARTIFACT",
            "source_ref": "docs/does-not-exist.md",
        }
    ]
    verified_intake = verify_architect_intake(
        intake=intake,
        intake_bytes=intake_path.read_bytes(),
        source_ref=str(intake_path),
    )
    verified_bundle = verify_source_bundle(
        source_bundle=source,
        source_bundle_bytes=source_path.read_bytes(),
        verified_intake=verified_intake,
        source_ref=str(source_path),
    )
    capability = assemble_verified_ce_stage_payload(
        draft=draft,
        verified_intake=verified_intake,
        verified_source_bundle=verified_bundle,
        repo_root=ROOT,
    )
    payload = verified_payload_data(
        capability,
        repo_root=ROOT,
        source_intake_bytes=intake_path.read_bytes(),
        source_bundle_bytes=source_path.read_bytes(),
    )
    interrogation = payload["constructability_review"]["reviewed_nodes"][0][
        "interrogation_result"
    ]
    assert interrogation["ui_control_evidence_present"] is False
    assert payload["builder_package_emitted"] is False
    assert payload["unresolved_evidence"]


def test_ce_cannot_self_approve_architect_owned_dynamic_loop(tmp_path: Path) -> None:
    intake, source, intake_path, source_path = _real_source_pair(tmp_path)
    draft = _draft(
        intake_path,
        claims=[{"claim_id": "dynamic_loop_approval", "required": True}],
    )
    verified_intake = verify_architect_intake(
        intake=intake,
        intake_bytes=intake_path.read_bytes(),
        source_ref=str(intake_path),
    )
    verified_bundle = verify_source_bundle(
        source_bundle=source,
        source_bundle_bytes=source_path.read_bytes(),
        verified_intake=verified_intake,
        source_ref=str(source_path),
    )
    capability = assemble_verified_ce_stage_payload(
        draft=draft,
        verified_intake=verified_intake,
        verified_source_bundle=verified_bundle,
        repo_root=ROOT,
    )
    payload = capability_record(capability)["payload"]
    interrogation = payload["constructability_review"]["reviewed_nodes"][0][
        "interrogation_result"
    ]
    assert interrogation["dynamic_loop_approved"] is False
    assert payload["constructability_review"]["constructability_status"] == (
        "needs_architect_amendment"
    )
    assert payload["builder_package_emitted"] is False


def test_runtime_only_responsive_claim_becomes_unproven_downstream_obligation(
    tmp_path: Path,
) -> None:
    intake, source, intake_path, source_path = _real_source_pair(tmp_path)
    draft = _draft(
        intake_path,
        claims=[
            {
                "claim_id": "responsive_behavior",
                "required": True,
                "consumer_stage": "responsive",
                "required_test": "Render at required viewports.",
                "blocking_behavior": "block_builder_handoff",
                "completion_criteria": "Observed reflow passes.",
            }
        ],
    )
    verified_intake = verify_architect_intake(
        intake=intake,
        intake_bytes=intake_path.read_bytes(),
        source_ref=str(intake_path),
    )
    verified_bundle = verify_source_bundle(
        source_bundle=source,
        source_bundle_bytes=source_path.read_bytes(),
        verified_intake=verified_intake,
        source_ref=str(source_path),
    )
    capability = assemble_verified_ce_stage_payload(
        draft=draft,
        verified_intake=verified_intake,
        verified_source_bundle=verified_bundle,
        repo_root=ROOT,
    )
    payload = capability_record(capability)["payload"]
    interrogation = payload["constructability_review"]["reviewed_nodes"][0][
        "interrogation_result"
    ]
    assert interrogation["responsive_behavior"] == "blocked"
    assert payload["builder_package_emitted"] is False
    evidence = payload["evidence_register"][0]
    assert evidence["assurance_kind"] == "DOWNSTREAM_TEST_OBLIGATION"
    assert evidence["verification"]["status"] == "UNPROVEN"


def test_wrong_source_bundle_digest_is_rejected(tmp_path: Path) -> None:
    intake, source, intake_path, source_path = _real_source_pair(tmp_path)
    source["bundle_id"] = "other-bundle"
    with pytest.raises(EvidenceVerificationError):
        verified_intake = verify_architect_intake(
            intake=intake,
            intake_bytes=intake_path.read_bytes(),
            source_ref=str(intake_path),
        )
        verify_source_bundle(
            source_bundle=source,
            source_bundle_bytes=source_path.read_bytes(),
            verified_intake=verified_intake,
            source_ref=str(source_path),
        )


def test_persisted_resolution_mutation_is_rejected(tmp_path: Path) -> None:
    _, _, intake_path, source_path, _, draft_path = _write_verified_inputs(tmp_path)
    output_path = ROOT / ".tmp-test-output" / "verified-mutation.json"
    _cleanup(output_path)
    try:
        result = export_verified_review_file(
            repo_root=ROOT,
            review_draft_path=draft_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
        )
        assert result.handoff_allowed is True, result.as_dict()
        export = load_json(output_path)
        payload = export["final_stage_bundle"]["payload"]["data"]
        payload["authority_resolution"] = [
            {
                "claim_ref": "node-root:geometry",
                "claim_id": "geometry",
                "subject_ref": "node-root",
                "policy": {},
                "submitted_judgment": "forged",
                "verified_evidence": [],
                "resolved_state": "VERIFIED",
                "limitations": [],
                "downstream_obligation": None,
            }
        ]
        diagnostics = validate_verified_transaction_artifact(ROOT, export)
        assert {
            item.code for item in diagnostics
        } & {
            "CE_VERIFIED_RESOLUTION_DIGEST_MISMATCH",
            "CE_VERIFIED_CLAIM_POLICY_DRIFT",
            "CE_VERIFIED_RESOLVED_CLAIM_EVIDENCE_REQUIRED",
        }
    finally:
        _cleanup(output_path)


def test_invalid_builder_package_cannot_remain_authorized(tmp_path: Path) -> None:
    _, _, intake_path, source_path, _, draft_path = _write_verified_inputs(tmp_path)
    output_path = ROOT / ".tmp-test-output" / "verified-builder-invalid.json"
    _cleanup(output_path)
    try:
        result = export_verified_review_file(
            repo_root=ROOT,
            review_draft_path=draft_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
        )
        assert result.handoff_allowed is True, result.as_dict()
        export = load_json(output_path)
        package = export["final_stage_bundle"]["payload"]["data"][
            "builder_executable_package"
        ]
        package["builder_decisions_required"] = 1
        diagnostics = validate_verified_transaction_artifact(ROOT, export)
        assert "CE_VERIFIED_TRX_BUILDER_PACKAGE_NOT_ELIGIBLE" in {
            item.code for item in diagnostics
        }
    finally:
        _cleanup(output_path)


def test_existing_builder_package_schema_remains_compatible(tmp_path: Path) -> None:
    intake, source, intake_path, source_path = _real_source_pair(tmp_path)
    verified_intake = verify_architect_intake(
        intake=intake,
        intake_bytes=intake_path.read_bytes(),
        source_ref=str(intake_path),
    )
    verified_bundle = verify_source_bundle(
        source_bundle=source,
        source_bundle_bytes=source_path.read_bytes(),
        verified_intake=verified_intake,
        source_ref=str(source_path),
    )
    capability = assemble_verified_ce_stage_payload(
        draft=_draft(intake_path),
        verified_intake=verified_intake,
        verified_source_bundle=verified_bundle,
        repo_root=ROOT,
    )
    package = capability_record(capability)["payload"]["builder_executable_package"]
    schema = json.loads(
        (ROOT / "schemas/builder_executable_package.schema.json").read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(schema).iter_errors(package)) == []


def test_legacy_payload_is_preview_only_and_never_authorized(tmp_path: Path) -> None:
    import validator.project_gate_exporter as legacy_exporter

    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload_path = _write_json(tmp_path / "legacy-payload.json", _payload(intake, intake_path))
    output_path = ROOT / ".tmp-test-output" / "legacy-preview.json"
    _cleanup(output_path)
    try:
        result = legacy_exporter.export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
        )
        assert result.status == "blocked"
        assert result.handoff_allowed is False
        export = load_json(output_path)
        assert export["handoff"]["allowed"] is False
        assert result.summary["assurance_kind"] == "DECLARATION"
        assert result.summary["official_builder_authorization"] is False
    finally:
        _cleanup(output_path)


def test_verified_export_bytes_are_deterministic(tmp_path: Path) -> None:
    _, _, intake_path, source_path, _, draft_path = _write_verified_inputs(tmp_path)
    output_path = ROOT / ".tmp-test-output" / "verified-deterministic.json"
    _cleanup(output_path)
    try:
        first = export_verified_review_file(
            repo_root=ROOT,
            review_draft_path=draft_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
        )
        first_bytes = output_path.read_bytes()
        second = export_verified_review_file(
            repo_root=ROOT,
            review_draft_path=draft_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
            overwrite=True,
        )
        assert first.status == second.status == "successful"
        assert output_path.read_bytes() == first_bytes
    finally:
        _cleanup(output_path)


def test_verified_payload_canonical_bytes_are_stable(tmp_path: Path) -> None:
    intake, source, intake_path, source_path = _real_source_pair(tmp_path)
    verified_intake = verify_architect_intake(
        intake=intake,
        intake_bytes=intake_path.read_bytes(),
        source_ref=str(intake_path),
    )
    verified_bundle = verify_source_bundle(
        source_bundle=source,
        source_bundle_bytes=source_path.read_bytes(),
        verified_intake=verified_intake,
        source_ref=str(source_path),
    )
    first = assemble_verified_ce_stage_payload(
        draft=_geometry_draft(intake_path),
        verified_intake=verified_intake,
        verified_source_bundle=verified_bundle,
        repo_root=ROOT,
    )
    second = assemble_verified_ce_stage_payload(
        draft=_geometry_draft(intake_path),
        verified_intake=verified_intake,
        verified_source_bundle=verified_bundle,
        repo_root=ROOT,
    )
    assert canonical_bytes(capability_record(first)["payload"]) == canonical_bytes(
        capability_record(second)["payload"]
    )
