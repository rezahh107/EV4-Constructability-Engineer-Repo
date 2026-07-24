from __future__ import annotations

from . import _verified_project_gate_exporter_impl as _impl


# Public CLI manifest retained in this module so the installed entry point and
# repository source-level contract expose the same explicit operator inputs.
OFFICIAL_CLI_OPTIONS = (
    "--review-draft",
    "--source-intake",
    "--source-bundle",
    "--output",
    "--repo-root",
    "--overwrite",
)

# The public Project Gate contract owns these validation identity values.
# The same verified exporter implementation remains authoritative; this facade
# only aligns its external envelope with producer-gate-export.v1.
_impl.VERIFIED_EXPORTER_ID = "ev4-producer-gate-export-validator"
_impl.VERIFIED_EXPORTER_VERSION = "1.0.0"

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)

VERIFIED_EXPORTER_ID = _impl.VERIFIED_EXPORTER_ID
VERIFIED_EXPORTER_VERSION = _impl.VERIFIED_EXPORTER_VERSION


if __name__ == "__main__":
    raise SystemExit(main())
