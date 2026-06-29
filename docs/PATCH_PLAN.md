# Patch Plan

## PATCH-001 Fail-Closed Core

Implemented in this branch:

- Python project scaffold
- JSON schemas
- validation engine
- fail-closed rules
- fixtures
- connector regression fixture
- pytest tests
- GitHub Actions workflow

## PATCH-002 Report Quality Validation

Next:

- separate valid non-executable reviews from invalid executable-ready packages
- add report-only validation mode
- add fixtures for evidence-request and amendment-request outputs

## PATCH-003 Builder Contract Integration

Next:

- align Builder intake with Builder Executable Package
- enforce structured confirmation handoff
- lock selected_candidate_id and approved class names across repo boundary
