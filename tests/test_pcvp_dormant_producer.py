from __future__ import annotations

import copy
from pathlib import Path

import pytest
from deterministic_runtime_support import evaluation_run

from validator.pcvp_dormant_producer import (
    PRODUCER_EMISSION_ENABLED,
    PCVPDormantProducerError,
    attach_to_builder_package_if_enabled,
    build_continuation_assurance,
    verify_dormant_producer_resources,
)

ROOT = Path(__file__).resolve().parents[1]


def _package() -> dict:
    run, _, _ = evaluation_run(ROOT)
    package = run["payload"]["builder_executable_package"]
    assert isinstance(package, dict)
    return copy.deepcopy(package)


def test_resources_are_pinned_and_emission_is_hard_disabled() -> None:
    result = verify_dormant_producer_resources(ROOT)
    assert result["schema_count"] == 4
    assert result["producer_emission"] is False
    assert result["adoption_status"] == "not_yet_adopted"
    assert result["activation_effect"] == "NONE"
    assert PRODUCER_EMISSION_ENABLED is False


def test_active_ce_payload_remains_legacy_and_carrier_free() -> None:
    run, _, _ = evaluation_run(ROOT)
    package = run["payload"]["builder_executable_package"]
    assert isinstance(package, dict)
    assert "continuation_assurance" not in package

    before = copy.deepcopy(package)
    observed = attach_to_builder_package_if_enabled(package)
    assert observed is package
    assert observed == before


def test_explicit_derivation_preserves_owner_confirmation_boundary() -> None:
    carrier = build_continuation_assurance(_package(), ROOT)
    assert carrier["source_stage"] == "CONSTRUCTABILITY_ENGINEER"
    assert carrier["claims"][0]["verification_state"] == "VERIFIED"
    assert carrier["claims"][1]["verification_state"] == "UNVERIFIED"
    assert carrier["effects"][0]["effect_class"] == "EXTERNAL_MUTATION"
    assert (
        carrier["effects"][0]["continuation_state"]
        == "AUTHORIZATION_REQUIRED"
    )
    assert carrier["effects"][0]["authorization_ref"] is None
    assert carrier["authorizations"] == []
    assert carrier["stage_summary"]["owner_projection"] == "YELLOW"
    assert (
        carrier["stage_summary"]["yellow_substate"]
        == "OWNER_CHOICE_REQUIRED"
    )


def test_derivation_is_stable_and_rejects_caller_carrier() -> None:
    first = build_continuation_assurance(_package(), ROOT)
    second = build_continuation_assurance(_package(), ROOT)
    assert first == second

    package = _package()
    package["continuation_assurance"] = first
    with pytest.raises(PCVPDormantProducerError, match="Caller-supplied"):
        attach_to_builder_package_if_enabled(package)


def test_non_ready_package_cannot_be_upgraded() -> None:
    package = _package()
    package["builder_package_status"] = "blocked"
    with pytest.raises(
        PCVPDormantProducerError,
        match="not deterministically Builder-ready",
    ):
        build_continuation_assurance(package, ROOT)
