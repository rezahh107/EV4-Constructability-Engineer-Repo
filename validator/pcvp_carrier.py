from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


def _load_standalone_sibling(module_name: str, filename: str) -> ModuleType:
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    module_path = Path(__file__).resolve().with_name(filename)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load PCVP sibling module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


if __package__:
    from . import _pcvp_carrier_impl as _impl
    from .pcvp_identity import (
        ARCHITECT_PROFILE_SHA256,
        ARCHITECTURE_LOCK_ID,
        CANONICAL_COMMIT,
        CANONICAL_REPOSITORY,
        POLICY_ID,
        POLICY_VERSION,
        PCVPIdentityError,
        load_pcvp_resources,
    )
else:
    _impl = _load_standalone_sibling("_ce_pcvp_carrier_impl", "_pcvp_carrier_impl.py")
    _identity = _load_standalone_sibling("_ce_pcvp_identity", "pcvp_identity.py")
    ARCHITECT_PROFILE_SHA256 = _identity.ARCHITECT_PROFILE_SHA256
    ARCHITECTURE_LOCK_ID = _identity.ARCHITECTURE_LOCK_ID
    CANONICAL_COMMIT = _identity.CANONICAL_COMMIT
    CANONICAL_REPOSITORY = _identity.CANONICAL_REPOSITORY
    POLICY_ID = _identity.POLICY_ID
    POLICY_VERSION = _identity.POLICY_VERSION
    PCVPIdentityError = _identity.PCVPIdentityError
    load_pcvp_resources = _identity.load_pcvp_resources

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


def _identity_diagnostic(exc: PCVPIdentityError) -> Diagnostic:
    return diagnostic(
        "CE_PCVP_CANONICAL_IDENTITY_MISMATCH",
        "error",
        str(exc),
        exc.path,
        expected=exc.expected,
        actual=exc.actual,
        validator_layer="CANONICAL_IDENTITY",
    )


def _load_shared_resources(repository_root: Path) -> tuple[Any | None, list[Diagnostic]]:
    try:
        return load_pcvp_resources(repository_root), []
    except PCVPIdentityError as exc:
        return None, [_identity_diagnostic(exc)]


def _shared_identity_schema_loader(
    repository_root: Path,
) -> tuple[dict[str, dict[str, Any]] | None, list[Diagnostic]]:
    resources, diagnostics = _load_shared_resources(repository_root)
    if resources is None:
        return None, diagnostics
    return copy.deepcopy(resources.schemas), []


def _profile_preauthorization_diagnostics(
    artifact: dict[str, Any],
    resources: Any,
) -> list[Diagnostic]:
    continuation = artifact.get("continuation_assurance")
    if not isinstance(continuation, dict):
        return []

    authorizations = continuation.get("authorizations")
    effects = continuation.get("effects")
    if not isinstance(authorizations, list) or not isinstance(effects, list):
        return []

    profile_authorizations = [
        (index, item)
        for index, item in enumerate(authorizations)
        if isinstance(item, dict) and item.get("basis") == "PROFILE_PREAUTHORIZED"
    ]
    if not profile_authorizations:
        return []

    source_stage = continuation.get("source_stage")
    source_profile_document = resources.source_profiles.get(source_stage)
    if not isinstance(source_profile_document, dict):
        return [
            diagnostic(
                "CE_PCVP_SOURCE_PROFILE_IDENTITY_UNAVAILABLE",
                "error",
                "PROFILE_PREAUTHORIZED requires the byte-pinned canonical profile for the carrier source stage.",
                "$.continuation_assurance.source_stage",
                source_stage=source_stage,
                validator_layer="CANONICAL_PROFILE",
            )
        ]

    source_profile = source_profile_document.get("continuation_profile")
    if not isinstance(source_profile, dict) or source_profile.get("stage_id") != source_stage:
        return [
            diagnostic(
                "CE_PCVP_SOURCE_PROFILE_IDENTITY_UNAVAILABLE",
                "error",
                "The pinned source profile does not establish the carrier source-stage identity.",
                "$.continuation_assurance.source_stage",
                source_stage=source_stage,
                validator_layer="CANONICAL_PROFILE",
            )
        ]

    profile_entries = source_profile.get("preauthorized_effects")
    if not isinstance(profile_entries, list):
        return [
            diagnostic(
                "CE_PCVP_SOURCE_PROFILE_PREAUTH_AMBIGUOUS",
                "error",
                "The canonical source-stage profile does not provide a deterministic preauthorized Effect-class/Scope mapping.",
                "$.continuation_assurance.source_stage",
                source_stage=source_stage,
                source_profile_id=source_profile.get("profile_id"),
                validator_layer="CANONICAL_PROFILE",
            )
        ]

    profile_scope_by_class: dict[str, str] = {}
    for entry_index, entry in enumerate(profile_entries):
        effect_class = entry.get("effect_class") if isinstance(entry, dict) else None
        scope = entry.get("scope") if isinstance(entry, dict) else None
        if (
            not isinstance(effect_class, str)
            or not effect_class
            or not isinstance(scope, str)
            or not scope
            or effect_class in profile_scope_by_class
        ):
            return [
                diagnostic(
                    "CE_PCVP_SOURCE_PROFILE_PREAUTH_AMBIGUOUS",
                    "error",
                    "The canonical source-stage profile must map each preauthorized Effect class to exactly one canonical Scope.",
                    "$.continuation_assurance.source_stage",
                    source_stage=source_stage,
                    source_profile_id=source_profile.get("profile_id"),
                    profile_entry_index=entry_index,
                    effect_class=effect_class,
                    validator_layer="CANONICAL_PROFILE",
                )
            ]
        profile_scope_by_class[effect_class] = scope

    diagnostics: list[Diagnostic] = []
    profile_auth_by_id = {
        item.get("authorization_id"): (index, item)
        for index, item in profile_authorizations
        if isinstance(item.get("authorization_id"), str)
    }

    for authorization_index, authorization in profile_authorizations:
        claimed_classes = authorization.get("allowed_effect_classes")
        if not isinstance(claimed_classes, list):
            continue
        forbidden_classes = sorted(
            {
                item
                for item in claimed_classes
                if isinstance(item, str) and item not in profile_scope_by_class
            }
        )
        if forbidden_classes:
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_PROFILE_PREAUTHORIZED_AUTH_CLASS_FORBIDDEN",
                    "error",
                    "PROFILE_PREAUTHORIZED Authorization cannot claim Effect classes absent from the canonical source-stage profile.",
                    f"$.continuation_assurance.authorizations[{authorization_index}].allowed_effect_classes",
                    authorization_id=authorization.get("authorization_id"),
                    source_stage=source_stage,
                    source_profile_id=source_profile.get("profile_id"),
                    forbidden_effect_classes=forbidden_classes,
                    preauthorized_effect_classes=sorted(profile_scope_by_class),
                    validator_layer="CANONICAL_PROFILE",
                )
            )

    for effect_index, effect in enumerate(effects):
        if not isinstance(effect, dict):
            continue
        authorization_record = profile_auth_by_id.get(effect.get("authorization_ref"))
        if authorization_record is None:
            continue
        _, authorization = authorization_record
        effect_class = effect.get("effect_class")
        canonical_scope = profile_scope_by_class.get(effect_class)
        if canonical_scope is None:
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_PROFILE_PREAUTHORIZED_EFFECT_FORBIDDEN",
                    "error",
                    "PROFILE_PREAUTHORIZED cannot authorize an Effect class outside the canonical source-stage profile.",
                    f"$.continuation_assurance.effects[{effect_index}].effect_class",
                    effect_id=effect.get("effect_id"),
                    authorization_id=authorization.get("authorization_id"),
                    source_stage=source_stage,
                    source_profile_id=source_profile.get("profile_id"),
                    effect_class=effect_class,
                    preauthorized_effect_classes=sorted(profile_scope_by_class),
                    validator_layer="CANONICAL_PROFILE",
                )
            )
            continue

        effect_scope = effect.get("permitted_scope")
        authorization_scope = authorization.get("permitted_scope")
        if effect_scope != canonical_scope or authorization_scope != canonical_scope:
            diagnostics.append(
                diagnostic(
                    "CE_PCVP_PROFILE_PREAUTHORIZED_SCOPE_MISMATCH",
                    "error",
                    "PROFILE_PREAUTHORIZED Effect and Authorization Scope must exactly equal the canonical Scope for that Effect class.",
                    f"$.continuation_assurance.effects[{effect_index}].permitted_scope",
                    effect_id=effect.get("effect_id"),
                    authorization_id=authorization.get("authorization_id"),
                    source_stage=source_stage,
                    source_profile_id=source_profile.get("profile_id"),
                    effect_class=effect_class,
                    expected_scope=canonical_scope,
                    effect_scope=effect_scope,
                    authorization_scope=authorization_scope,
                    validator_layer="CANONICAL_PROFILE",
                )
            )

    return diagnostics


# The legacy semantic checker remains the single mechanical carrier validator, but
# its resource loader is rebound to the shared fixed trust anchor. The former
# module-local mutable Lock digest path is therefore not an active authority.
_impl._load_pinned_schemas = _shared_identity_schema_loader
_load_pinned_schemas = _shared_identity_schema_loader


def inspect_optional_pcvp_carrier(
    artifact: Any,
    repository_root: str | Path = ".",
) -> tuple[dict[str, Any], list[Diagnostic]]:
    projection, diagnostics = _impl.inspect_optional_pcvp_carrier(
        artifact,
        repository_root=repository_root,
    )
    if projection.get("status") != "validated" or any(
        item.severity == "error" for item in diagnostics
    ):
        return projection, diagnostics
    if not isinstance(artifact, dict):
        return projection, diagnostics

    resources, identity_diagnostics = _load_shared_resources(Path(repository_root))
    if resources is None:
        combined = sort_diagnostics([*diagnostics, *identity_diagnostics])
        return _impl._projection("invalid"), combined

    profile_diagnostics = _profile_preauthorization_diagnostics(artifact, resources)
    combined = sort_diagnostics([*diagnostics, *profile_diagnostics])
    if any(item.severity == "error" for item in combined):
        return _impl._projection("invalid"), combined
    return projection, combined


__all__ = [
    "ARCHITECT_PROFILE_SHA256",
    "ARCHITECTURE_LOCK_ID",
    "CANONICAL_COMMIT",
    "CANONICAL_REPOSITORY",
    "POLICY_ID",
    "POLICY_VERSION",
    "inspect_optional_pcvp_carrier",
]
