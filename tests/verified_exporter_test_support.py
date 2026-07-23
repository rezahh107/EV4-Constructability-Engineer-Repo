from __future__ import annotations

import copy
from pathlib import Path

import validator.verified_project_gate_exporter as verified_exporter
from exporter_test_support import _provenance, _real_source_pair, _write_json


def _draft(intake_path: Path, *, claims: list[dict] | None = None) -> dict:
    return {
        "schema_id": "ev4-ce-review-draft@1.0.0",
        "review_id": "CRR-VERIFIED-001",
        "reviewer_identity": "ce-test-reviewer",
        "source_intake_ref": str(intake_path),
        "reviewed_nodes": [
            {
                "node_id": "node-root",
                "node_type": "section_root",
                "proposed_action": "preserve approved structure",
                "engineering_rationale": "Derive a bounded CE implementation strategy from explicit premises.",
                "requested_claims": copy.deepcopy(claims or []),
                "candidate_source_refs": [],
                "claim_semantics": {},
                "assumptions": ["The accepted Architect structure remains unchanged."],
                "limitations": [],
                "reversible_if_wrong": True,
                "requires_class_change": False,
                "requires_structure_change": False,
                "architect_decomposition_permission": False,
            }
        ],
        "implementation_strategy_proposal": {
            "strategy_map_id": "ISM-VERIFIED-001",
            "strategies": [
                {
                    "strategy_id": "STR-VERIFIED-001",
                    "node_id": "node-root",
                    "strategy_selected": "preserve-approved-structure",
                    "alternatives_considered": [],
                    "rationale": "Accepted architecture identity is preserved.",
                    "evidence_source": "architect_package",
                    "class_names_affected": [],
                }
            ],
        },
        "builder_action_proposals": [
            {
                "action_id": "ACTION-VERIFIED-001",
                "action_type": "create_element",
                "target_node": "node-root",
                "parameters": {"element_type": "Container"},
            }
        ],
        "unresolved_questions": [],
        "downstream_test_obligations": [],
    }


def _geometry_draft(intake_path: Path) -> dict:
    draft = _draft(
        intake_path,
        claims=[{"claim_id": "geometry", "required": True}],
    )
    node = draft["reviewed_nodes"][0]
    node["claim_semantics"] = {
        "geometry": {
            "anchor_model": {"root": "node-root"},
            "coordinate_or_layout_model": "normal-flow flex container",
            "derivation_method": "bounded CE layout derivation",
        }
    }
    return draft


def _write_verified_inputs(tmp_path: Path, *, geometry: bool = False):
    verified_exporter.inspect_git_provenance = (
        lambda repo_root, ignored_paths=(): _provenance(dirty=False)
    )
    intake, source, intake_path, source_path = _real_source_pair(tmp_path)
    draft = _geometry_draft(intake_path) if geometry else _draft(intake_path)
    draft_path = _write_json(tmp_path / "ce-review-draft.json", draft)
    return intake, source, intake_path, source_path, draft, draft_path


__all__ = ["_draft", "_geometry_draft", "_provenance", "_write_verified_inputs"]
