from __future__ import annotations

import copy
import hashlib
import inspect
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

import validator.payload_assembler as payload_assembler
import validator.pcvp_dormant_producer as producer
from deterministic_runtime_support import (
    canonical_bundle,
    canonical_draft,
    canonical_intake,
    evaluation_run,
)
from validator.payload_assembler import canonical_bytes
from validator.pcvp_carrier import inspect_optional_pcvp_carrier
from validator.pcvp_identity import PCVPIdentityError, load_pcvp_resources

ROOT = Path(__file__).resolve().parents[1]


def _authoritative_inputs() -> dict[str, Any]:
    bundle = canonical_bundle()
    intake = canonical_intake(bundle=bundle)
    return {
        "architect_intake": intake,
        "architect_intake_bytes": canonical_bytes(intake),
        "source_bundle": bundle,
        "source_bundle_bytes": canonical_bytes(bundle),
        "review_draft": canonical_draft(),
        "repository_root": ROOT,
    }


def _derive(**overrides: Any) -> dict[str, Any]:
    values = _authoritative_inputs()
    values.update(overrides)
    return producer.derive_continuation_assurance(**values)


def _copy_pcvp_resources(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    target = root / "contracts" / "pcvp"
    target.parent.mkdir(parents=True)
    shutil.copytree(ROOT / "contracts" / "pcvp", target)
    return root


def _load_lock(root: Path) -> dict[str, Any]:
    return json.loads(
        (root / "contracts/pcvp/pcvp-v1.lock.json").read_text(encoding="utf-8")
    )


def _write_lock(root: Path, lock: dict[str, Any]) -> None:
    (root / "contracts/pcvp/pcvp-v1.lock.json").write_text(
        json.dumps(lock, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def test_active_payload_path_is_structurally_carrier_free(monkeypatch: pytest.MonkeyPatch) -> None:
    source = inspect.getsource(payload_assembler)
    assert "pcvp_dormant_producer" not in source
    assert "attach_to_builder_package_if_enabled" not in source

    baseline, _, _ = evaluation_run(ROOT)
    baseline_payload = baseline["payload"]
    baseline_package = baseline_payload["builder_executable_package"]
    assert isinstance(baseline_package, dict)
    assert "continuation_assurance" not in baseline_package

    monkeypatch.setattr(payload_assembler, "PRODUCER_EMISSION_ENABLED", True, raising=False)
    monkeypatch.setattr(
        payload_assembler,
        "attach_to_builder_package_if_enabled",
        lambda package: package.update({"continuation_assurance": {"forged": True}}),
        raising=False,
    )
    observed, _, _ = evaluation_run(ROOT)
    assert observed["payload"] == baseline_payload
    assert "continuation_assurance" not in observed["payload"]["builder_executable_package"]


def test_unsafe_emission_and_raw_package_apis_are_absent() -> None:
    assert not hasattr(producer, "PRODUCER_EMISSION_ENABLED")
    assert not hasattr(producer, "attach_to_builder_package_if_enabled")
    assert not hasattr(producer, "build_continuation_assurance")
    assert producer.__all__ == [
        "ARCHITECTURE_LOCK_ID",
        "CANONICAL_COMMIT",
        "CANONICAL_REPOSITORY",
        "PCVPDormantProducerError",
        "POLICY_ID",
        "POLICY_VERSION",
        "derive_continuation_assurance",
        "verify_dormant_producer_resources",
    ]


@pytest.mark.parametrize(
    "forbidden",
    [
        {"builder_package": {"builder_package_status": "executable_ready"}},
        {"persisted_payload": {"payload_status": "complete"}},
        {"runtime_results": [{"status": "passed"}]},
        {"completed_runtime_result": {"status": "passed"}},
    ],
)
def test_raw_or_completed_authority_inputs_are_rejected(forbidden: dict[str, Any]) -> None:
    with pytest.raises(
        producer.PCVPDormantProducerError,
        match="Unsupported authority inputs are forbidden",
    ):
        _derive(**forbidden)


def test_genuine_replay_derivation_is_deterministic_and_bounded() -> None:
    first = _derive()
    second = _derive()
    assert first == second
    assert first["source_stage"] == "CONSTRUCTABILITY_ENGINEER"
    assert first["claims"][0]["verification_state"] == "VERIFIED"
    assert first["claims"][1]["verification_state"] == "UNVERIFIED"
    assert first["effects"][0]["effect_class"] == "EXTERNAL_MUTATION"
    assert first["effects"][0]["continuation_state"] == "AUTHORIZATION_REQUIRED"
    assert first["effects"][0]["authorization_ref"] is None
    assert first["authorizations"] == []
    assert first["stage_summary"]["owner_projection"] == "YELLOW"
    assert first["stage_summary"]["yellow_substate"] == "OWNER_CHOICE_REQUIRED"


@pytest.mark.parametrize("field", ["architect_intake", "source_bundle"])
def test_mapping_and_exact_bytes_must_match(field: str) -> None:
    values = _authoritative_inputs()
    altered = copy.deepcopy(values[field])
    altered["tampered"] = True
    values[f"{field}_bytes"] = canonical_bytes(altered)
    with pytest.raises(
        producer.PCVPDormantProducerError,
        match="mapping does not match its exact source bytes",
    ):
        producer.derive_continuation_assurance(**values)


def test_exact_sources_must_be_bytes() -> None:
    with pytest.raises(
        producer.PCVPDormantProducerError,
        match="exact bytes must be bytes",
    ):
        _derive(architect_intake_bytes="not-bytes")


def test_invalid_review_draft_fails_closed() -> None:
    draft = canonical_draft()
    draft.pop("architecture_echo")
    with pytest.raises(
        producer.PCVPDormantProducerError,
        match="Authoritative CE replay failed closed",
    ):
        _derive(review_draft=draft)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("architect_contract",), None),
        (("confirmation_request",), None),
        (("first_safe_builder_batch",), None),
        (("strategy_map_ref",), None),
        (("selected_candidate_id_unchanged",), False),
        (("approved_class_names_unchanged",), False),
        (("builder_package_status",), "blocked"),
    ],
)
def test_recomputed_builder_package_full_contract_is_enforced(
    monkeypatch: pytest.MonkeyPatch,
    path: tuple[str, ...],
    value: Any,
) -> None:
    run, _, _ = evaluation_run(ROOT)
    tampered = copy.deepcopy(run["payload"])
    target = tampered["builder_executable_package"]
    assert isinstance(target, dict)
    cursor: dict[str, Any] = target
    for part in path[:-1]:
        cursor = cursor[part]
    cursor[path[-1]] = value

    monkeypatch.setattr(producer, "verified_payload_data", lambda *args, **kwargs: tampered)
    with pytest.raises(
        producer.PCVPDormantProducerError,
        match="Full Builder package schema failure|not deterministically Builder-ready",
    ):
        _derive()


def test_tampered_recomputed_payload_cannot_mint_a_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run, _, _ = evaluation_run(ROOT)
    tampered = copy.deepcopy(run["payload"])
    tampered["builder_executable_package"]["continuation_assurance"] = {"forged": True}
    monkeypatch.setattr(producer, "verified_payload_data", lambda *args, **kwargs: tampered)
    with pytest.raises(
        producer.PCVPDormantProducerError,
        match="unexpectedly contains continuation_assurance|Full Builder package schema failure",
    ):
        _derive()


def test_coordinated_schema_and_lock_drift_is_rejected_by_both_loaders(
    tmp_path: Path,
) -> None:
    root = _copy_pcvp_resources(tmp_path)
    schema_path = (
        root
        / "contracts/pcvp/vendor/decision-kernel/v1.0.0/claim.schema.json"
    )
    schema_path.write_bytes(schema_path.read_bytes() + b"\n")
    lock = _load_lock(root)
    for entry in lock["files"]:
        if entry["name"] == "claim.schema.json":
            entry["sha256"] = hashlib.sha256(schema_path.read_bytes()).hexdigest()
    _write_lock(root, lock)

    with pytest.raises(PCVPIdentityError, match="canonical identity mismatch"):
        producer.verify_dormant_producer_resources(root)
    projection, diagnostics = inspect_optional_pcvp_carrier(
        {"continuation_assurance": {}},
        repository_root=root,
    )
    assert projection["status"] == "invalid"
    assert any(item.code == "CE_PCVP_CANONICAL_IDENTITY_MISMATCH" for item in diagnostics)


def test_coordinated_profile_and_lock_drift_is_rejected_by_both_loaders(
    tmp_path: Path,
) -> None:
    root = _copy_pcvp_resources(tmp_path)
    profile_path = root / "contracts/pcvp/constructability.profile.yaml"
    profile_path.write_bytes(profile_path.read_bytes() + b"\n")
    lock = _load_lock(root)
    lock["profile"]["sha256"] = hashlib.sha256(profile_path.read_bytes()).hexdigest()
    _write_lock(root, lock)

    with pytest.raises(PCVPIdentityError, match="canonical identity mismatch"):
        producer.verify_dormant_producer_resources(root)
    projection, diagnostics = inspect_optional_pcvp_carrier(
        {"continuation_assurance": {}},
        repository_root=root,
    )
    assert projection["status"] == "invalid"
    assert any(item.code == "CE_PCVP_CANONICAL_IDENTITY_MISMATCH" for item in diagnostics)


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("canonical", "repository", "example/other"),
        ("canonical", "commit_sha", "0" * 40),
        ("canonical", "schema_root", "moving/schema/root"),
        ("canonical", "profile_path", "moving/profile.yaml"),
        ("vendored", "root", "contracts/pcvp/other"),
        ("vendored", "local_copy_authoritative", True),
        ("profile", "path", "contracts/pcvp/other.profile.yaml"),
        ("profile", "local_copy_authoritative", True),
    ],
)
def test_identity_and_path_drift_is_field_specifically_rejected(
    tmp_path: Path,
    section: str,
    field: str,
    value: Any,
) -> None:
    root = _copy_pcvp_resources(tmp_path)
    lock = _load_lock(root)
    lock[section][field] = value
    _write_lock(root, lock)
    with pytest.raises(PCVPIdentityError) as captured:
        load_pcvp_resources(root)
    assert section in captured.value.path
    assert field in captured.value.path


def test_resource_summary_remains_dormant_and_non_authoritative() -> None:
    result = producer.verify_dormant_producer_resources(ROOT)
    assert result == {
        "architecture_lock_id": "EV4-PCVP-ROLL-LOCK-20260727-R1",
        "canonical_commit": "069a50fa243b01fa578a7c1bcb8864d9e796d34b",
        "schema_count": 4,
        "producer_emission": False,
        "adoption_status": "not_yet_adopted",
        "activation_effect": "NONE",
    }
