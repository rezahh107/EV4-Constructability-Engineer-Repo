from __future__ import annotations

import copy
from collections.abc import Callable
from pathlib import Path

import pytest

import validator.project_gate_exporter as exporter_module
from exporter_test_support import ROOT, _payload, _provenance, _real_source_pair, _write_json
from validator.project_gate_export import load_json
from validator.project_gate_exporter import export_file

Mutation = Callable[[dict], None]


def _interrogation(payload: dict) -> dict:
    return payload["constructability_review"]["reviewed_nodes"][0]["interrogation_result"]


def _fake_geometry(payload: dict) -> None:
    interrogation = _interrogation(payload)
    interrogation.update(
        geometry_required=True,
        geometry_proven=True,
        geometry_proof={"claim": "invented geometry"},
    )


def _shallow_overlay(payload: dict) -> None:
    interrogation = _interrogation(payload)
    interrogation.update(
        overlay_strategy_required=True,
        overlay_strategy_proven=True,
        overlay_strategy={"description": "place it above the section"},
    )


def _unbound_responsive(payload: dict) -> None:
    interrogation = _interrogation(payload)
    interrogation.update(
        action_targets_responsive=True,
        responsive_behavior="evidence_backed",
    )


def _nonexistent_ui_path(payload: dict) -> None:
    interrogation = _interrogation(payload)
    interrogation.update(
        exact_ui_control_path_used=True,
        ui_control_evidence_present=True,
        ui_control_evidence={"path": "docs/does-not-exist.md"},
    )


def _unsupported_accessibility(payload: dict) -> None:
    interrogation = _interrogation(payload)
    interrogation.update(
        accessibility_claimed=True,
        accessibility_evidenced=True,
    )


def _self_approved_dynamic_loop(payload: dict) -> None:
    interrogation = _interrogation(payload)
    interrogation.update(
        dynamic_loop_implied=True,
        dynamic_loop_approved=True,
        dynamic_loop_binding_map={"binding": "invented"},
    )


def _caller_validated_evidence(payload: dict) -> None:
    payload["evidence_register"] = [
        {
            "id": "caller-evidence-validated",
            "kind": "validator",
            "state": "validated",
            "description": "Caller says this is validated.",
            "source": {
                "type": "repo_path",
                "reference": "docs/does-not-exist.md",
            },
        }
    ]


def _copied_other_subject_proof(payload: dict) -> None:
    interrogation = _interrogation(payload)
    interrogation.update(
        geometry_required=True,
        geometry_proven=True,
        geometry_proof={
            "subject_ref": "another-node",
            "anchors": ["other-root"],
        },
    )


def _wrong_source_sha(payload: dict) -> None:
    interrogation = _interrogation(payload)
    interrogation.update(
        geometry_required=True,
        geometry_proven=True,
        geometry_proof={
            "subject_ref": "node-root",
            "source_sha256": "0" * 64,
            "anchors": ["root"],
        },
    )


def _raw_operator_payload(payload: dict) -> None:
    # The baseline itself is a raw operator-authored CE Stage Payload path.
    assert payload["builder_package_emitted"] is True


CASES: tuple[tuple[str, str, Mutation], ...] = (
    ("CE-AUTH-001", "geometry_proven with invented non-empty geometry_proof", _fake_geometry),
    ("CE-AUTH-002", "overlay_strategy_proven with shallow text carrier", _shallow_overlay),
    ("CE-AUTH-003", "responsive evidence_backed without source binding", _unbound_responsive),
    ("CE-AUTH-004", "UI control evidence with nonexistent path", _nonexistent_ui_path),
    ("CE-AUTH-005", "accessibility_evidenced without compatible evidence", _unsupported_accessibility),
    ("CE-AUTH-006", "CE self-approves Architect-owned dynamic loop", _self_approved_dynamic_loop),
    ("CE-AUTH-007", "caller-authored evidence state=validated", _caller_validated_evidence),
    ("CE-AUTH-008", "proof copied from another subject", _copied_other_subject_proof),
    ("CE-AUTH-009", "proof carries a wrong source SHA", _wrong_source_sha),
    ("CE-AUTH-010", "raw operator-authored payload path", _raw_operator_payload),
)


@pytest.fixture(autouse=True)
def clean_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        exporter_module,
        "inspect_git_provenance",
        lambda repo_root, ignored_paths=(): _provenance(dirty=False),
    )


@pytest.mark.parametrize(("test_id", "authority_effect", "mutate"), CASES, ids=[item[0] for item in CASES])
def test_current_runtime_allows_unsupported_authority_to_reach_handoff(
    tmp_path: Path,
    test_id: str,
    authority_effect: str,
    mutate: Mutation,
) -> None:
    intake, _, intake_path, source_path = _real_source_pair(tmp_path)
    payload = copy.deepcopy(_payload(intake, intake_path))
    mutate(payload)
    payload_path = _write_json(tmp_path / f"{test_id}-payload.json", payload)
    output_path = ROOT / ".tmp-test-output" / f"{test_id}.json"
    output_path.unlink(missing_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = export_file(
            repo_root=ROOT,
            payload_path=payload_path,
            source_intake_path=intake_path,
            source_bundle_path=source_path,
            output_path=output_path,
        )
        persisted = load_json(output_path) if output_path.exists() else {}

        assert result.status == "successful", {
            "test_id": test_id,
            "authority_effect": authority_effect,
            "classification": "AUTHORITY_PATH_REJECTED",
            "result": result.as_dict(),
        }
        assert result.output_written is True
        assert result.handoff_allowed is True
        assert persisted["handoff"]["allowed"] is True, {
            "test_id": test_id,
            "authority_effect": authority_effect,
            "classification": "AUTHORITY_BYPASS_CONFIRMED",
        }
    finally:
        output_path.unlink(missing_ok=True)
        try:
            output_path.parent.rmdir()
        except OSError:
            pass
