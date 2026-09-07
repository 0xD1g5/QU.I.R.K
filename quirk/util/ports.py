"""Canonical well-known-TLS-port constant for QU.I.R.K. — Phase 186 / TRIAGE-176-02.

This is the single canonical well-known-TLS-port set for QU.I.R.K. It is NOT
a scan-target list — that is `ScanCfg.ports_tls`, the list of ports the
scanner probes. This module exists because Phase 186 / TRIAGE-176-02 found
two divergent copies of this list (`quirk/interactive.py` and
`quirk/discovery/nmap_provider.py`) and `186-CONTEXT.md` D-08 forbids
introducing a third. Both call sites now import from here instead.

Public surface:
  WELL_KNOWN_TLS_PORTS: Tuple[int, ...]
"""
from __future__ import annotations

from typing import Tuple

WELL_KNOWN_TLS_PORTS: Tuple[int, ...] = (443, 8443, 9443, 10443, 4433, 5001)
