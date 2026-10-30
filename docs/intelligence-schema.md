# Intelligence JSON Output

Each scan writes `intelligence-<timestamp>.json` in the configured output directory.

## Versioning

- `intelligence_version`: version marker for this file.
- Sourced from `INTELLIGENCE_VERSION = PLATFORM_VERSION` in `quirk/reports/writer.py` — it equals the installed QUIRK package version (for example `5.25.0` for the 5.25.0 release).

## Top-level fields

`quirk/validate.py` (`python -m quirk.validate --output-dir <dir>`) checks the file's required keys. Its `roadmap` check currently expects a list while `write_reports()` emits an object (shown below), so a freshly written intelligence file is reported as `intelligence.roadmap must be a list`. The shape documented here is the one `write_reports()` emits. Top-level keys:

- `intelligence_version`: string
- `assessment`: metadata only
  - `name`
  - `owner`
  - `data_classification`
  - `timezone`
- `evidence_summary`: normalized evidence from endpoints + findings
  - protocol counts, plaintext HTTP counts, mTLS signals
  - certificate observation counts (expired/expiring/self-signed, key type counts)
  - scan error and TLS enum coverage metrics
  - `finding_severity_counts` (every finding by severity) and `scored_finding_severity_counts` (the same counts without score-neutral configuration advisories, such as the JWKS verify-disabled finding; scoring, the roadmap and score-lift estimates read this one)
- `score`: readiness score output
  - `total`, `subscores`, `drivers` (a list of reason strings), `rating_cap_reason`, `domains_assessed`, `domains_total`, `score_divisor`, `coverage_disclosure`, `scoring_version`
  - `subscores` contains six entries: `hygiene`, `modern_tls`, `identity_trust`, `agility_signals`, `data_at_rest`, `data_in_motion` (each 0–25, or `null` for a domain that was not assessed)
- `confidence`: confidence output
  - `confidence` (a number), `confidence_factors` (an object with `coverage_ratio`, `scan_error_ratio`, `tls_enum_coverage_ratio`, `unknown_ratio`), `confidence_formula_version`
- `roadmap`: phased roadmap output (an object)
  - `roadmap_version`, `item_count`, `phase_counts`, `items`
- `calibration`: the scoring calibration in effect
  - `profile`, `overrides_applied`

## Data safety

- The intelligence JSON is summary-level: counts, ratios and scores, plus assessment metadata and roadmap and driver text derived from them (the roadmap is built from the evidence summary and the score, not from individual endpoints). `CryptoEndpoint` has no raw-certificate-PEM column, so no PEM can appear in it.
- Output is summary-level and deterministic for identical inputs (two runs over the same endpoints produce byte-identical content apart from the filename timestamp).

## TrendReport (Phase 31)

`compute_trend_report()` in `quirk/intelligence/trends.py` produces a session-over-session comparison between the two most recent distinct scan sessions. For `GET /api/trends`, a session is one scan run: rows are grouped by their `scan_run_id`, and each session is represented by its earliest `scanned_at` (`list_session_timestamps` in `quirk/intelligence/trends.py`, which the drift notifier also uses). Older rows that carry no `scan_run_id` are grouped by `scanned_at` truncated to the millisecond, so two such scans started within the same second remain distinct sessions. The endpoint `GET /api/trends` returns this schema.

### Wire format

Full two-session response (two or more distinct sessions in the database):

```json
{
  "current_session_ts": "2026-04-26T10:30:00+00:00",
  "previous_session_ts": "2026-04-26T09:00:00+00:00",
  "current_score": 84.0,
  "previous_score": 80.0,
  "score_delta": 4.0,
  "new_high": 0,
  "new_medium": 1,
  "new_low": 1,
  "resolved_high": 1,
  "resolved_medium": 0,
  "resolved_low": 0,
  "scan_errors_new_count": 0,
  "scan_errors_resolved_count": 1,
  "new_findings_sample": [
    { "host": "10.0.1.5", "port": 8443, "protocol": "TLS", "severity": "MEDIUM" },
    { "host": "10.0.1.7", "port": 22,   "protocol": "SSH", "severity": "LOW" }
  ],
  "resolved_findings_sample": [
    { "host": "10.0.1.3", "port": 443,  "protocol": "TLS", "severity": "HIGH" }
  ],
  "severity_transitions": [
    { "host": "10.0.1.9", "port": 443, "protocol": "TLS", "previous_severity": "HIGH", "current_severity": "MEDIUM" }
  ],
  "new_total": 2,
  "resolved_total": 1
}
```

**Added in 5.19.0 (Phase 178, IDENT-02):** `severity_transitions`, `new_total`, `resolved_total`.
Older clients that only read the severity-bucketed fields (`new_high`/`new_medium`/... and
`resolved_high`/`resolved_medium`/...) are unaffected — the three new fields are additive, with
backward-compatible defaults (`[]` / `0` / `0`) on the single-session response below.

| Field | Type | Added | Meaning |
|-------|------|-------|---------|
| `severity_transitions` | `SeverityTransitionResponse[]` | 5.19.0 | One entry per `(host, port, protocol)` present in both sessions whose severity changed. Each entry has `host`, `port`, `protocol`, `previous_severity`, `current_severity`. An endpoint listed here is excluded from `new_findings_sample`/`resolved_findings_sample` — it did not appear or disappear, it changed. |
| `new_total` | `int` | 5.19.0 | Severity-agnostic count of newly appeared `(host, port, protocol)` keys (`len(new_keys)`). Stays non-zero even when every row's severity is `NULL`, unlike the `new_high`/`new_medium`/`new_low` buckets. |
| `resolved_total` | `int` | 5.19.0 | Severity-agnostic count of `(host, port, protocol)` keys present in the previous session but not the current one (`len(resolved_keys)`). Same non-zero-even-without-severity guarantee as `new_total`. |

### Single-session response (D-06)

When exactly one distinct session exists, `GET /api/trends` returns HTTP 200 with the following collapsed form (an empty database returns the same shape, with the timestamp and score fields null, every count zero and every array empty):

```json
{
  "current_session_ts": "2026-04-26T10:30:00+00:00",
  "previous_session_ts": null,
  "current_score": 84.0,
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
  "resolved_findings_sample": [],
  "severity_transitions": [],
  "new_total": 0,
  "resolved_total": 0
}
```

`score_delta` is JSON `null`, NOT `0` — `null` signals "no comparison available", which the dashboard renders as the baseline empty state.

### Match key (D-03, re-keyed in Phase 178 / IDENT-02)

**As of 5.19.0**, findings are matched across sessions by the tuple `(host, port, protocol)` —
severity is NOT part of the match key. A finding is "new" if its key appears in the current
session but not the previous. A finding is "resolved" if its key appears in the previous session
but not the current. Severity is carried alongside the key (not embedded in it), so a severity
change at an unchanged `(host, port, protocol)` no longer surfaces as one resolved entry plus one
new entry — it surfaces as a single `severity_transitions` entry instead. See "Wire format" above
for the field.

**Why this changed:** severity is set only by some scanners and connectors (for example the AWS, Azure, GCP, database, Kubernetes and Vault connectors); TLS, SSH, container, email and source-code endpoints leave it NULL, so on a typical scan database the large majority of `crypto_endpoints` rows carry `severity IS NULL`. Before Phase 178
the match key included severity AND a filter dropped every `severity IS NULL` row before the
comparison ran, which together emptied both session's key sets whenever no row carried a severity — on such a
database (the typical case) every trend report showed 0 new / 0 resolved regardless of real change. The `severity IS NULL` filter was
removed and severity was moved out of the key so the delta reflects real endpoint-level movement;
see `docs/report-interpretation.md` §15 for the client-facing explanation.

### Severity buckets (D-05)

| ORM severity | Bucket  |
|--------------|---------|
| CRITICAL     | high    |
| HIGH         | high    |
| MEDIUM       | medium  |
| LOW          | low     |
| INFO         | excluded from the `*_high` / `*_medium` / `*_low` counts (still counted in `new_total` / `resolved_total`, and may appear in the sample arrays) |

### Excluded rows

- Rows with `scan_error IS NOT NULL` (D-04) — reported separately as `scan_errors_new_count` / `scan_errors_resolved_count`, NOT in the severity buckets. These two are a net change in the number of error rows, not a per-host match: `scan_errors_new_count` is `max(0, current errors - previous errors)` and `scan_errors_resolved_count` is `max(0, previous errors - current errors)`; rows whose `scan_error_category` is `missing_extra` are not counted. Additionally, if a `(host, port, protocol)` triplet has a scan_error in the current session, its matching previous-session entries are also excluded to prevent phantom "resolved" findings for temporarily unreachable hosts.
- Rows with `scanned_at IS NULL` (D-13) — older data without a scan timestamp is ignored entirely; does not count toward session total.

### Sample arrays (D-08)

Sample arrays are capped at 5 entries. Sort order is severity descending (CRITICAL, HIGH, MEDIUM, LOW, then INFO and NULL severity) then host ascending then port ascending. Sample entries contain only `host`, `port`, `protocol`, and `severity` — no remediation text, no algorithm details.

## Trends Timeline (TREND-01)

A second endpoint `GET /api/trends/timeline` returns a multi-point sequence (not just a two-session diff), newest first, up to `n` points (default 30). It groups exactly like `/api/trends` (via `list_session_timestamps`): one point per scan run, so a scan whose stages stamped their rows at different times is still one point. Lives at `quirk/dashboard/api/routes/trends.py:get_trends_timeline`; response model is `TrendTimelineResponse` in `quirk/dashboard/api/schemas.py`.

`/timeline` is a separate endpoint and does not change the `/api/trends` response described above.
