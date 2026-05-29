# Intelligence JSON Output

Each scan writes `intelligence-<timestamp>.json` in the configured output directory.

## Versioning

- `intelligence_version`: schema/version marker for this file.
- Sourced from `INTELLIGENCE_VERSION = PLATFORM_VERSION` in `quirk/reports/writer.py` — tracks the QUIRK release version.
- Current version: `5.5.0`.

## Top-level fields

The authoritative schema check is `quirk/validate.py` (`intelligence` validator). Required top-level keys:

- `intelligence_version`: string
- `generated_utc`: UTC timestamp when the file was generated
- `assessment`: metadata only
  - `name`
  - `report_owner`
  - `data_classification`
  - `timezone`
- `evidence_summary`: normalized evidence from endpoints + findings
  - protocol counts, plaintext HTTP counts, mTLS signals
  - certificate observation counts (expired/expiring/self-signed, key type counts)
  - scan error and TLS enum coverage metrics
- `score`: readiness score output (renamed from `score_breakdown` in v5.0)
  - `score`, `rating`, `subscores`, `drivers`
  - `subscores` contains six entries: `hygiene`, `modern_tls`, `identity_trust`, `agility_signals`, `data_at_rest`, `data_in_motion` (each 0–25)
- `confidence`: confidence output (renamed from `confidence_factors` in v5.0)
  - `confidence_score`, `confidence_rating`, `coverage_pct`, `tls_enum_coverage_pct`, `blockers_top`
- `roadmap`: phased roadmap output
  - `roadmap_version`, `item_count`, `phase_counts`, `items`

## Data safety

- The intelligence JSON excludes raw certificate PEMs and secrets.
- Output is summary-level and deterministic for identical inputs.

## TrendReport (v4.3, Phase 31)

`compute_trend_report()` in `quirk/intelligence/trends.py` produces a session-over-session comparison between the two most recent distinct scan sessions. Sessions are grouped by second-truncated `scanned_at` timestamp — the same `strftime("%Y-%m-%d %H:%M:%S", scanned_at)` grouping established by `list_scans()` in `quirk/dashboard/api/routes/scan.py`. The endpoint `GET /api/trends` returns this schema.

### Wire format

Full two-session response (two or more distinct sessions in the database):

```json
{
  "current_session_ts": "2026-04-26T10:30:00",
  "previous_session_ts": "2026-04-26T09:00:00",
  "current_score": 72,
  "previous_score": 65,
  "score_delta": 7,
  "new_high": 0,
  "new_medium": 2,
  "new_low": 1,
  "resolved_high": 1,
  "resolved_medium": 0,
  "resolved_low": 3,
  "scan_errors_new_count": 0,
  "scan_errors_resolved_count": 1,
  "new_findings_sample": [
    { "host": "10.0.1.5", "port": 8443, "protocol": "TLS", "severity": "MEDIUM" },
    { "host": "10.0.1.7", "port": 22,   "protocol": "SSH", "severity": "LOW" }
  ],
  "resolved_findings_sample": [
    { "host": "10.0.1.3", "port": 443,  "protocol": "TLS", "severity": "HIGH" }
  ]
}
```

### Single-session response (D-06)

When fewer than two distinct sessions exist, `GET /api/trends` returns HTTP 200 with the following collapsed form:

```json
{
  "current_session_ts": "2026-04-26T10:30:00",
  "previous_session_ts": null,
  "current_score": 72,
  "previous_score": null,
  "score_delta": null,
  "new_high": 0,
  "new_medium": 0,
  "new_low": 0,
  "resolved_high": 0,
  "resolved_medium": 0,
  "resolved_low": 0,
  "scan_errors_new_count": 0,
  "scan_errors_resolved_count": 0,
  "new_findings_sample": [],
  "resolved_findings_sample": []
}
```

`score_delta` is JSON `null`, NOT `0` — `null` signals "no comparison available", which the dashboard renders as the baseline empty state.

### Match key (D-03)

Findings are matched across sessions by the tuple `(host, port, protocol, severity)`. A finding is "new" if it appears in the current session but not the previous. A finding is "resolved" if it appears in the previous session but not the current. A severity change on the same `(host, port, protocol)` surfaces as one resolved entry + one new entry.

### Severity buckets (D-05)

| ORM severity | Bucket  |
|--------------|---------|
| CRITICAL     | high    |
| HIGH         | high    |
| MEDIUM       | medium  |
| LOW          | low     |
| INFO         | excluded (does not appear in counts or samples) |

### Excluded rows

- Rows with `scan_error IS NOT NULL` (D-04) — counted separately as `scan_errors_new_count` / `scan_errors_resolved_count`, NOT in the severity buckets. Additionally, if a `(host, port, protocol)` triplet has a scan_error in the current session, its matching previous-session entries are also excluded to prevent phantom "resolved" findings for temporarily unreachable hosts.
- Rows with `scanned_at IS NULL` (D-13) — v4.2-era data ignored entirely; does not count toward session total. The first post-v4.3 trend report will show all DAR findings as "new" (they were absent from any prior session that lacked DAR columns) — this is correct behavior, not a bug.

### Sample arrays (D-08)

Sample arrays are capped at 5 entries. Sort order is severity descending (high → medium → low) then host ascending then port ascending. Sample entries contain only `host`, `port`, `protocol`, and `severity` — no remediation text, no algorithm details.

## Trends Timeline (v5.x, TREND-01)

A second endpoint `GET /api/trends/timeline` returns a multi-session sequence (not just a two-session diff). Use it to drive sparkline / line-chart visualizations of overall readiness across many scans. Lives at `quirk/dashboard/api/routes/trends.py:get_trends_timeline`; response model is `TrendTimelineResponse` in `quirk/dashboard/api/schemas.py`.

The two-session `/api/trends` endpoint described above is unchanged in v5.x — `/timeline` is additive.
