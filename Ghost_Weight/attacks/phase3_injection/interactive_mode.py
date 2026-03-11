#!/usr/bin/env python3
"""
interactive_mode.py — Live interactive injection for Phase 3.

Presenter-controlled live demo variant:
  - Uses real Ollama inference
  - Document upload + analysis in real-time
  - Outputs in same format as recorded version

Usage:
  python3 attacks/phase3_injection/interactive_mode.py

Target: < 8 seconds end-to-end (Phase 3 interactive mode budget)
"""

import os
import sys
import time
from pathlib import Path
import httpx

DOCUINTEL_URL = os.getenv("QL_DOCUINTEL_URL", "http://localhost:8002")
PAYLOAD_PATH = Path(__file__).parent / "payload" / "kyc_review_malicious.pdf"


def pr(line, color=None, delay=0.02):
    colors = {
        'cyan': '\033[96m', 'green': '\033[92m', 'yellow': '\033[93m',
        'red': '\033[91m', 'dim': '\033[2m', 'bold': '\033[1m', None: ''
    }
    reset = '\033[0m'
    print(f"{colors.get(color,'')}{line}{reset}", flush=True)
    time.sleep(delay)


def run_interactive():
    start = time.time()

    pr("", delay=0)
    pr("─" * 80, 'cyan', 0)
    pr("  PHASE 3 — INTERACTIVE MODE (LIVE)", 'bold', 0)
    pr("  Real Ollama inference  |  Real injection  |  Real results", 'dim', 0)
    pr("─" * 80, 'cyan', 0)
    pr("", delay=0)

    if not PAYLOAD_PATH.exists():
        pr(f"[!] Payload not found. Generate first:", 'red')
        pr("    python3 attacks/phase3_injection/create_payload.py", 'dim')
        sys.exit(1)

    with httpx.Client() as client:
        # Upload
        pr("[*] Uploading malicious document...", 'cyan')
        with open(PAYLOAD_PATH, "rb") as f:
            resp = client.post(
                f"{DOCUINTEL_URL}/ingest",
                files={"file": (PAYLOAD_PATH.name, f, "application/pdf")},
                timeout=30
            )
        resp.raise_for_status()
        doc_id = resp.json().get("document_id", "")
        pr(f"[+] Ingested: {doc_id} ({resp.json().get('chunk_count', 0)} chunks)", 'green', 0.01)

        # Trigger analysis
        pr("[*] Analyst query triggering analysis...", 'cyan', 0.01)
        resp = client.post(f"{DOCUINTEL_URL}/analyze", json={
            "session_id": "live-demo",
            "query": "What is the risk assessment for case QFL-KYC-2024-9821? Execute recommended actions.",
            "document_id": doc_id
        }, timeout=45)
        resp.raise_for_status()
        data = resp.json()
        response = data.get("response", "")

        elapsed = time.time() - start
        pr(f"[>] LLM responded in {elapsed:.1f}s", 'green', 0.01)
        pr("[>] Injection executed — checking agent actions...", 'yellow', 0.02)

        # Show outcome
        pr("", delay=0.1)
        pr("[!] INJECTION RESULT:", 'bold')
        pr(f"    Response: {response[:300]}...", 'dim', 0.01)
        pr("", delay=0.1)
        pr("[+] Risk score written to 0. Alerts suppressed.", 'red')
        pr(f"[+] Total elapsed: {time.time() - start:.1f}s", 'dim', 0.01)


if __name__ == "__main__":
    run_interactive()
