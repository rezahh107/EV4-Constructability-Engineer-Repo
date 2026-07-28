from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

from validator.payload_assembler import canonical_bytes
from validator.pcvp_carrier import (
    ARCHITECT_PROFILE_SHA256,
    PROFILE_SHA256,
    canonical_sha256,
    inspect_optional_pcvp_carrier,
)
from validator.verified_constructability import (
    EvidenceVerificationError,
    verify_architect_intake,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-ce-architect-stage-intake.py"
FIXTURE = (
    ROOT
    / "fixtures"
    / "architect-stage-intake-v1-1"
    / "valid"
    / "project-gate-transition-complete.v1_1.json"
)
LOCK_PATH = ROOT / "contracts" / "pcvp" / "pcvp-v1.lock.json"
PROFILE_PATH = ROOT / "contracts" / "pcvp" / "constructability.profile.yaml"
ARCHITECT_PROFILE_PATH = ROOT / "contracts" / "pcvp" / "architect.profile.yaml"
VENDORED_ROOT = (
    ROOT / "contracts" / "pcvp" / "vendor" / "decision-kernel" / "v1.0.0"
)

spec = importlib.util.spec_from_file_location("ce_pcvp_intake_validator", SCRIPT)
mod = importlib.util.module_from_spec(spec)
sys.modules["ce_pcvp_intake_validator"] = mod
assert spec.loader is not None
spec.loader.exec_module(mod)


def _intake() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _carrier() -> dict:
    return {
        "policy_id": "EV4-PCVP",
        "policy_version": "1.0.0",
        "source_stage": "ARCHITECT",
        "claims": [
            {
                "claim_id": "CLM-ARCH-001",
                "statement": "The bounded architecture draft has source evidence.",
                "criticality": "CRITICAL",
                "applicability_state": "APPLICABLE",
                "verification_state": "VERIFIED",
                "lifecycle_state": "ACTIVE",
                "evidence_refs": ["EVD-ARCH-001"],
                "dependency_refs": [],
                "assumption_refs": [],
            }
        ],
        "effects": [
            {
                "effect_id": "EFF-ARCH-001",
                "effect_class": "DRAFT_ONLY",
                "depends_on_claim_ids": ["CLM-ARCH-001"],
                "continuation_state": "CONTINUE",
                "authorization_ref": "AUTH-ARCH-001",
                "blocker_reason": None,
                "permitted_scope": "provisional architecture handoff only",
            }
        ],
        "authorizations": [
            {
                "authorization_id": "AUTH-ARCH-001",
                "basis": "PROFILE_PREAUTHORIZED",
                "status": "ACTIVE",
                "allowed_effect_ids": ["EFF-ARCH-001"],
                "allowed_effect_classes": ["DRAFT_ONLY"],
                "bound_unknown_ids": [],
                "bound_assumption_ids": [],
                "stage_scope": {
                    "from": "ARCHITECT",
                    "through": "CONSTRUCTABILITY_ENGINEER",
                },
                "permitted_scope": "provisional architecture handoff only",
                "valid_until_events": [
                    "NEW_MATERIAL_BLOCKER",
                    "OWNER_REVOCATION",
                    "SCOPE_EXPANSION",
                ],
            }
        ],
        "unresolved_items": [],
        "stage_summary": {
            "owner_projection": "GREEN",
            "yellow_substate": None,
            "derived_from_claim_ids": ["CLM-ARCH-001"],
            "current_effect_id": "EFF-ARCH-001",
            "lifecycle_state": "ACTIVE",
            "derivation_reason": "critical dependent claim is verified",
        },
    }


def _with_carrier() -> dict:
    intake = _intake()
    intake["continuation_assurance"] = _carrier()
    return intake


def _codes(result: dict) -> set[str]:
    return {item["code"] for item in result["diagnostics"]}


def _mutate_profile_authorized_effect(intake: dict, effect_class: str) -> None:
    carrier = intake["continuation_assurance"]
    carrier["effects"][0]["effect_class"] = effect_class
    carrier["authorizations"][0]["allowed_effect_classes"] = [effect_class]


def test_legacy_intake_without_pcvp_remains_valid() -> None:
    intake = _intake()
    before = copy.deepcopy(intake)

    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(intake)
    projection, diagnostics = inspect_optional_pcvp_carrier(intake, ROOT)

    assert result["status"] == "valid", result
    assert diagnostics == []
    assert projection["status"] == "legacy_absent"
    assert projection["compatibility_mode"] == "DUAL_READ"
    assert projection["activation_effect"] == "NONE"
    assert intake == before


def test_valid_pcvp_is_read_losslessly_without_activation_or_emission() -> None:
    intake = _with_carrier()
    before = copy.deepcopy(intake)

    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(intake)
    projection, diagnostics = inspect_optional_pcvp_carrier(intake, ROOT)
    verified = verify_architect_intake(
        intake=intake,
        intake_bytes=canonical_bytes(intake),
        source_ref="architect-intake.json",
        repo_root=ROOT,
    )

    assert result["status"] == "valid", result
    assert diagnostics == []
    assert projection["status"] == "validated"
    assert projection["policy_id"] == "EV4-PCVP"
    assert projection["policy_version"] == "1.0.0"
    assert projection["source_stage"] == "ARCHITECT"
    assert projection["adoption_status"] == "not_yet_adopted"
    assert projection["activation_effect"] == "NONE"
    assert projection["carrier"] == {
        "continuation_assurance": before["continuation_assurance"]
    }
    assert projection["canonical_sha256"] == canonical_sha256(
        projection["carrier"]
    )
    assert verified["data"]["continuation_assurance"] == before[
        "continuation_assurance"
    ]
    assert intake == before


@pytest.mark.parametrize(
    "effect_class",
    [
        "REVERSIBLE_LOCAL_CHANGE",
        "EXTERNAL_MUTATION",
        "IRREVERSIBLE_OR_AUTHORITY_BEARING",
    ],
)
def test_architect_profile_preauthorization_rejects_effects_outside_profile(
    effect_class: str,
) -> None:
    intake = _with_carrier()
    _mutate_profile_authorized_effect(intake, effect_class)

    projection, diagnostics = inspect_optional_pcvp_carrier(intake, ROOT)
    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(intake)

    assert projection["status"] == "invalid"
    assert "CE_PCVP_PROFILE_PREAUTHORIZED_EFFECT_FORBIDDEN" in {
        item.code for item in diagnostics
    }
    assert result["status"] == "invalid"
    assert "CE_PCVP_PROFILE_PREAUTHORIZED_EFFECT_FORBIDDEN" in _codes(result)
    with pytest.raises(
        EvidenceVerificationError,
        match="CE_PCVP_PROFILE_PREAUTHORIZED_EFFECT_FORBIDDEN",
    ):
        verify_architect_intake(
            intake=intake,
            intake_bytes=canonical_bytes(intake),
            source_ref="architect-intake.json",
            repo_root=ROOT,
        )


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        (
            lambda carrier: carrier.update(policy_version="2.0.0"),
            "CE_PCVP_CARRIER_SCHEMA_INVALID",
        ),
        (
            lambda carrier: carrier.update(source_stage="PROJECT_GATE"),
            "CE_PCVP_SOURCE_STAGE_MISMATCH",
        ),
        (
            lambda carrier: carrier["claims"][0].update(
                dependency_refs=["CLM-MISSING"]
            ),
            "CE_PCVP_CLAIM_DEPENDENCY_UNRESOLVED",
        ),
        (
            lambda carrier: carrier["authorizations"][0].update(
                status="REVOKED"
            ),
            "CE_PCVP_EFFECT_AUTH_NOT_ACTIVE",
        ),
        (
            lambda carrier: carrier["authorizations"][0]["stage_scope"].update(
                through="BUILDER_ASSISTANT"
            ),
            "CE_PCVP_EFFECT_AUTH_STAGE_SCOPE_MISMATCH",
        ),
        (
            lambda carrier: carrier["authorizations"][0].update(
                allowed_effect_ids=[],
                allowed_effect_classes=["REASONING_ONLY"],
            ),
            "CE_PCVP_EFFECT_AUTH_NOT_COVERING",
        ),
        (
            lambda carrier: carrier["stage_summary"].update(
                owner_projection="RED"
            ),
            "CE_PCVP_RED_WITH_NON_BLOCKED_EFFECT",
        ),
    ],
)
def test_malformed_or_mechanically_invalid_carriers_fail_closed(
    mutation,
    expected_code: str,
) -> None:
    intake = _with_carrier()
    mutation(intake["continuation_assurance"])

    result = mod.CEArchitectStageIntakeValidator(ROOT).validate_value(intake)

    assert result["status"] == "invalid"
    assert expected_code in _codes(result)
    with pytest.raises(EvidenceVerificationError, match=expected_code):
        verify_architect_intake(
            intake=intake,
            intake_bytes=canonical_bytes(intake),
            source_ref="architect-intake.json",
            repo_root=ROOT,
        )


@pytest.mark.parametrize("coordinated_lock_update", [False, True])
def test_architect_source_profile_drift_cannot_create_new_preauthorization(
    tmp_path: Path,
    coordinated_lock_update: bool,
) -> None:
    test_root = tmp_path / "repo"
    pcvp_root = test_root / "contracts" / "pcvp"
    shutil.copytree(ROOT / "contracts" / "pcvp", pcvp_root)

    profile_path = pcvp_root / "architect.profile.yaml"
    profile_text = profile_path.read_text(encoding="utf-8")
    marker = "  safe_reversible_default_enabled: true\n"
    addition = (
        "  - effect_class: EXTERNAL_MUTATION\n"
        "    bounded_output_types:\n"
        "    - mutated_external_action\n"
        "    scope: mutated local mirror only\n"
    )
    assert marker in profile_text
    profile_path.write_text(
        profile_text.replace(marker, addition + marker, 1),
        encoding="utf-8",
    )

    if coordinated_lock_update:
        lock_path = pcvp_root / "pcvp-v1.lock.json"
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        lock["source_profiles"]["ARCHITECT"]["sha256"] = hashlib.sha256(
            profile_path.read_bytes()
        ).hexdigest()
        lock_path.write_text(
            json.dumps(lock, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    intake = _with_carrier()
    _mutate_profile_authorized_effect(intake, "EXTERNAL_MUTATION")
    projection, diagnostics = inspect_optional_pcvp_carrier(intake, test_root)

    assert projection["status"] == "invalid"
    assert "CE_PCVP_CANONICAL_IDENTITY_MISMATCH" in {
        item.code for item in diagnostics
    }


def test_pcvp_lock_covers_exact_non_authoritative_profile_and_schemas() -> None:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))

    assert lock["architecture_lock_id"] == "EV4-PCVP-ROLL-LOCK-20260727-R1"
    assert lock["canonical"]["repository"] == "rezahh107/EV4-Decision-Kernel"
    assert (
        lock["canonical"]["commit_sha"]
        == "069a50fa243b01fa578a7c1bcb8864d9e796d34b"
    )
    assert lock["policy"]["adoption_status"] == "not_yet_adopted"
    assert lock["policy"]["activation"] == "NONE"
    assert lock["profile"]["repository"] == (
        "rezahh107/EV4-Constructability-Engineer-Repo"
    )
    assert lock["profile"]["stage_id"] == "CONSTRUCTABILITY_ENGINEER"
    assert lock["profile"]["consumes_from"] == ["ARCHITECT"]
    assert lock["profile"]["local_copy_authoritative"] is False
    assert hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest() == PROFILE_SHA256

    architect = lock["source_profiles"]["ARCHITECT"]
    assert architect == {
        "profile_id": "EV4-PCVP-PROFILE-ARCHITECT",
        "profile_version": "1.0.0",
        "repository": "rezahh107/EV4-Architect-Repo",
        "stage_id": "ARCHITECT",
        "canonical_path": "kernel/pcvp/v1.0.0/bundle/03-PROFILES/architect.profile.yaml",
        "path": "contracts/pcvp/architect.profile.yaml",
        "sha256": ARCHITECT_PROFILE_SHA256,
        "local_copy_authoritative": False,
    }
    assert (
        hashlib.sha256(ARCHITECT_PROFILE_PATH.read_bytes()).hexdigest()
        == ARCHITECT_PROFILE_SHA256
    )
    assert {
        item["name"]: item["sha256"] for item in lock["files"]
    } == {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(VENDORED_ROOT.glob("*.schema.json"))
    }
