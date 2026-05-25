"""quirk.ticketing — Ticketing fan-out package (Phase 104 TICKET-01/03/04).

Public re-exports (Plan 02 — ABC + config + JiraChannel):
  TicketingChannel        — ABC (TICKET-04)
  TicketingCfg            — config dataclass
  load_ticketing_config   — config loader
  JiraChannel             — Jira backend (TICKET-01/03); lazy-imports jira at __init__ time

Note: importing JiraChannel from here does NOT trigger the jira import — the lazy
`from jira import JIRA` only runs when JiraChannel(...) is instantiated.
"""
from __future__ import annotations

from quirk.ticketing.base import TicketingChannel
from quirk.ticketing.config import TicketingCfg, load_ticketing_config
from quirk.ticketing.jira import JiraChannel

__all__ = [
    "TicketingChannel",
    "TicketingCfg",
    "load_ticketing_config",
    "JiraChannel",
]
