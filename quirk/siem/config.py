"""quirk.siem.config — SIEM configuration loader (Phase 103 SIEM-01).

Resolves the QUIRK config YAML (via QUIRK_CONFIG_PATH env var or an explicit
path arg), reads the [siem] sub-block, and returns a SiemCfg.

CRITICAL CONSTRAINT (Pitfall 2):
  The scheduler's --config is a SQLite .db path, NOT a YAML file.  This loader
  MUST resolve the YAML config via QUIRK_CONFIG_PATH (or an explicit path),
  never via the scheduler DB-path argument plumbed from _dispatch_schedule.  If a
  binary/non-YAML file is encountered the function silently returns None so
  SIEM export failure never aborts a running scan.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import yaml


# ---------------------------------------------------------------------------
# Dataclass — flat fields, no nested sub-configs
# ---------------------------------------------------------------------------


@dataclass
class SiemCfg:
    """SIEM export configuration (loaded from the [siem] YAML block).

    host             — syslog receiver hostname or IP address (required)
    port             — syslog receiver port (default: 514)
    protocol         — "udp" or "tcp", lowercased at load time (default: "udp")
    export_after_scan — when True, push findings after every scheduled scan
    timeout_seconds  — socket timeout for each send attempt (default: 5)
    """

    host: str
    port: int = 514
    protocol: str = "udp"            # "udp" (default) or "tcp"
    export_after_scan: bool = False
    timeout_seconds: int = 5


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _parse_siem_cfg(raw: dict) -> SiemCfg:
    """Construct SiemCfg from the raw [siem] dict.

    All fields default gracefully when absent from the YAML.
    """
    return SiemCfg(
        host=str(raw.get("host", "")),
        port=int(raw.get("port", 514)),
        protocol=str(raw.get("protocol", "udp")).lower(),
        export_after_scan=bool(raw.get("export_after_scan", False)),
        timeout_seconds=int(raw.get("timeout_seconds", 5)),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_siem_config(path: str | None = None) -> "SiemCfg | None":
    """Load the [siem] block from the QUIRK YAML config.

    Priority: explicit path > QUIRK_CONFIG_PATH env var > None (disabled).

    Returns None when:
    - No path is resolvable (SIEM disabled — not an error).
    - The file does not exist.
    - The file is not valid YAML (e.g. a SQLite .db file — Pitfall 2).
    - The YAML has no [siem] top-level key.

    SIEM config failure MUST NEVER abort a running scan.  The scheduler calls
    this function with NO arguments — it must NEVER be called with the
    scheduler's --config SQLite DB path argument.
    """
    effective_path = path or os.environ.get("QUIRK_CONFIG_PATH")
    if not effective_path or not os.path.isfile(effective_path):
        return None
    try:
        with open(effective_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        siem_raw = (raw or {}).get("siem")
        if not siem_raw:
            return None
        return _parse_siem_cfg(siem_raw)
    except Exception:
        # Binary / malformed / non-YAML files (Pitfall 2) return None silently.
        return None
