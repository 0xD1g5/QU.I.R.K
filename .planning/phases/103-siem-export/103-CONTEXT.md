# Phase 103: SIEM Export - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase lets security teams push QU.I.R.K. findings into their existing SIEM
(Splunk, Elastic, QRadar, or any syslog-ingesting platform) in vendor-neutral
syslog/CEF format, with zero new pip dependencies. It is a per-finding FINDINGS-PUSH
— distinct from the Phase 101 drift notifications — invokable from the CLI
(`quirk export --siem`) and optionally after a scheduled scan.

In scope: SIEM-01 (syslog/CEF export, vendor-neutral, stdlib), SIEM-02 (per-finding
CEF field mapping — severity/host/signature/evidence — CLI + optional after-scan).
Inherits Phase 101 primitives: the `integration_deliveries` audit table, `safe_str`
scrubbing, the SSRF/url-allowlist discipline, and the optional-extra/lazy-import norm
(though syslog is stdlib, so no extra needed).

Out of scope: Splunk HEC and Elastic native endpoints (DEFERRED to future-reqs per
v5.3-D-04 — syslog/CEF is the vendor-neutral baseline that lands in all of them);
ticketing (Phases 104/105).
</domain>

<decisions>
## Implementation Decisions

### CEF Format & Field Mapping (SIEM-02)
- ArcSight CEF:0 format: `CEF:0|QUIRK|scanner|<version>|<signature>|<name>|<severity>|<extension>` — vendor-neutral, parsed by Splunk/Elastic/QRadar alike
- Severity mapping to the CEF 0-10 scale: CRITICAL→10, HIGH→8, MEDIUM→5, LOW→3
- signature = finding category/id; name = human-readable finding title
- Extension fields use CEF-standard keys: `dhost`=host, `dpt`=port, `cs1`=category, `cs2`=evidence summary, `msg`=detail

### Transport (SIEM-01)
- stdlib syslog over UDP and TCP, config-selectable, via the `socket` module — zero new pip dependencies
- Splunk HEC is DEFERRED (v5.3-D-04) — syslog/CEF only this phase; note HEC + Elastic native as future-reqs
- Target configured in a `[siem]` YAML config block (host, port, protocol udp/tcp), mirroring the Phase 101 `[notifications]` config shape (loaded via QUIRK_CONFIG_PATH for the after-scan path — same DB-path trap applies)
- Endpoint validation: validate target host/port format and produce a clear error on misconfiguration; do NOT hard-block internal/loopback targets (syslog collectors are commonly on internal networks) — reuse the url_allowlist discipline only to reject obviously malformed targets, not to block private IPs

### CLI Surface & Invocation
- `quirk export --siem` reads a completed scan's `findings-*.json` (latest in output dir, or `--input <path>`)
- One CEF event per finding (SIEM-02)
- Optional after-scan push: a `[siem]` config flag (e.g. `export_after_scan: true`) triggers the push after a scheduled scan completes, analogous to the notification dispatch hook
- Failure handling (criterion 3): an unreachable/misconfigured endpoint produces a clear error message + WARNING and records an `integration_deliveries` row; it NEVER aborts or corrupts the scan record

### Payload Safety (inherits ISEC-03)
- A NEW finding-level CEF whitelist (the Phase 101 `to_integration_payload` operates on TrendReport/drift — wrong shape for per-finding): host / port / protocol / severity / category / evidence-summary are ALLOWED; raw cert PEM, full SAN lists, and any private-key material are EXCLUDED (criterion 2 — no raw cert PEM or internal PKI topology)
- Evidence field is a truncated/sanitized summary, never raw PEM blocks
- Route all errors through `safe_str` (ISEC-02); escape CEF special characters (`|`, `=`, `\`, newline) per the CEF spec in both header and extension
- Reuse the Phase 101 `integration_deliveries` table for the delivery audit (destination="siem")

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 101 `integration_deliveries` table (quirk/models.py) + `safe_str` (quirk/util/safe_exc.py) + url_allowlist discipline (quirk/util/url_allowlist.py).
- Findings are a list of dicts with `severity`, `host`, `category`, evidence fields, persisted to `findings-{stamp}.json` by quirk/reports/writer.py::write_reports (line ~144).
- CryptoEndpoint model (quirk/models.py:9) holds the per-endpoint scan data (host, port, protocol, cert_* fields — cert_subject/issuer/sans must be excluded from the SIEM payload).
- CLI subcommand registration via the run_scan.py interception block (see init/serve/compliance/doctor/schedule/qramm/analyze-token patterns ~lines 364-484).
- Phase 101 notification dispatcher (quirk/notify/dispatcher.py) + the scheduler hook in scheduler_cmd.py — model the optional after-scan SIEM push on this, and reuse the QUIRK_CONFIG_PATH config-load (NOT the scheduler --config DB path).

### Established Patterns
- `[notifications]` YAML config block + NotifyCfg loader (quirk/notify/config.py) — mirror for `[siem]`.
- Per-channel try/except + integration_deliveries audit row + safe_str logging (Phase 101 dispatcher) — mirror for SIEM delivery.
- Zero-new-dep norm; syslog/CEF are entirely stdlib (socket / string formatting).

### Integration Points
- New quirk/cli/export_cmd.py (or siem module) + run_scan.py interception for `quirk export`.
- New `[siem]` config parsing.
- The scheduled-scan after-hook (scheduler_cmd.py) for export_after_scan.
- quirk/reports/writer.py findings JSON is the input the CLI reads.

</code_context>

<specifics>
## Specific Ideas

- CEF char-escaping is a classic correctness pitfall: the header fields escape `\` and `|`; the extension escapes `\`, `=`, and newlines. Get both right or SIEM parsing breaks.
- This validates the `send_findings_export` pattern before Phases 104/105 add higher-complexity ticketing dedup (v5.3-D-04 ordering rationale).
- The success-criteria text mentions "Splunk HEC endpoint" but the LOCKED scope (v5.3-D-04) defers HEC — syslog/CEF lands in Splunk via a syslog input, satisfying the goal without HTTP. Note HEC as future-reqs, do not implement it here.

</specifics>

<deferred>
## Deferred Ideas

- Splunk HEC native endpoint + Elastic native endpoint (v5.3-D-04) — future-reqs.
- TLS-wrapped syslog (RFC 5425) — plain UDP/TCP this phase.
- Per-finding dedup/idempotency (that's the ticketing concern in 104/105; SIEM is fire-and-forget push).

</deferred>
