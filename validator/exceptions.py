from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConstructabilityViolation:
    """Single fail-closed validator finding."""

    rule_id: str
    status: str
    message: str
    location: str = "document"


class ConstructabilityException(Exception):
    """Raised by strict callers when constructability validation fails."""

    def __init__(self, violations: list[ConstructabilityViolation]) -> None:
        self.violations = violations
        details = "; ".join(f"{v.rule_id}: {v.message}" for v in violations)
        super().__init__(f"Constructability validation failed: {details}")
