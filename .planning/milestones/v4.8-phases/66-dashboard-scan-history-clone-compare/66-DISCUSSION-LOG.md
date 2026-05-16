# Phase 66: Dashboard Scan History + Clone/Compare - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-13
**Phase:** 66-dashboard-scan-history-clone-compare
**Areas discussed:** History page data, Clone for CLI scans, Compare selection UX, Diff view layout

---

## History Page Data

| Option | Description | Selected |
|--------|-------------|----------|
| Extend /api/scans | Add fields + remove LIMIT 10 from existing endpoint; ScanSelector gets richer data for free | ✓ |
| New /api/scans/history endpoint | Keep /api/scans unchanged; add a separate richer endpoint for the /scans page | |

**User's choice:** Extend /api/scans (Recommended)
**Notes:** One endpoint to maintain; ScanSelector is already calling /api/scans and additive fields don't break it.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Inline score per session | Same pattern as Phase 64 trends/timeline — compute_readiness_score per session (~30ms each) | ✓ |
| Score only for latest N sessions | Compute inline for most recent 50; older sessions show score as null | |

**User's choice:** Inline score per session (Recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse trends severity buckets | CRITICAL+HIGH → "high", MEDIUM → "medium", LOW → "low", INFO excluded | ✓ |
| 4-tier: CRITICAL, HIGH, MEDIUM, LOW | Distinct counts for all four tiers | |

**User's choice:** Yes — reuse trends severity buckets (Recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| All scans, no cap | Remove LIMIT 10; return every session | ✓ |
| Configurable cap — default 200 | Keep a cap but raise it; prevent unbounded query | |

**User's choice:** All scans, no cap (Recommended)

---

## Clone for CLI Scans

| Option | Description | Selected |
|--------|-------------|----------|
| Clone all scans — derive target from endpoints | Reconstruct target from CryptoEndpoint.host; default profile/calibration | ✓ |
| Clone only dashboard-launched scans | Hide/gray clone button for scans with no scan_jobs row | |

**User's choice:** Clone all scans — derive target from endpoints

---

| Option | Description | Selected |
|--------|-------------|----------|
| Editable + notice | Pre-fill with amber info: "Targets reconstructed from scan results — review before submitting" | ✓ |
| Editable, no notice | Pre-fill silently | |

**User's choice:** Yes — editable + notice (Recommended)

---

## Compare Selection UX

| Option | Description | Selected |
|--------|-------------|----------|
| Checkboxes on rows | Select 2 → enable sticky Compare button; 3rd check unchecks oldest | ✓ |
| "Compare to..." button per row | Two-step: anchor first scan, then click Compare on second | |

**User's choice:** Checkboxes on rows (Recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| New /compare route | Navigate to /compare?a=X&b=Y — dedicated full-page diff, bookmarkable | ✓ |
| Expand below the table | Diff renders inline on /scans page | |
| Modal / sheet overlay | Full-height sheet, no URL change | |

**User's choice:** New /compare route (Recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| New /api/compare?a=X&b=Y endpoint | Backend computes diff; returns structured CompareResponse; testable with pytest | ✓ |
| Client-side diff from two /api/scan/latest calls | Frontend fetches both scans and diffs in TypeScript | |

**User's choice:** New /api/compare?a=X&b=Y endpoint (Recommended)

---

## Diff View Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Score header + tabbed sections | Delta card at top; Findings / Subscores / Endpoints tabs | ✓ |
| Side-by-side split view | Two columns, one per scan; differences highlighted | |

**User's choice:** Score header + tabbed sections (Recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| Show as endpoint-only-in-A or endpoint-only-in-B | Disjoint hosts in dedicated sections; flagged as "not present in other scan" | ✓ |
| Exclude disjoint hosts from Endpoints tab | Only show hosts that appear in both scans | |

**User's choice:** Show as endpoint-only-in-A or endpoint-only-in-B (Recommended)

---

| Option | Description | Selected |
|--------|-------------|----------|
| All 6 subscores, always | Show all 6 pillar deltas even if Δ = 0 | ✓ |
| Only changed subscores | Filter out subscores where delta = 0 | |

**User's choice:** All 6 subscores, always (Recommended)

---

## Claude's Discretion

- **Findings tab as default tab** — most actionable for a consultant reviewing a regression
- **Empty-state messages per tab** — show friendly "No added findings" / "No removed findings" / "No changed endpoints" rather than hiding tabs
- **Score delta color** — green if scan A > scan B (improvement), red if scan A < scan B
- **`/api/compare` 400 on a==b** — return HTTP 400 with "Cannot compare a scan to itself."
- **`ScanSession.profile` and `.calibration` for CLI scans** — null in API response; rendered as "—" in UI
- **Compare auth** — read-only GET, `require_auth` only (no CSRF needed)

## Deferred Ideas

- **Pagination UI** — scrollable table is sufficient for consulting-scale scan counts; paginate in a future phase if needed
- **Scan deletion** — future UX polish phase
- **Bulk export** — multiple scan export; separate phase
- **Per-scan permalink page** — dedicated URL per historical scan; would complement the compare URL scheme
