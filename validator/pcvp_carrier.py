from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from . import _pcvp_carrier_impl as _impl
from .pcvp_identity import (
    ARCHITECTURE_LOCK_ID,
    CANONICAL_COMMIT,
    CANONICAL_REPOSITORY,
    POLICY_ID,
    POLICY_VERSION,
    PCVPIdentityError,
    load_pcvp_resources,
)

Diagnostic = _impl.Diagnostic
Severity = _impl.Severity
canonical_sha256 = _impl.canonical_sha256
diagnostic = _impl.diagnostic
load_json_file = _impl.load_json_file
sort_diagnostics = _impl.sort_diagnostics
PROFILE_SHA256 = _impl.PROFILE_SHA256
LOCK_PATH = _impl.LOCK_PATH
LOCK_SCHEMA_VERSION = _impl.LOCK_SCHEMA_VERSION
VENDORED_ROOT = _impl.VENDORED_ROOT
PROFILE_PATH = _impl.PROFILE_PATH
EXPECTED_SOURCE_STAGE = _impl.EXPECTED_SOURCE_STAGE
EXPECTED_CONSUMER_STAGE = _impl.EXPECTED_CONSUMER_STAGE
SCHEMA_NAMES = _impl.SCHEMA_NAMES


def _shared_identity_schema_loader(
    repository_root: Path,
) -> tuple[dict[str, dict[str, Any]] | None, list[Diagnostic]]:
    try:
        resources = load_pcvp_resources(repository_root)
    except PCVPIdentityError as exc:
        return None, [
            diagnostic(
                "CE_PCVP_CANONICAL_IDENTITY_MISMATCH",
                "error",
                str(exc),
                exc.path,
                expected=exc.expected,
                actual=exc.actual,
                validator_layer="CANONICAL_IDENTITY",
            )
        ]
    return copy.deepcopy(resources.schemas), []


# The legacy semantic checker remains the single mechanical carrier validator, but
# its resource loader is rebound to the shared fixed trust anchor. The former
# module-local mutable Lock digest path is therefore not an active authority.
_impl._load_pinned_schemas = _shared_identity_schema_loader
_load_pinned_schemas = _shared_identity_schema_loader
inspect_optional_pcvp_carrier = _impl.inspect_optional_pcvp_carrier


__all__ = [
    "ARCHITECTURE_LOCK_ID",
    "CANONICAL_COMMIT",
    "CANONICAL_REPOSITORY",
    "POLICY_ID",
    "POLICY_VERSION",
    "inspect_optional_pcvp_carrier",
]
