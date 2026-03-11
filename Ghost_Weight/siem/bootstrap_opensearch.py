"""
bootstrap_opensearch.py — Configure OpenSearch + OpenDashboards for Operation Ghost Wait.

Run once after OpenSearch is healthy. Safe to re-run (idempotent).

Actions:
  1. Create index template for qfl-events-* with full field mapping
  2. Load alerting monitors from siem/pipeline_rules/ JSON files
  3. Import OpenDashboards dashboard from siem/dashboards/ .ndjson file
  4. Create index pattern in OpenDashboards: qfl-events-*

Usage:
  python3 siem/bootstrap_opensearch.py
  OR: called from scripts/bootstrap.sh
"""

import os
import sys
import json
import time
import glob
import logging

import httpx

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
DASHBOARDS_URL = os.getenv("SIEM_UI_URL", "http://localhost:5601")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_RULES_DIR = os.path.join(SCRIPT_DIR, "pipeline_rules")
DASHBOARDS_DIR = os.path.join(SCRIPT_DIR, "dashboards")

# ─── Index Template ──────────────────────────────────────────────────────────

INDEX_TEMPLATE = {
    "index_patterns": ["qfl-events-*"],
    "template": {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "refresh_interval": "5s"
        },
        "mappings": {
            "properties": {
                "@timestamp":        {"type": "date"},
                "event_id":          {"type": "keyword"},
                "service":           {"type": "keyword"},
                "atlas_phase":       {"type": "integer"},
                "atlas_technique":   {"type": "keyword"},
                "event_type":        {"type": "keyword"},
                "severity":          {"type": "keyword"},
                "session_id":        {"type": "keyword"},
                "agent_id":          {"type": "keyword"},
                "user_id":           {"type": "keyword"},
                "transaction_id":    {"type": "keyword"},
                "document_id":       {"type": "keyword"},
                "message":           {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "llm_action_taken":  {"type": "keyword"},
                "llm_completion":    {"type": "text"},
                "risk_score":        {"type": "float"},
                "risk_score_delta":  {"type": "float"},
                "score_before":      {"type": "float"},
                "score_after":       {"type": "float"},
                "memory_keys_used":  {"type": "keyword"},
                "tokens_in":         {"type": "integer"},
                "tokens_out":        {"type": "integer"},
                "latency_ms":        {"type": "integer"},
                "chunk_count":       {"type": "integer"},
                "retrieval_score":   {"type": "float"},
                "trust_token":       {"type": "keyword"},
                "source_agent":      {"type": "keyword"},
                "target_agent":      {"type": "keyword"},
            }
        }
    }
}


def wait_for_opensearch(timeout: int = 60) -> bool:
    """Poll OpenSearch cluster health until green/yellow or timeout."""
    log.info(f"Waiting for OpenSearch at {OPENSEARCH_URL}...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = httpx.get(f"{OPENSEARCH_URL}/_cluster/health", timeout=5)
            status = resp.json().get("status", "")
            if status in ("green", "yellow"):
                log.info(f"OpenSearch ready (status: {status})")
                return True
        except Exception:
            pass
        time.sleep(3)
        print(".", end="", flush=True)
    print()
    return False


def create_index_template(client: httpx.Client) -> bool:
    """Create or update qfl-events-* index template."""
    resp = client.put(
        f"{OPENSEARCH_URL}/_index_template/qfl-events",
        json=INDEX_TEMPLATE,
        headers={"Content-Type": "application/json"}
    )
    if resp.is_success:
        log.info("Index template 'qfl-events' created/updated")
        return True
    else:
        log.error(f"Failed to create index template: {resp.status_code} {resp.text}")
        return False


def load_alerting_monitors(client: httpx.Client) -> int:
    """Load alerting monitors from pipeline_rules/*.json. Returns count loaded."""
    monitor_files = sorted(glob.glob(os.path.join(PIPELINE_RULES_DIR, "monitor_*.json")))
    loaded = 0
    for f in monitor_files:
        with open(f) as fh:
            monitor = json.load(fh)
        # Check if monitor already exists (by name)
        name = monitor.get("name", os.path.basename(f))
        search_resp = client.post(
            f"{OPENSEARCH_URL}/_plugins/_alerting/monitors/_search",
            json={"query": {"term": {"monitor.name": name}}},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        existing_id = None
        if search_resp.is_success:
            hits = search_resp.json().get("hits", {}).get("hits", [])
            if hits:
                existing_id = hits[0]["_id"]

        if existing_id:
            # Update existing
            resp = client.put(
                f"{OPENSEARCH_URL}/_plugins/_alerting/monitors/{existing_id}",
                json=monitor,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
        else:
            # Create new
            resp = client.post(
                f"{OPENSEARCH_URL}/_plugins/_alerting/monitors",
                json=monitor,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

        if resp.is_success:
            log.info(f"Monitor loaded: {name}")
            loaded += 1
        else:
            log.warning(f"Monitor load failed for {os.path.basename(f)}: {resp.status_code}")

    return loaded


def import_dashboard(client: httpx.Client) -> bool:
    """Import OpenDashboards dashboard from .ndjson file."""
    ndjson_path = os.path.join(DASHBOARDS_DIR, "blue_team_dashboard.ndjson")
    if not os.path.exists(ndjson_path):
        log.info("No dashboard .ndjson file found — skipping dashboard import (will be created in M6)")
        return True

    with open(ndjson_path, "rb") as fh:
        content = fh.read()

    resp = client.post(
        f"{DASHBOARDS_URL}/api/saved_objects/_import?overwrite=true",
        content=content,
        headers={"osd-xsrf": "true", "Content-Type": "application/ndjson"},
        timeout=30
    )
    if resp.is_success:
        log.info("Dashboard imported to OpenDashboards")
        return True
    else:
        log.warning(f"Dashboard import failed: {resp.status_code} — will retry when dashboard file exists")
        return False


def create_index_pattern(client: httpx.Client) -> bool:
    """Create qfl-events-* index pattern in OpenDashboards."""
    payload = {
        "attributes": {
            "title": "qfl-events-*",
            "timeFieldName": "@timestamp"
        }
    }
    resp = client.post(
        f"{DASHBOARDS_URL}/api/saved_objects/index-pattern/qfl-events-star",
        json=payload,
        headers={"osd-xsrf": "true", "Content-Type": "application/json"},
        timeout=10
    )
    if resp.is_success or resp.status_code == 409:  # 409 = already exists
        log.info("Index pattern 'qfl-events-*' created/confirmed in OpenDashboards")
        return True
    else:
        log.warning(f"Index pattern creation returned {resp.status_code} — may not be critical")
        return False


def main():
    errors = 0

    if not wait_for_opensearch(60):
        log.error("OpenSearch did not become healthy — aborting bootstrap")
        sys.exit(1)

    with httpx.Client(timeout=15.0) as client:
        log.info("─── Creating index template ─────────────────────────────")
        if not create_index_template(client):
            errors += 1

        log.info("─── Loading alerting monitors ───────────────────────────")
        monitor_count = load_alerting_monitors(client)
        log.info(f"Monitors loaded: {monitor_count}")

        log.info("─── Importing OpenDashboards dashboard ──────────────────")
        import_dashboard(client)

        log.info("─── Creating SIEM index pattern ─────────────────────────")
        create_index_pattern(client)

    if errors > 0:
        log.error(f"Bootstrap completed with {errors} error(s)")
        sys.exit(1)
    else:
        log.info("Bootstrap complete. SIEM ready.")


if __name__ == "__main__":
    main()
