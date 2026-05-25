"""quirk.ticketing — Ticketing fan-out package (Phase 104 TICKET-01/03/04).

Public re-exports (Plan 01 — ABC + config only):
  TicketingChannel        — ABC (TICKET-04)
  TicketingCfg            — config dataclass
  load_ticketing_config   — config loader

Note: JiraChannel is added by Plan 02. Do NOT import jira.py here.
"""
from __future__ import annotations

from quirk.ticketing.base import TicketingChannel
from quirk.ticketing.config import TicketingCfg, load_ticketing_config

__all__ = [
    "TicketingChannel",
    "TicketingCfg",
    "load_ticketing_config",
]
