from __future__ import annotations

import json
from pathlib import Path

import pytest

from validator.ce_validation_transaction import ExporterError, assert_snapshot_unchanged, capture_json_snapshot, safe_output_path
from validator.claim_evaluators import evaluate_claim
from validator.payload_fidelity import evaluate_ce_transaction
from validator.project_gate_exporter_build import _handoff_diagnostics
from validator.project_gate_exporter_core import ExportResult, GitProvenance
from validator.runtime_execution import RuntimeExecutionBoundaryError, execute_runtime_requests, execution_transaction_id
from validator.verified_project_gate_exporter import reject_legacy_payload_export
from deterministic_runtime_support import canonical_bundle, canonical_draft, canonical_intake

ROOT = Path(__file__).resolve().parents[1]


def _responsive_draft() -> dict:
    draft = canonical_draft()
    node = draft["reviewed_nodes"][0]
    node["proposed_action"] = "configure responsive behavior"
    node["claim_semantics"]["responsive_strategy"] = {"breakpoint_strategy": "mobile-first at project breakpoints", "layout_adaptation": "stack root content below 768px", "derivation_method": "derive from retained parent-child layout"}
    node["claim_semantics"]["responsive_behavior"] = {"target_identity": "node-root"}
    draft["builder_action_proposals"][0] = {"action_id": "action-root", "action_type": "set_responsive", "target_node": "node-root", "parameters": {"layout": "stacked", "breakpoints": "mobile-first", "target_identity": "node-root"}}
    return draft


def _runtime_target(path: Path) -> Path:
    path.write_text(json.dumps({"schema_id": "ev4-ce-responsive-evaluation-target@1.0.0", "claim_id": "responsive_behavior", "subject_ref": "node-root", "target_identity": "node-root", "cases": [{"viewport": "mobile", "expected_layout": "stacked", "observed_layout": "stacked"}]}, sort_keys=True), encoding="utf-8")
    return path


def _runtime_request(input_ref: str) -> dict:
    return {"claim_id": "responsive_behavior", "subject_ref": "node-root", "evaluator_id": "ce-responsive-evaluator", "target_identity": "node-root", "input_ref": input_ref}


def test_official_cli_remains_verified_review_runtime() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'ev4-ce-project-gate-export = "validator.verified_project_gate_exporter:main"' in pyproject
    source = (ROOT / "validator/verified_project_gate_exporter.py").read_text(encoding="utf-8")
    for option in ("--review-draft", "--source-intake", "--source-bundle", "--output", "--repo-root", "--overwrite"):
        assert option in source
    assert "--intermediate-inputs" not in source


def test_one_canonical_evaluator_and_no_parallel_carrier_authority() -> None:
    fidelity = (ROOT / "validator/payload_fidelity.py").read_text(encoding="utf-8")
    assert fidelity.count("def evaluate_ce_transaction(") == 1
    verified = (ROOT / "validator/verified_constructability.py").read_text(encoding="utf-8")
    assert "recompute_expected_payload" in verified
    assert not (ROOT / "validator/intermediate_carriers.py").exists()
    assert not (ROOT / "schemas/ce_intermediate_export_inputs.v1.schema.json").exists()


def test_legacy_payload_cannot_authorize_builder(tmp_path: Path) -> None:
    result = reject_legacy_payload_export(repo_root=ROOT, payload_path=tmp_path / "legacy.json", source_intake_path=tmp_path / "intake.json", source_bundle_path=tmp_path / "bundle.json", output_path=tmp_path / "output.json")
    assert result.status == "invalid"
    assert result.handoff_allowed is False
    assert result.diagnostics[0].code == "CE_EXPORT_LEGACY_PAYLOAD_AUTHORIZATION_FORBIDDEN"


def test_runtime_supported_evaluator_executes_in_current_transaction(tmp_path: Path) -> None:
    target = _runtime_target(tmp_path / "responsive.json")
    request = _runtime_request(target.name)
    row = evaluate_claim("responsive_behavior", "node-root", {}, canonical_intake(), canonical_bundle(), _responsive_draft(), {"repo_root": tmp_path}, [request])
    assert row["status"] == "satisfied"
    assert row["evidence_records"][0]["mode"] == "VERIFIED_TOOL_EXECUTION"
    assert row["evidence_records"][0]["execution_status"] == "success"


def test_runtime_result_from_another_transaction_is_not_selected(tmp_path: Path) -> None:
    target = _runtime_target(tmp_path / "responsive.json")
    request = _runtime_request(target.name)
    transaction = execution_transaction_id(architect_intake=canonical_intake(), source_bundle=canonical_bundle(), review_draft=_responsive_draft(), requests=[request])
    batch = execute_runtime_requests(repo_root=tmp_path, transaction_id=transaction, requests=[request])
    row = evaluate_claim("responsive_behavior", "node-root", {}, canonical_intake(), canonical_bundle(), _responsive_draft(), {"repo_root": tmp_path}, execution_batch=batch, execution_transaction_id_override="other-transaction")
    assert row["status"] == "downstream_validation_required"
    assert row["evidence_refs"] == []


def test_unsupported_runtime_evaluator_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(RuntimeExecutionBoundaryError):
        execute_runtime_requests(repo_root=tmp_path, transaction_id="trx", requests=[{**_runtime_request("missing.json"), "evaluator_id": "caller-evaluator"}])


def test_successful_runtime_execution_removes_pending_obligation(tmp_path: Path) -> None:
    target = _runtime_target(tmp_path / "responsive.json")
    payload, results = evaluate_ce_transaction(architect_intake=canonical_intake(), source_bundle=canonical_bundle(), review_draft=_responsive_draft(), repo_root=tmp_path, runtime_execution_requests=[_runtime_request(target.name)])
    runtime_row = next(row for row in results["dependency_result"]["rows"] if row["claim_id"] == "responsive_behavior")
    assert runtime_row["status"] == "satisfied"
    assert runtime_row["evidence_refs"]
    assert payload["downstream_test_obligations"] == []


def test_missing_runtime_target_remains_phase_aware_obligation(tmp_path: Path) -> None:
    payload, _ = evaluate_ce_transaction(architect_intake=canonical_intake(), source_bundle=canonical_bundle(), review_draft=_responsive_draft(), repo_root=tmp_path, runtime_execution_requests=[_runtime_request("missing.json")])
    assert payload["builder_package_emitted"] is True
    assert payload["downstream_test_obligations"][0]["status"] == "required"


def test_explicit_snapshot_and_alias_boundaries(tmp_path: Path) -> None:
    review = tmp_path / "custom" / "review-any-name.json"
    review.parent.mkdir()
    review.write_text('{"schema_id":"x"}', encoding="utf-8")
    snapshot = capture_json_snapshot(review, label="CE Review Draft", read_error_code="READ", changed_error_code="CHANGED")
    assert snapshot.path == review
    with pytest.raises(ExporterError) as captured:
        safe_output_path(tmp_path, review, True, protected_inputs=(review,))
    assert captured.value.diagnostic.code == "CE_EXPORT_OUTPUT_ALIASES_INPUT"
    review.write_text('{"schema_id":"changed"}', encoding="utf-8")
    with pytest.raises(ExporterError) as changed:
        assert_snapshot_unchanged(snapshot)
    assert changed.value.diagnostic.code == "CHANGED"


def test_duplicate_json_keys_fail_snapshot_capture(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"a":1,"a":2}', encoding="utf-8")
    with pytest.raises(ExporterError) as captured:
        capture_json_snapshot(path, label="duplicate", read_error_code="READ", changed_error_code="CHANGED")
    assert captured.value.diagnostic.code == "CE_EXPORT_INPUT_INVALID_JSON"


def test_dirty_git_state_is_metadata_only() -> None:
    provenance = GitProvenance(repository="rezahh107/EV4-Constructability-Engineer-Repo", ref="agent/verified-constructability-proof-runtime", commit_sha="1" * 40, dirty=True, dirty_paths=("docs/unrelated.md",))
    diagnostics = _handoff_diagnostics({"payload_status": "complete", "unresolved_evidence": [], "builder_package_emitted": True, "constructability_review": {"constructability_status": "executable_ready"}}, {"intake_status": "complete"}, {}, provenance)
    assert "CE_EXPORT_DIRTY_WORKTREE_BLOCKS_HANDOFF" not in {item.code for item in diagnostics}
    result = ExportResult(status="successful", output_path=None, output_written=False, handoff_allowed=True, diagnostics=(), summary={"repository_dirty": provenance.dirty, "dirty_paths": list(provenance.dirty_paths)})
    assert result.summary["repository_dirty"] is True
    assert result.summary["dirty_paths"] == ["docs/unrelated.md"]
