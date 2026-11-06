"""Single source of truth for external scanner binaries (Phase 235.1 D-05/D-08).

Shared by ``run_scan.py`` (the missing-binary skip gate) and, in a later plan,
``quirk/cli/doctor_cmd.py`` so the two cannot drift apart. Hand-maintained
parallel lists of sites have drifted repeatedly in this project; derive from
this table instead of re-declaring binary names or INSTALL codes elsewhere.
"""
from __future__ import annotations

from typing import Dict, NamedTuple


class ScannerBinary(NamedTuple):
    binary: str
    error_code: str
    enable_attr: str
    targets_attr: str
    phase_name: str
    scanner_label: str
    domain_label: str


SCANNER_BINARIES: Dict[str, ScannerBinary] = {
    "semgrep": ScannerBinary(
        "semgrep", "INSTALL-008", "enable_source", "source_targets",
        "source_scanning", "source_scanner", "Source Code",
    ),
    "syft": ScannerBinary(
        "syft", "INSTALL-007", "enable_container", "container_targets",
        "container_scanning", "container_scanner", "Container",
    ),
}
