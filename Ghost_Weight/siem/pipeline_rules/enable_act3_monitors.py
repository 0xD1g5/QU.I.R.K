#!/usr/bin/env python3
"""
enable_act3_monitors.py — Enable defensive monitoring for Act III.

Enables monitors 02-04 via OpenSearch Alerting API.
Run this at the Act III transition to show the defended state.

Usage:
  python3 siem/pipeline_rules/enable_act3_monitors.py
  python3 siem/pipeline_rules/enable_act3_monitors.py --disable  (revert to Act II state)
"""

import sys
import argparse
import httpx

OPENSEARCH_URL = "http://localhost:9200"
MONITOR_NAMES = [
    "QFL-MONITOR-02-SemanticFirewall",
    "QFL-MONITOR-03-AgentIdentity",
    "QFL-MONITOR-04-TrustChain",
]


def find_monitor_id(client: httpx.Client, name: str) -> str | None:
    resp = client.post(
        f"{OPENSEARCH_URL}/_plugins/_alerting/monitors/_search",
        json={"query": {"term": {"monitor.name.keyword": name}}},
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    if resp.is_success:
        hits = resp.json().get("hits", {}).get("hits", [])
        if hits:
            return hits[0]["_id"]
    return None


def set_monitor_state(client: httpx.Client, monitor_id: str, enabled: bool) -> bool:
    # Fetch current monitor
    resp = client.get(f"{OPENSEARCH_URL}/_plugins/_alerting/monitors/{monitor_id}", timeout=10)
    if not resp.is_success:
        return False

    monitor = resp.json().get("monitor", {})
    monitor["enabled"] = enabled

    # Update
    resp = client.put(
        f"{OPENSEARCH_URL}/_plugins/_alerting/monitors/{monitor_id}",
        json=monitor,
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    return resp.is_success


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--disable", action="store_true", help="Disable Act III monitors (revert to Act II)")
    args = parser.parse_args()

    target_state = not args.disable
    action = "Enabling" if target_state else "Disabling"
    print(f"\n{'─'*60}")
    print(f"  {action} Act III defensive monitors...")
    print(f"{'─'*60}")

    with httpx.Client() as client:
        # Check OpenSearch is reachable
        try:
            client.get(f"{OPENSEARCH_URL}/_cluster/health", timeout=5)
        except Exception:
            print(f"  ERROR: OpenSearch not reachable at {OPENSEARCH_URL}")
            sys.exit(1)

        for name in MONITOR_NAMES:
            monitor_id = find_monitor_id(client, name)
            if not monitor_id:
                print(f"  SKIP  {name} — not found (run bootstrap first)")
                continue

            success = set_monitor_state(client, monitor_id, target_state)
            state_label = "ENABLED" if target_state else "DISABLED"
            status = "✓" if success else "✗"
            print(f"  {status}  {name} → {state_label}")

    print(f"{'─'*60}")
    print(f"  Act III monitors {'active' if target_state else 'disabled'}.")
    print()


if __name__ == "__main__":
    main()
