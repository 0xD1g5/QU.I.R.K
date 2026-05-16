---
status: complete
phase: 65-dashboard-initiated-scan
source: [65-06-PLAN.md, 65-VALIDATION.md]
started: 2026-05-13
updated: 2026-05-14
---

## Current Test

Awaiting operator walkthrough — 4 manual cases to verify.

## Setup

**Prereqs before starting:**
1. `QUIRK_API_TOKEN` set in the environment used by `quirk serve`
2. Build dashboard: `cd src/dashboard && npm run build`
3. Start API: `quirk serve`
4. Open dashboard URL in browser and authenticate with bearer token

## Tests

### Case A — Form render (UI-SCAN-01)

**Steps:**
1. Click "New Scan" in the sidebar (accent-colored button above nav items)
2. Verify URL changes to `/scan/new`
3. Verify form shows EXACTLY 4 controls:
   - Targets textarea (empty, monospaced, placeholder "192.168.1.0/24, api.example.com")
   - Profile radio group: Quick / Standard / Deep — Standard selected by default
   - Calibration radio group: Strict / Balanced / Lenient — Balanced selected by default
   - "Enable nmap discovery" checkbox — UNCHECKED by default
4. Submit with empty targets — verify inline error "Targets field is required."
5. Type `@/tmp/x.txt` and submit — verify inline error mentions "@file paths are not supported from the dashboard"

expected: /scan/new renders 4 controls with correct defaults; empty submit and @file submit both show correct inline errors
result: PASS
date: 2026-05-13  tester: Digs

### Case B — Live stage progression (UI-SCAN-02)

**Steps:**
1. On /scan/new, enter `127.0.0.1` as target
2. Leave profile=Standard, calibration=Balanced, nmap=off
3. Click "Run Scan"
4. Verify URL changes to `/scan/job/<uuid>` within ~1 second
5. Verify page renders:
   - "Scan Progress" heading + "Running" badge (orange/high)
   - 7-step stage indicator
   - Progress bar starting near 0
   - Job ID in monospace
   - "Cancel scan" destructive (red) button at the bottom
6. Observe for ~30-90 seconds: stage label updates from "Stage 1 of 7 — Discovery" through "Stage 7 of 7 — Reports"; completed stage dots turn teal; current stage pulses accent

expected: /scan/job/:jobId renders within 1s; 7-step stage indicator advances through all stages; dots change state as stages complete
result: PASS
date: 2026-05-13  tester: Digs

### Case C — Post-completion navigation (UI-SCAN-03)

**Steps:**
1. Continuing from Case B, wait for scan to complete
2. Verify page auto-navigates to `/` (executive summary)
3. Verify scan switcher shows the new scan selected (just-completed scan_run_id)
4. Verify executive summary displays the readiness score and findings of the new scan

expected: On completion, auto-navigates to / with new scan selected and results visible — indistinguishable from CLI-launched scan
result: PASS
date: 2026-05-13  tester: Digs

### Case D — Cancel button stops the subprocess (UI-SCAN-03)

**Steps:**
1. From sidebar, click "New Scan" again
2. Submit a long-running scan (e.g. `192.168.1.0/24` with profile=Deep)
3. On /scan/job/:jobId during a running stage (not Reports), click "Cancel scan"
4. Verify page navigates to /scan/new immediately
5. In a terminal: `ps aux | grep run_scan` — verify NO run_scan.py process with the cancelled scan's pid remains
6. Check DB: `SELECT status, error_message, completed_at FROM scan_jobs WHERE job_id = '<cancelled_id>';` — verify status='cancelled' and completed_at is set

expected: Cancel button disappears; status transitions to "cancelled" on next poll; scan_jobs row shows status='cancelled' with completed_at populated
result: PASS
date: 2026-05-13  tester: Digs
notes: Initial implementation navigated to /scan/new on cancel; fixed to stay on job page and let polling pick up cancelled status.

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

None anticipated. All 4 cases cover visually-verifiable behaviors that automated tests cannot replicate.
