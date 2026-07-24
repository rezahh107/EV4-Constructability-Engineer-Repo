from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .artifact_fact_derivation import _compare, _regenerate
from .artifact_parse_formats import ArtifactAdapterError, _load_json_bytes


@dataclass(frozen=True)
class ArtifactBinding:
    claim_id: str
    subject_ref: str
    selected_candidate_id: str
    source_bundle_id: str
    intake_digest: str


def evaluate_artifact_source(
    *,
    claim_id: str,
    path: Path,
    semantics: Mapping[str, Any],
    binding: ArtifactBinding,
    cached_extract_path: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if claim_id not in {
        "geometry",
        "overlay_strategy",
        "ui_control_path",
        "asset_source",
    }:
        raise ArtifactAdapterError(f"No original-source adapter exists for {claim_id}")
    facts, parser_id, raw = _regenerate(path, claim_id, binding.subject_ref)
    _compare(claim_id, facts, semantics)
    cache_digest: str | None = None
    if cached_extract_path is not None:
        cache_raw = cached_extract_path.read_bytes()
        cached = _load_json_bytes(cache_raw)
        if cached != facts:
            raise ArtifactAdapterError(
                "Cached extract cannot be regenerated from the original source"
            )
        cache_digest = hashlib.sha256(cache_raw).hexdigest()
    metadata = {
        "adapter_id": parser_id,
        "schema_id": f"original-source:{path.suffix.casefold().lstrip('.')}",
        "source_bytes_sha256": hashlib.sha256(raw).hexdigest(),
        "source_role": "original_source",
        "selected_candidate_id": binding.selected_candidate_id,
        "source_bundle_id": binding.source_bundle_id,
        "intake_digest": binding.intake_digest,
        "cached_extract_sha256": cache_digest,
    }
    return dict(facts), metadata


__all__ = ["ArtifactAdapterError", "ArtifactBinding", "evaluate_artifact_source"]
