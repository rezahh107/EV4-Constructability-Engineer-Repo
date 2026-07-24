from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Any, Mapping


class ArtifactAdapterError(ValueError):
    """Raised when original-source facts cannot be derived deterministically."""

class _StrictObject(dict[str, Any]):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> _StrictObject:
    result: _StrictObject = _StrictObject()
    for key, value in pairs:
        if key in result:
            raise ArtifactAdapterError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ArtifactAdapterError(f"Non-finite JSON number is forbidden: {value}")


def _load_json_bytes(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except UnicodeDecodeError as exc:
        raise ArtifactAdapterError("Original JSON source is not UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ArtifactAdapterError(f"Original JSON source is invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise ArtifactAdapterError("Original JSON source must have an object root")
    if (
        "facts" in value
        or str(value.get("schema_id") or "").startswith("ev4-ce-")
        and "extract" in str(value.get("schema_id"))
    ):
        raise ArtifactAdapterError(
            "Pre-authored facts/extract envelopes are declarations, not original-source evidence"
        )
    return dict(value)


def _find_json_subject(value: Any, subject_ref: str) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        if (
            value.get("node_id") == subject_ref
            or value.get("id") == subject_ref
            or value.get("subject_ref") == subject_ref
        ):
            return dict(value)
        for child in value.values():
            found = _find_json_subject(child, subject_ref)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_json_subject(child, subject_ref)
            if found is not None:
                return found
    return None


def _style_map(value: str | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in (value or "").split(";"):
        if ":" not in item:
            continue
        key, raw = item.split(":", 1)
        if key.strip() and raw.strip():
            result[key.strip().casefold()] = raw.strip()
    return result


class _HTMLSourceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str | None] = []
        self.records: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {str(key): value for key, value in attrs}
        identifier = attributes.get("id") or attributes.get("data-node-id")
        parent = next((value for value in reversed(self.stack) if value), None)
        self.records.append(
            {
                "tag": tag,
                "id": identifier,
                "parent_id": parent,
                "attrs": attributes,
                "style": _style_map(attributes.get("style")),
            }
        )
        self.stack.append(identifier)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        del tag
        if self.stack:
            self.stack.pop()


def _html_records(raw: bytes) -> list[dict[str, Any]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ArtifactAdapterError("Original HTML source is not UTF-8") from exc
    parser = _HTMLSourceParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:
        raise ArtifactAdapterError(f"Original HTML source could not be parsed: {exc}") from exc
    return parser.records


def _css_records(raw: bytes) -> list[dict[str, Any]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ArtifactAdapterError("Original CSS source is not UTF-8") from exc
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    records: list[dict[str, Any]] = []
    for selector_text, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
        declarations: dict[str, str] = {}
        for item in body.split(";"):
            if ":" not in item:
                continue
            key, value = item.split(":", 1)
            if key.strip() and value.strip():
                declarations[key.strip().casefold()] = value.strip()
        for selector in selector_text.split(","):
            if selector.strip():
                records.append({"selector": selector.strip(), "style": declarations})
    if not records:
        raise ArtifactAdapterError("Original CSS source contains no parseable rules")
    return records


def _svg_records(raw: bytes) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ArtifactAdapterError(f"Original SVG source is invalid: {exc}") from exc
    result: list[dict[str, Any]] = []

    def walk(element: ET.Element, parent_id: str | None) -> None:
        identifier = element.attrib.get("id") or element.attrib.get("data-node-id")
        result.append(
            {
                "tag": element.tag.rsplit("}", 1)[-1],
                "id": identifier,
                "parent_id": parent_id,
                "attrs": dict(element.attrib),
                "style": _style_map(element.attrib.get("style")),
            }
        )
        for child in list(element):
            walk(child, identifier or parent_id)

    walk(root, None)
    return result


def _subject_selector_matches(selector: str, subject_ref: str) -> bool:
    escaped = re.escape(subject_ref)
    return bool(
        re.search(rf"#{escaped}(?![\w-])", selector)
        or re.search(rf"\[data-node-id\s*=\s*['\"]?{escaped}['\"]?\]", selector)
    )


