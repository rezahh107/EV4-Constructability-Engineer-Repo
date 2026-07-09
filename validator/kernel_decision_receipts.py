from __future__ import annotations

from dataclasses import dataclass
from typing import Any

REQUIRED_TRACE_FIELDS = (
    "decision_family",
    "decision_card_ref",
    "selected_option",
    "rejected_options",
    "evidence_refs",
    "evidence_state",
    "consumer_stage",
)

SUCCESS_RECEIPT_TEXT = (
    "✅ تصمیم به decision card کرنل وصل است؛ CE فقط constructability آن را بررسی کرده "
    "و lineage تصمیم حفظ شده است."
)
WARNING_RECEIPT_TEXT = (
    "⚠️ این آیتم هنوز رسید معتبر کرنل ندارد؛ CE نمی‌تواند بدون machine-readable trace "
    "کامل آن را قابل‌عبور اعلام کند."
)

SUCCESS_STATUS = "kernel_trace_connected"
WARNING_STATUS = "insufficient_evidence"

DIAGNOSTIC_GREEN_WITHOUT_TRACE = "CE_RECEIPT_GREEN_WITHOUT_MACHINE_TRACE"
DIAGNOSTIC_WARNING_REQUIRED = "CE_RECEIPT_WARNING_REQUIRED"
DIAGNOSTIC_CE_PASS_WITHOUT_TRACE = "CE_RECEIPT_CE_PASS_WITHOUT_TRACE"

SUCCESS_STATUS_ALIASES = {
    "success",
    "valid",
    "passed",
    "accepted",
    "kernel_trace_connected",
    "trace_connected",
}
CE_PASS_STATUS_ALIASES = {
    "accepted",
    "builder_ready",
    "constructability_pass",
    "executable_ready",
    "passed",
}


@dataclass(frozen=True)
class ReceiptDiagnostic:
    code: str
    path: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def missing_machine_trace_fields(trace: Any) -> list[str]:
    if not isinstance(trace, dict):
        return list(REQUIRED_TRACE_FIELDS)

    missing: list[str] = []
    for field in REQUIRED_TRACE_FIELDS:
        if field not in trace:
            missing.append(field)

    for field in ("decision_family", "decision_card_ref", "selected_option", "consumer_stage"):
        if field in trace and not _is_nonempty_string(trace.get(field)):
            missing.append(field)

    rejected_options = trace.get("rejected_options")
    if "rejected_options" in trace and not isinstance(rejected_options, list):
        missing.append("rejected_options")

    evidence_refs = trace.get("evidence_refs")
    if "evidence_refs" in trace:
        refs_valid = (
            isinstance(evidence_refs, list)
            and bool(evidence_refs)
            and all(_is_nonempty_string(ref) for ref in evidence_refs)
        )
        if not refs_valid:
            missing.append("evidence_refs")

    if trace.get("evidence_state") == "insufficient_evidence":
        missing.append("evidence_state")

    return sorted(set(missing), key=REQUIRED_TRACE_FIELDS.index)


def has_complete_machine_trace(surface: Any) -> bool:
    if not isinstance(surface, dict):
        return False
    lineage = surface.get("decision_lineage")
    if not isinstance(lineage, list):
        return False
    return any(not missing_machine_trace_fields(entry) for entry in lineage)


def render_ce_kernel_decision_receipt(surface: Any) -> dict[str, str]:
    if has_complete_machine_trace(surface):
        return {
            "visible_status_marker": "✅",
            "status": SUCCESS_STATUS,
            "message": SUCCESS_RECEIPT_TEXT,
            "source": "machine_readable_decision_trace",
        }

    return {
        "visible_status_marker": "⚠️",
        "status": WARNING_STATUS,
        "message": WARNING_RECEIPT_TEXT,
        "source": "insufficient_machine_readable_decision_trace",
    }


def _receipt_text(receipt: Any) -> str:
    if isinstance(receipt, str):
        return receipt
    if isinstance(receipt, dict):
        parts = [
            receipt.get("visible_status_marker"),
            receipt.get("status"),
            receipt.get("message"),
            receipt.get("statement"),
        ]
        return " ".join(part for part in parts if isinstance(part, str))
    return ""


def _receipt_status(receipt: Any) -> str:
    if isinstance(receipt, dict) and isinstance(receipt.get("status"), str):
        return receipt["status"].strip()
    return ""


def _is_success_receipt(receipt: Any) -> bool:
    status = _receipt_status(receipt)
    text = _receipt_text(receipt)
    return status in SUCCESS_STATUS_ALIASES or "✅" in text or SUCCESS_RECEIPT_TEXT in text


def _is_warning_receipt(receipt: Any) -> bool:
    status = _receipt_status(receipt)
    text = _receipt_text(receipt)
    return status == WARNING_STATUS or "⚠️" in text or WARNING_RECEIPT_TEXT in text


def _surface_claims_ce_pass(surface: dict[str, Any]) -> bool:
    direct_values = (
        surface.get("status"),
        surface.get("constructability_status"),
        surface.get("builder_package_status"),
    )
    for value in direct_values:
        if isinstance(value, str) and value.strip() in CE_PASS_STATUS_ALIASES:
            return True

    review = surface.get("constructability_review")
    if isinstance(review, dict):
        status = review.get("constructability_status")
        if isinstance(status, str) and status.strip() in CE_PASS_STATUS_ALIASES:
            return True

    return surface.get("builder_package_emitted") is True


def validate_receipt_surface(surface: Any, path: str) -> list[ReceiptDiagnostic]:
    if not isinstance(surface, dict):
        return []

    receipt = surface.get("kernel_decision_receipt")
    complete_trace = has_complete_machine_trace(surface)
    diagnostics: list[ReceiptDiagnostic] = []

    if receipt is not None and _is_success_receipt(receipt) and not complete_trace:
        diagnostics.append(
            ReceiptDiagnostic(
                DIAGNOSTIC_GREEN_WITHOUT_TRACE,
                f"{path}.kernel_decision_receipt",
                "Success receipt requires a complete machine-readable Kernel decision trace.",
            )
        )

    if receipt is not None and not complete_trace and not _is_warning_receipt(receipt):
        diagnostics.append(
            ReceiptDiagnostic(
                DIAGNOSTIC_WARNING_REQUIRED,
                f"{path}.kernel_decision_receipt",
                "Incomplete or missing trace must render the insufficient-evidence warning.",
            )
        )

    if _surface_claims_ce_pass(surface) and not complete_trace:
        diagnostics.append(
            ReceiptDiagnostic(
                DIAGNOSTIC_CE_PASS_WITHOUT_TRACE,
                path,
                "CE constructability pass or Builder-ready wording requires a complete trace.",
            )
        )

    return diagnostics


SURFACE_KEYS = (
    "ce_intake",
    "ce_output",
    "constructability_report",
    "constructability_review",
    "repair_request",
    "repair_handoff",
    "handoff",
    "builder_handoff",
)


def validate_receipt_document(document: Any) -> list[ReceiptDiagnostic]:
    if not isinstance(document, dict):
        return [
            ReceiptDiagnostic(
                DIAGNOSTIC_WARNING_REQUIRED,
                "$",
                "Receipt validation expects a JSON/YAML object.",
            )
        ]

    diagnostics: list[ReceiptDiagnostic] = []
    if "kernel_decision_receipt" in document or "decision_lineage" in document:
        diagnostics.extend(validate_receipt_surface(document, "$"))

    for key in SURFACE_KEYS:
        value = document.get(key)
        if isinstance(value, dict):
            diagnostics.extend(validate_receipt_surface(value, f"$.{key}"))

    items = document.get("items")
    if isinstance(items, list):
        for index, item in enumerate(items):
            diagnostics.extend(validate_receipt_surface(item, f"$.items[{index}]"))

    return diagnostics
