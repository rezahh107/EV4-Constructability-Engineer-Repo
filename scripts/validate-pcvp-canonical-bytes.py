from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from validator.pcvp_identity import DESCRIPTOR


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--canonical-root", type=Path, required=True)
    args = parser.parse_args()

    local_root = args.repository_root.resolve()
    canonical_root = args.canonical_root.resolve()
    pairs = [
        (
            local_root / DESCRIPTOR.local_profile_path,
            canonical_root / DESCRIPTOR.canonical_profile_path,
            DESCRIPTOR.profile_sha256,
        )
    ]
    pairs.extend(
        (
            local_root / item.local_path,
            canonical_root / item.canonical_path,
            item.sha256,
        )
        for item in DESCRIPTOR.source_profiles
    )
    pairs.extend(
        (
            local_root / DESCRIPTOR.local_schema_root / item.name,
            canonical_root / DESCRIPTOR.canonical_schema_root / item.name,
            item.sha256,
        )
        for item in DESCRIPTOR.schema_files
    )

    for local_path, canonical_path, expected_digest in pairs:
        local_bytes = local_path.read_bytes()
        canonical_bytes = canonical_path.read_bytes()
        if local_bytes != canonical_bytes:
            raise SystemExit(
                f"PCVP byte mismatch: {local_path} != {canonical_path}"
            )
        local_digest = _sha256(local_path)
        canonical_digest = _sha256(canonical_path)
        if local_digest != expected_digest or canonical_digest != expected_digest:
            raise SystemExit(
                "PCVP digest mismatch: "
                f"{local_path}={local_digest}, {canonical_path}={canonical_digest}, "
                f"expected={expected_digest}"
            )
        print(f"MATCH {local_path} {expected_digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
