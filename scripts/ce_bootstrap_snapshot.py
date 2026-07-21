from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ce_bootstrap_validation import ValidationError, _reject_constant, _reject_duplicates, require


@dataclass(frozen=True)
class AttachmentSnapshot:
    path: Path
    value: dict[str, Any]
    raw_bytes: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.raw_bytes).hexdigest()


def strict_load_json_snapshot(path: Path) -> AttachmentSnapshot:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"file could not be read: {path}") from exc
    try:
        text = raw.decode("utf-8")
        value = json.loads(
            text,
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicates,
        )
    except UnicodeDecodeError as exc:
        raise ValidationError(f"file is not valid UTF-8: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}"
        ) from exc
    require(isinstance(value, dict), f"{path} must contain a JSON object")
    return AttachmentSnapshot(path=path, value=value, raw_bytes=raw)


def assert_snapshot_unchanged(snapshot: AttachmentSnapshot) -> None:
    try:
        observed = snapshot.path.read_bytes()
    except OSError as exc:
        raise ValidationError(f"file could not be re-read: {snapshot.path}") from exc
    if observed != snapshot.raw_bytes:
        raise ValidationError(f"attachment changed after exact-byte capture: {snapshot.path}")
