"""
opensearch_bridge.py — Log buffering and retry bridge to OpenSearch REST API.

QL services call post_event() to emit structured log events to the SIEM.
This module handles:
  - HTTP POST to OpenSearch _doc endpoint
  - Retry with exponential backoff if OpenSearch is temporarily unavailable
  - In-memory buffer: events queued locally during outage, flushed on reconnect
  - Index naming: qfl-events-YYYY.MM.DD (daily rolling)

Usage:
  from scripts.opensearch_bridge import SIEMBridge
  bridge = SIEMBridge()
  bridge.post_event({...})

Or as a standalone module imported by QL services via shared volume/path.
"""

import os
import json
import time
import uuid
import threading
import logging
from datetime import datetime, timezone
from collections import deque
from typing import Optional

import httpx

log = logging.getLogger(__name__)

SIEM_URL = os.getenv("SIEM_URL", "http://opensearch:9200")
SIEM_INDEX_PREFIX = os.getenv("SIEM_INDEX", "qfl-events")
MAX_BUFFER_SIZE = 500
RETRY_INTERVAL_S = 5
MAX_RETRY_S = 60


def _index_name() -> str:
    """Returns today's rolling index name: qfl-events-YYYY.MM.DD"""
    return f"{SIEM_INDEX_PREFIX}-{datetime.now(timezone.utc).strftime('%Y.%m.%d')}"


class SIEMBridge:
    """Thread-safe bridge for posting events to OpenSearch."""

    def __init__(self, siem_url: Optional[str] = None):
        self.siem_url = siem_url or SIEM_URL
        self._buffer: deque = deque(maxlen=MAX_BUFFER_SIZE)
        self._lock = threading.Lock()
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()

    def post_event(self, event: dict) -> bool:
        """
        Post a structured log event to the SIEM.
        Adds @timestamp, event_id if not present.
        Returns True if posted immediately, False if buffered for retry.
        """
        enriched = self._enrich(event)

        try:
            self._send(enriched)
            return True
        except Exception:
            with self._lock:
                self._buffer.append(enriched)
            return False

    def _enrich(self, event: dict) -> dict:
        """Add required fields if missing."""
        enriched = dict(event)
        if "@timestamp" not in enriched:
            enriched["@timestamp"] = datetime.now(timezone.utc).isoformat()
        if "event_id" not in enriched:
            enriched["event_id"] = str(uuid.uuid4())
        return enriched

    def _send(self, event: dict) -> None:
        """POST event to OpenSearch _doc endpoint. Raises on failure."""
        index = _index_name()
        url = f"{self.siem_url}/{index}/_doc"
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(url, json=event, headers={"Content-Type": "application/json"})
            resp.raise_for_status()

    def _flush_loop(self) -> None:
        """Background thread: retry buffered events with exponential backoff."""
        backoff = RETRY_INTERVAL_S
        while True:
            time.sleep(backoff)
            with self._lock:
                if not self._buffer:
                    backoff = RETRY_INTERVAL_S
                    continue
                batch = list(self._buffer)
                self._buffer.clear()

            failed = []
            for event in batch:
                try:
                    self._send(event)
                except Exception:
                    failed.append(event)

            if failed:
                with self._lock:
                    for event in failed:
                        self._buffer.appendleft(event)
                backoff = min(backoff * 2, MAX_RETRY_S)
                log.warning(f"SIEM bridge: {len(failed)} events re-buffered. Retry in {backoff}s.")
            else:
                backoff = RETRY_INTERVAL_S


# ─── Module-level singleton (used by QL services) ───────────────────────────
_bridge: Optional[SIEMBridge] = None


def get_bridge() -> SIEMBridge:
    global _bridge
    if _bridge is None:
        _bridge = SIEMBridge()
    return _bridge


def post_event(event: dict) -> bool:
    """Convenience function — post event via module-level bridge."""
    return get_bridge().post_event(event)
