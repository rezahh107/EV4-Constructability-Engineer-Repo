from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = (
    ROOT / ".github" / "workflows" / "validate-ce-bootstrap.yml",
    ROOT / ".github" / "workflows" / "validate-fixtures.yml",
)

ACTION_REFERENCE = re.compile(
    r"^[ \t]*-?[ \t]*uses:[ \t]*([^\s#]+)",
    re.MULTILINE,
)
IMMUTABLE_ACTION_REFERENCE = re.compile(
    r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$"
)

EXPECTED_ACTIONS = {
    "validate-ce-bootstrap.yml": {
        "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
    },
    "validate-fixtures.yml": {
        "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020",
    },
}


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda path: path.name)
def test_pr_correctness_workflows_use_only_immutable_action_shas(
    workflow: Path,
) -> None:
    content = workflow.read_text(encoding="utf-8")
    references = ACTION_REFERENCE.findall(content)
    assert set(references) == EXPECTED_ACTIONS[workflow.name]
    assert all(IMMUTABLE_ACTION_REFERENCE.fullmatch(ref) for ref in references)


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda path: path.name)
def test_pr_correctness_workflows_checkout_and_assert_exact_head(
    workflow: Path,
) -> None:
    content = workflow.read_text(encoding="utf-8")
    assert "name: Checkout exact PR head" in content
    assert "ref: ${{ github.event.pull_request.head.sha }}" in content
    assert "persist-credentials: false" in content
    assert "name: Assert exact PR-head identity" in content
    assert "EXPECTED_HEAD_SHA: ${{ github.event.pull_request.head.sha }}" in content
    assert 'TESTED_SHA="$(git rev-parse HEAD)"' in content
    assert 'test "$TESTED_SHA" = "$EXPECTED_HEAD_SHA"' in content
    assert "tested_pr_head=%s" in content


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda path: path.name)
def test_pr_correctness_workflows_do_not_generate_governance_evidence(
    workflow: Path,
) -> None:
    content = workflow.read_text(encoding="utf-8").casefold()
    forbidden = (
        "upload-artifact",
        "exact-head-validation-receipt",
        "ce-bootstrap-exact-head-receipt",
        ".governance-evidence",
        "validate-ai-governance.py",
        "governance-gate-evidence",
        "completion-receipt",
    )
    for token in forbidden:
        assert token not in content


def test_workflows_remain_correctness_focused() -> None:
    runtime = WORKFLOWS[0].read_text(encoding="utf-8")
    fixtures = WORKFLOWS[1].read_text(encoding="utf-8")
    assert "python scripts/check-ce-bootstrap.py" in runtime
    assert "tests/test_ce_runtime_balanced_repairs.py" in runtime
    assert "tests/test_ce_validation_transaction.py" in runtime
    assert "pytest -q" in runtime
    assert "pytest -q" in fixtures
    assert "validate-ce-architect-stage-intake.py" in fixtures
    assert "test:reference-paradigm-lock" in fixtures
