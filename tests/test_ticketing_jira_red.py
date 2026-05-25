"""RED phase: minimal failing test asserting JiraChannel exists in quirk.ticketing.jira.

This file is the TDD gate for Task 1 (jira.py) — it MUST fail before jira.py is created.
"""
from quirk.ticketing.jira import JiraChannel  # noqa: F401 — import existence check
