from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Any, Callable

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "check-ce-bootstrap.py"

spec = importlib.util.spec_from_file_location("check_ce_bootstrap", VALIDATOR_PATH)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
sys.modules["check_ce_bootstrap"] = validator
spec.loader.exec_module(validator)

MANIFEST_PATH = Path("manifests/ce-conversation-bootstrap.v1.json")
SCHEMA_PATH = Path("schemas/ce-conversation-bootstrap.v1.schema.json")
PROJECT_INSTRUCTIONS_PATH = Path(
    "release/EV4_CE_PROJECT_RELEASE_PACK_v1/PROJECT_INSTRUCTIONS.md"
)
FIRST_RUN_PATH = Path(
    "release/EV4_CE_PROJECT_RELEASE_PACK_v1/EV4_FIRST_RUN_GUIDE.md"
)
VALID_INPUT = REPO_ROOT / (
    "fixtures/architect-stage-intake-v1-1/valid/"
    "project-gate-transition-complete.v1_1.json"
)
INSUFFICIENT_INPUT = REPO_ROOT / (
    "fixtures/architect-stage-intake-v1-1/insufficient-evidence/"
    "project-gate-transition-insufficient.v1_1.json"
)
LEGACY_INPUT = REPO_ROOT / (
    "fixtures/architect-stage-intake/valid/minimal-canonical-intake.v1.json"
)
SOURCE_BUNDLE_FIXTURE = REPO_ROOT / (
    "fixtures/architect-stage-intake-v1-1/source-bundles/"
    "synthetic-architect-stage-bundle.v1.json"
)

CONTROLLED_PATHS = (
    Path("AGENTS.md"),
    Path("README.md"),
    Path("STATUS.md"),
    MANIFEST_PATH,
    Path("manifests/ce_pipeline_manifest.v1.json"),
    SCHEMA_PATH,
    Path("schemas/ce_architect_stage_intake.v1.schema.json"),
    Path("schemas/ce_architect_stage_intake.v1_1.schema.json"),
    Path("scripts/validate-ce-architect-stage-intake.py"),
    PROJECT_INSTRUCTIONS_PATH,
    FIRST_RUN_PATH,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(tmp_path: Path, name: str, value: Any) -> Path:
    path = tmp_path / name
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    return path


def valid_input_value() -> dict[str, Any]:
    return load_json(VALID_INPUT)


def insufficient_input_value() -> dict[str, Any]:
    return load_json(INSUFFICIENT_INPUT)


def legacy_input_value() -> dict[str, Any]:
    return load_json(LEGACY_INPUT)


def source_bundle_wrapper() -> dict[str, Any]:
    return load_json(SOURCE_BUNDLE_FIXTURE)


def source_bundle_value() -> dict[str, Any]:
    return copy.deepcopy(source_bundle_wrapper()["source_bundle"])


def receipt_value(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": "project-gate-a2c-receipt.v1",
        "transition": {
            "id": "ev4-architect-to-ce-transition",
            "version": "1.0.0",
        },
        "source_bundle_id": "synthetic-architect-bundle-001",
        "handoff_allowed": True,
    }
    value.update(overrides)
    return value


def request(
    message: str,
    attachments: list[Path] | tuple[Path, ...] = (),
    *,
    operating_mode: str = "auto",
    active_ce_run: bool = False,
) -> validator.RoutingRequest:
    return validator.RoutingRequest(
        message=message,
        operating_mode=operating_mode,
        active_ce_run=active_ce_run,
        attachments=tuple(attachments),
    )


def route(
    message: str,
    attachments: list[Path] | tuple[Path, ...] = (),
    *,
    operating_mode: str = "auto",
    active_ce_run: bool = False,
) -> dict[str, Any]:
    return validator.route_request(
        REPO_ROOT,
        request(
            message,
            attachments,
            operating_mode=operating_mode,
            active_ce_run=active_ce_run,
        ),
    )


def assert_explicit_result(result: dict[str, Any]) -> None:
    for field in (
        "activation_authorized",
        "operating_mode",
        "route",
        "pipeline_execution",
        "authorization_reason",
        "case_id",
    ):
        assert field in result


def valid_pair(tmp_path: Path) -> tuple[Path, Path]:
    intake = write_json(tmp_path, "ce-input.json", valid_input_value())
    source = write_json(tmp_path, "architect-source-bundle.json", source_bundle_wrapper())
    return intake, source
