# Phase 31: Trend Analysis - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-26
**Phase:** 31-trend-analysis
**Areas discussed:** Finding match key, Trends page placement, Single-session behavior, Report detail level

---

## Finding Match Key

### Q1: How should compute_trend_report() decide if a finding is 'the same' across sessions?

| Option | Description | Selected |
|--------|-------------|----------|
| (host, port, protocol, severity) | Balances precision and stability. Severity in key means a severity change shows as resolved+new. | ✓ |
| (host, port, service_detail, severity) | Most precise but service_detail strings can drift across scanner versions, causing ghost findings. | |

**User's choice:** (host, port, protocol, severity) — but raised question about what "host" means

---

### Q2: How to handle the host field (hostname vs IP instability)?

| Option | Description | Selected |
|--------|-------------|----------|
| Use host as-is + note the caveat | Match on (host, port, protocol, severity). Document IP caveat. | ✓ |
| Use host as-is, no severity | Match on (host, port, protocol). Severity changes invisible. | |
| Normalize host to lowercase only | Minor hygiene improvement for hostname comparison. | |

**User's choice:** Use host as-is, document the caveat
**Notes:** User specifically raised that IPs can change in an environment (DHCP, load balancers), and hostnames can too but less frequently. MAC address considered but ruled out as too late and doesn't apply to all resource types. Host field is already stable for cloud resources (bucket names, Vault addresses, etc.) — instability is limited to IP-configured TLS/SSH targets.

---

### Q3: Severity changes — should they show as resolved+new?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — surface severity changes | HIGH → MEDIUM shows as HIGH resolved + MEDIUM new. Visible improvement story. | ✓ |
| No — severity changes silent | Match on (host, port, protocol) without severity. | |

**User's choice:** Yes — surface severity changes

---

### Q4: How to handle scan_error endpoints?

| Option | Description | Selected |
|--------|-------------|----------|
| Exclude scan_errors from trend | Filter out rows where scan_error IS NOT NULL. | ✓ |
| Include scan_errors in trend | Treat scan_error endpoints like any other finding. | |
| Separate scan_error delta | Track errors as own field alongside finding delta. | (revisited) |

**User's choice:** Initially excluded, then revisited to add separate error count delta

---

### Q5 (revisit): Should scan_error delta be surfaced separately?

| Option | Description | Selected |
|--------|-------------|----------|
| Ignore error changes entirely | Keep trend report focused on findings only. | |
| Surface error count delta | Add scan_errors_new_count and scan_errors_resolved_count as simple integers. | ✓ |
| Surface error host detail | List which hosts are newly erroring or reachable. | |

**User's choice:** Surface error count delta (simple integers, no host detail)

---

## Trends Page Placement

### Q1: Where does trend data live?

| Option | Description | Selected |
|--------|-------------|----------|
| New sidebar page at /trends | Follows exact established pattern (new page, route, nav entry). | ✓ |
| Section on Executive Summary | Score delta as appended panel on existing Executive page. | |

**User's choice:** New sidebar page at /trends

---

### Q2: What does the Trends page show?

| Option | Description | Selected |
|--------|-------------|----------|
| Score delta + severity counts | Matches TREND-01 through TREND-04 exactly. | |
| Score delta + severity counts + session timestamps | Same plus the two session timestamps being compared. | ✓ |

**User's choice:** Score delta + severity counts + timestamps
**Notes:** User asked about building historical time-series charts based on remediation scans — this is a great future addition. Timestamps in the API response enable this. Deferred multi-session charting to a future phase.

---

## Single-Session Behavior

### Q1: GET /api/trends when only 1 scan exists?

| Option | Description | Selected |
|--------|-------------|----------|
| 200 with null delta | Return 200 with score_delta: null, all counts 0, previous_session_ts: null. | ✓ |
| 404 Not Found | Return 404 with message. | |
| 200 with is_baseline flag | Return 200 with is_baseline: true field. | |

**User's choice:** 200 with null delta

---

## Report Detail Level

### Q1: Counts only or include finding identifiers?

| Option | Description | Selected |
|--------|-------------|----------|
| Counts by severity only | Matches TREND-02/03 exactly. | |
| Counts + top 5 examples per category | Include host+port+protocol+severity for top 5 new and resolved findings. | ✓ |
| Counts + full finding lists | Complete arrays of all new/resolved identifiers. | |

**User's choice:** Counts + top 5 examples per category

---

### Q2: What fields in each sample finding?

| Option | Description | Selected |
|--------|-------------|----------|
| host + port + protocol + severity | Minimal identifiable context. | ✓ |
| host + port + protocol + severity + service_detail | Adds finding type description. | |

**User's choice:** host + port + protocol + severity

---

### Q3: How to display top-5 samples in the UI?

| Option | Description | Selected |
|--------|-------------|----------|
| Compact table in Trends page | Two collapsible tables: "New Findings" and "Resolved Findings". | ✓ |
| Badge list below each severity count | Inline host:port badges below the count card. | |
| You decide | Claude picks based on existing patterns. | |

**User's choice:** Compact table in the Trends page

---

## Claude's Discretion

- Exact Pydantic schema class name for API response
- Whether compute_trend_report() returns a dataclass or Pydantic model
- lucide-react icon for Trends nav entry (TrendingUp recommended)
- Score delta badge prefix format (e.g., "▲ +X.X pts")
- Exact wording of "Baseline scan" empty state

## Deferred Ideas

- **Historical time-series charts** — User asked about charting progress across many scans. Requires persisting trend snapshots. Phase 31 timestamps lay the groundwork. Deferred to v4.4.
- **Full new/resolved finding lists** — Phase 31 returns top-5 only. Future phase can paginate.
- **Per-scanner-type trend breakdown** — Score delta by surface (TLS, identity, DAR). Requires subscore history.
