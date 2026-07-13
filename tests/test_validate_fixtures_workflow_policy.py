from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "validate-fixtures.yml"

ACTION_REFERENCE = re.compile(
    r"^[ \t]*-?[ \t]*uses:[ \t]*([^\s#]+)",
    re.MULTILINE,
)
IMMUTABLE_ACTION_REFERENCE = re.compile(
    r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$"
)

EXPECTED_ACTION_REFERENCES = {
    "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5",
    "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
    "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020",
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
}


def test_validate_fixtures_uses_only_immutable_action_shas() -> None:
    content = WORKFLOW.read_text(encoding="utf-8")
    references = ACTION_REFERENCE.findall(content)

    assert set(references) == EXPECTED_ACTION_REFERENCES
    assert all(IMMUTABLE_ACTION_REFERENCE.fullmatch(ref) for ref in references)
