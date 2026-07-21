from __future__ import annotations

from typing import Any


def contains_synthetic_evidence(value: Any) -> bool:
    """Derive synthetic state from authoritative carried facts, not declarations."""
    if isinstance(value, dict):
        if value.get("synthetic") is True:
            return True
        if value.get("classification") == "synthetic":
            return True
        if value.get("state") == "synthetic":
            return True
        if value.get("fact_class") == "synthetic_fixture":
            return True
        if value.get("source_type") == "synthetic_fixture":
            return True
        if value.get("type") == "synthetic_fixture":
            return True
        return any(contains_synthetic_evidence(child) for child in value.values())
    if isinstance(value, list):
        return any(contains_synthetic_evidence(child) for child in value)
    return False


def derive_stage_bundle_synthetic(bundle: dict[str, Any]) -> bool:
    """Recompute Stage Bundle synthetic state while ignoring its declared flag."""
    return any(
        contains_synthetic_evidence(value)
        for key, value in bundle.items()
        if key != "synthetic"
    )
