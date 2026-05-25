# Feature Research — v5.4 Distributed On-Prem Scanner Architecture

**Domain:** Distributed agent/console security scanning for segmented enterprise networks
**Researched:** 2026-05-25
**Confidence:** HIGH (industry patterns from Tenable, Rapid7/InsightVM, Qualys, Wazuh; verified
across multiple official doc sources)

---

## Scope Reminder

This file covers ONLY the NEW distributed behaviors introduced in v5.4. The entire
single-host scan→score→CBOM→report→dashboard pipeline is already built and is a
hard dependency for everything below.

Primary users: security **consultants** and enterprise security teams running engagements
across segmented networks (DMZ, PCI zones, OT/ICS VLANs, air-gapped enclaves).

---

## Feature Landscape

### 1. Sensor Lifecycle

#### TABLE STAKES

| Feature | Why Expected | Complexity | Pipeline Dependency |
|---------|--------------|------------|---------------------|
| **Enrollment via one-time token / activation key** | Every major distributed scanner (Rapid7, Qualys, Wazuh, Nessus Manager) uses a pre-shared enrollment token or key. Operators assume they can generate a token on the console, hand it to the person deploying the sensor, and that sensor self-registers. No manual DB row insertion. | MEDIUM | Needs a new `sensors` table + enrollment endpoint; reuses v5.3 token-auth pattern |
| **Sensor identity: stable UUID assigned at enrollment** | After enrollment the sensor gets a permanent `sensor_id` (UUID) that survives restarts, IP changes, and reboots. This is the anchor for all result keying. Without it operators cannot correlate historical data to a specific sensor. | LOW | New column on `sensors` table |
| **Heartbeat / last-seen tracking** | Qualys default heartbeat is 15 min; Rapid7 shows green/orange/unknown. Operators need to know whether a sensor is alive before trusting its results. Missing last-seen = product feels unfinished. | LOW | Periodic `POST /api/sensors/{id}/heartbeat` endpoint; write timestamp to `sensors` table |
| **Sensor status visible on console** | Tenable Scan Zones, Rapid7 engine list, Qualys asset inventory all surface agent status. Operators expect a sensors page showing: sensor ID, segment label, last-seen, version, current state (active / stale / offline). | LOW-MEDIUM | New dashboard route; reads `sensors` table |
| **De-registration (unlink sensor)** | Wazuh, Nessus Manager all provide explicit de-registration. Orphaned sensor records accumulate fast in consulting engagements where you deploy and tear down sensors per engagement. Console must let you remove a sensor. | LOW | DELETE endpoint + cascade-nullify orphaned scan results |
| **Sensor version reported to console** | Operators need to know what version each sensor is running to reason about result reliability after upgrades. | LOW | Include version string in heartbeat payload; store in `sensors` table |

#### DIFFERENTIATORS

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Console-driven version skew warning (not hard block)** | Rapid7 enforces exact version match (hard break). Qualys announces EOS. A consulting tool should warn when sensor is N versions behind but not hard-block — a sensor in a locked-down OT segment may lag intentionally. | LOW | Compare semver on heartbeat; emit a `version_skew_warning` flag; display in UI. Do NOT hard-fail. |
| **Engagement-scoped sensors** | In consulting workflows sensors are ephemeral — one per engagement. Supporting an `engagement_label` on sensor enrollment lets the console filter/group by engagement, not just segment. | LOW | Extra optional field at enrollment |

#### ANTI-FEATURES

| Feature | Why It Seems Good | Why It's a Trap | Alternative |
|---------|-------------------|-----------------|-------------|
| **Automatic sensor upgrade push from console** | Reduces ops burden | Requires outbound console→sensor connection (violates no-inbound-access constraint) and introduces version-rollback risk in air-gapped zones. Vendors that do this (Qualys) require internet access or a local mirror. | Document manual upgrade path; sensor checks its own version and logs skew warning. |
| **Agent heartbeat as liveness gate for scans** | Prevents stale data | In air-gapped / low-heartbeat scenarios you would silently block scan imports. A sensor that cannot heartbeat continuously is not broken — it may just be air-gapped. | Decouple heartbeat from scan result acceptance entirely. Accept results regardless of last heartbeat. |
| **Certificate-pinned mTLS enrollment** | "Enterprise-grade security" | Massive operational burden for a consulting tool: PKI setup, cert rotation, broken sensors on expiry. | Enrollment token + HTTPS with console self-signed cert + TOFU is the pragmatic model at this scale. |

---

### 2. Results Flow

#### TABLE STAKES

| Feature | Why Expected | Complexity | Pipeline Dependency |
|---------|--------------|------------|---------------------|
| **Outbound-push results delivery (sensor to console HTTP POST)** | The "no inbound access to segments" constraint makes pull impossible. Every post-2015 distributed scanner supports push from agent to server. Consultants assume this is the default. | MEDIUM | New `POST /api/sensors/{id}/results` ingestion endpoint; reuses v5.3 auth layer and `safe_str`/SSRF discipline |
| **Scan result payload = existing scan JSON schema** | The sensor already has the full single-host pipeline. The result payload should be the scan JSON output (findings + CBOM + scores), not a bespoke new format. Reuse avoids two diverging data models. | LOW | No new schema; sensor runs `run_scan.py`, serializes output, POSTs it |
| **Idempotent re-push by scan_job_id** | A sensor in a spotty-connectivity zone may push the same completed scan twice. The console must deduplicate by `(sensor_id, scan_job_id)` — same job ID is a no-op re-push, not a duplicate scan. | LOW-MEDIUM | Unique constraint on `(sensor_id, scan_job_id)` in ingestion table; HTTP 200 with "already received" on duplicate |
| **Manual export/import for air-gapped enclaves ("sneakernet")** | Tenable explicitly documents this: export `.nessus` file, physically transfer, import to console. Air-gapped environments are real (OT/ICS, classified networks). Consultants will encounter them and need a sanctioned path. | MEDIUM | CLI command: `quirk sensor export-results --output results.quirk.json`; console CLI: `quirk console import-results --sensor-id X --file results.quirk.json`; file is the scan JSON + metadata envelope |
| **Store-and-forward for intermittent connectivity** | Sensors in DMZs or remote sites may have scheduled connectivity windows (e.g., scan runs at 02:00, connectivity window is 06:00–07:00). Sensor queues completed scans and pushes when reachable. | MEDIUM | Local SQLite queue on sensor; push worker retries on schedule; bounded queue depth (configurable, default 5 scans) to avoid unbounded disk growth |

#### DIFFERENTIATORS

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Scan result TTL / staleness flag** | Tenable ignores results older than 14 days. QUIRK should flag results older than N days as stale in the console (configurable; default 30 days for consulting cadence) rather than silently treating old data as current. | LOW | Compute `result_age_days` on ingest; UI badge when stale |
| **Push acknowledgment + delivery receipt** | Console returns a job receipt UUID on successful ingest. Sensor records it locally. Operator can verify `quirk sensor delivery-status` to confirm results landed. Especially valuable for air-gapped sneakernet where the human carrying the file is the delivery channel. | LOW | Include receipt UUID in POST response; sensor logs it |

#### ANTI-FEATURES

| Feature | Why It Seems Good | Why It's a Trap | Alternative |
|---------|-------------------|-----------------|-------------|
| **Streaming / real-time scan events from sensor to console** | Live progress feels responsive | Requires persistent inbound connection or WebSocket from sensor; violates no-inbound constraint; adds complexity for no consulting value (consultants care about the final report, not live progress). | Push completed scan payload only. Console shows last-completed-scan time. |
| **Console-initiated scan trigger (console tells sensor to scan now)** | Centralized scheduling convenience | Requires inbound connection to sensor — the thing distributed scanning is specifically trying to avoid. In a DMZ or OT zone, inbound from console is typically blocked by design. | Sensor runs on its own schedule (cron/Windows Task Scheduler); console scheduling is an optional intent the sensor picks up on its next outbound heartbeat. |
| **Binary result diff at the wire level** | Bandwidth savings | Premature optimization; crypto scan payloads are small (JSON, rarely >500 KB). Diff logic adds fragility for minimal gain in a consulting context. | Push full scan payload; dedup at the DB level. |

---

### 3. Merge Semantics — (segment, host) Keying and Unified Score

This section surfaces explicit design decisions that must be resolved in the v5.4 architecture
doc phase before any code is written.

#### THE CRITICAL KEYING PROBLEM

The same RFC1918 IP (e.g., `10.0.1.50`) can legitimately exist in two different network
segments and be a completely different physical or virtual host. Rapid7 addresses this by
scoping deduplication per-site when asset linking is disabled; Tenable uses scan zones.

**QUIRK must key every finding by `(sensor_id, host)` — never by `host` alone.**

The existing `CryptoEndpoint` model and `fingerprint` SHA256 formula (`host:port::title`)
treat host as globally unique. This is wrong in a distributed deployment. The v5.4 data model
change must prefix or namespace all stored findings with `sensor_id` to prevent cross-segment
collisions.

This is the highest-risk data model change in the project. It must be resolved in Phase 1
(architecture doc) before any ingestion code is written.

#### TABLE STAKES

| Feature | Why Expected | Complexity | Pipeline Dependency |
|---------|--------------|------------|---------------------|
| **`(sensor_id, host, port)` as the unique key for findings** | Without this, `10.0.1.50:443` from the DMZ sensor overwrites `10.0.1.50:443` from the PCI sensor. Operators will see phantom dedup and missing findings. Consultants running multi-segment engagements will distrust the results. | HIGH | Requires schema migration: add `sensor_id` FK to `CryptoEndpoint` (or equivalent); update fingerprint formula; update all queries that join on host/port |
| **Segment label on all stored findings** | Operators need to know which segment a finding came from. "10.0.1.50 — TLS WEAK" means nothing without knowing whether it is the DMZ or the OT VLAN. | LOW | `segment_label` column (human-readable string) on `sensors` table; joined to findings on display |
| **Per-segment CBOM** | Each sensor scan produces its own CBOM. Console stores per-sensor CBOMs. Used for per-segment deliverable to client. | LOW | Already works if findings are keyed by sensor_id; CBOM builder scoped to sensor |
| **Unified/aggregate CBOM (union of all segments)** | A consultant handing a CISO a report wants ONE CBOM for the whole organization. This is the CycloneDX merge problem: combine N per-sensor CBOMs into one. | MEDIUM | Implement a merge pass: union of algorithm components, deduplicated by `(purl OR algorithm_name + quantum_class)` NOT by `bom-ref` (bom-refs are per-document, not globally stable). CycloneDX-CLI merge exists as a reference implementation. |
| **Unified quantum-readiness score** | One authoritative score across all segments is the product core value. Without it, v5.4 has no single deliverable. | HIGH | **Design decision required** (see below) |

#### THE "ONE SCORE ACROSS SEGMENTS" DESIGN QUESTION

This is not a solved problem in the ecosystem. The options are:

**Option A — Union of findings, score computed on merged finding set**
Treat all findings from all sensors as if they came from one scan. The merged finding set feeds
the existing scoring engine unchanged. Consequence: a HIGH finding in a low-priority OT segment
drags down the org-wide score equally with a HIGH in the DMZ. Technically simple; may
misrepresent risk to the client (a 20-host air-gapped OT segment should not dominate the score
for a 2,000-host enterprise network).

**Option B — Per-segment scores; org-wide = weighted average by host count**
Each segment produces its own score. Org-wide score = weighted average (weight = host count or
asset count). Reflects actual risk surface weighting. More complex; requires the merge layer
to track host counts per segment. Matches how consultants actually present findings
(per-zone risk with an org roll-up).

**Option C — Org-wide = weakest-link (minimum segment score)**
"You are only as secure as your least-secure segment." Mathematically simple. Overly punishing
in practice — one misconfigured test sensor would crater the org-wide score. Not recommended.

**Recommendation:** Start with Option A (union, single scoring pass) because it reuses the
existing engine with zero changes. Add a `per_segment_scores` breakdown to the report so
consultants can contextualize the org-wide number. Option B can be a v5.5 follow-on if clients
want weighted scoring. Option C should not be implemented.

**Explicitly surface this decision in the requirements doc for user confirmation.**

#### DIFFERENTIATORS

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Per-segment score gauges in dashboard alongside org-wide gauge** | Consultants present per-zone posture to clients. A per-segment breakdown is a differentiator because commodity tools (Qualys, Tenable) require premium dashboard modules for this. | MEDIUM | New dashboard section; reads per-sensor score from stored results |
| **Cross-segment algorithm frequency map** | "Algorithm X appears in 4 of 5 segments" is a high-value consulting insight. Shows org-wide crypto sprawl. | MEDIUM | Aggregate query across sensor-scoped findings; display in unified CBOM view |
| **Merge conflict annotation on CBOM** | When the same algorithm appears in multiple segments with different quantum-safety classifications (edge case, but possible if different library versions), flag it. | LOW | During merge pass, compare `quantum_safety` for same algorithm; emit a `merge_conflict` annotation |

#### ANTI-FEATURES

| Feature | Why It Seems Good | Why It's a Trap | Alternative |
|---------|-------------------|-----------------|-------------|
| **Automatic cross-segment host dedup ("same host, different IPs")** | Removes duplicate findings for multi-homed hosts | Requires fingerprinting beyond IP (MAC, hostname, cert CN) — unreliable in segmented nets where you may only see the host from one side. False dedup is worse than duplicates. | Do not attempt cross-segment host correlation. Key findings by `(sensor_id, host, port)` always. Let the consultant decide if two records represent the same physical host. |
| **Global finding dedup by algorithm** | Seems to reduce noise | A TLS_RSA_2048 finding on `10.0.1.50` in the DMZ and the same algorithm on `10.0.1.50` in the OT VLAN are NOT the same finding — different hosts. Dedup by algorithm alone destroys the per-segment picture. | Dedup only within a segment (same sensor_id scope). |

---

### 4. Console Visibility

#### TABLE STAKES

| Feature | Why Expected | Complexity | Pipeline Dependency |
|---------|--------------|------------|---------------------|
| **Sensor registry page** | Qualys, Tenable, Rapid7, Wazuh all provide a "manage agents/engines" view. Operators need to know what they have deployed. Minimum: sensor ID, segment label, version, last-seen timestamp, status badge. | LOW | New `/sensors` dashboard route; reads `sensors` table |
| **Per-sensor coverage summary** | What IP ranges / targets does this sensor cover? Operators configure this at enrollment time. Console must reflect it for audit trail. | LOW | `target_ranges` field stored at enrollment; displayed on sensor detail page |
| **Per-segment scan history** | Last-completed scan time per sensor, with link to per-segment findings. Without this, a consultant cannot tell whether the OT sensor ran its scan last night or three weeks ago. | LOW | Join `sensors` to ingested scan records; display on sensor detail page |
| **Aggregate view in existing dashboard** | The existing findings table, score gauges, CBOM viewer, and trend page must work on the unified (merged) dataset by default. Operators should not need to navigate to a new "distributed" section to see the org-wide picture. | MEDIUM | Filter/scope controls on existing dashboard routes; "all segments" as default, segment selector as filter |
| **Per-segment filter on all existing dashboard views** | Consultant wants to show the client only the PCI segment findings. Every existing dashboard view (findings, CBOM, score, trends) must support a segment filter. | MEDIUM | Add `sensor_id` / `segment_label` filter param to all existing `/api/scan/latest`, `/api/findings`, `/api/cbom` endpoints; propagate to UI |

#### DIFFERENTIATORS

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Segment coverage table in PDF report** | Consultants document scope. A table of "segments covered: DMZ (sensor abc123, last scan 2026-05-24), PCI (sensor def456, last scan 2026-05-23)" is a deliverable artifact. | LOW | Rendered in the report/PDF output as a scope table |
| **Offline sensor alert** | If a sensor has not checked in for N hours (configurable; default 24h), flag it in the UI. Saves consultant from discovering mid-engagement that an OT sensor went silent. | LOW | Computed field on sensors list: `now() - last_seen > threshold` |
| **Sensor notes / engagement metadata field** | Free-text notes per sensor ("deployed 2026-05-20, rack B, physical access via John Smith") are valuable for consulting engagements. | LOW | Optional `notes` text column on `sensors` table |

#### ANTI-FEATURES

| Feature | Why It Seems Good | Why It's a Trap | Alternative |
|---------|-------------------|-----------------|-------------|
| **Network topology graph visualization** | "See all your sensors on a diagram" | High UI complexity (graphing library, layout engine), no consulting value added vs. a text table, and topologies are client-confidential. | Sensor registry as a plain table with segment labels. Let the consultant draw the topology in their own deliverable. |
| **Role-based access control per segment** | "Segment owners see only their segment" | Multi-user RBAC is a SaaS/multi-tenant concern. QUIRK is single-tenant. Adding per-segment RBAC is premature complexity that drags toward multi-tenant infrastructure. | Single-tenant, single-user (or shared token per v5.3). Per-segment filtering is a UI convenience, not an access control boundary. |

---

### 5. Windows Sensor Support

#### TABLE STAKES

| Feature | Why Expected | Complexity | Pipeline Dependency |
|---------|--------------|------------|---------------------|
| **Sensor runs as Windows Service or Scheduled Task** | Enterprise Windows environments use Windows Services or Scheduled Tasks as the standard mechanism for background processes. `cron`/`systemd` do not exist. A sensor that requires manual invocation is not deployable in enterprise. Qualys Cloud Agent, Nessus Agent, and Wazuh Agent all install as Windows Services. | HIGH | `scheduler_cmd.py` subprocess loop assumes POSIX; needs Windows host process wrapper (pywin32 `win32serviceutil.ServiceFramework` or NSSM wrapper); Scheduled Task is the fallback for locked-down boxes that block third-party service managers |
| **Frozen executable (no Python required)** | A sensor deployed to a locked-down Windows box that lacks Python must still run. PyInstaller `.exe` or Nuitka is the industry-standard approach. Consultants cannot assume Python is present on every target box. | HIGH | PyInstaller build target for Windows sensor binary; Windows CI runner (GitHub Actions `windows-latest`) to produce and smoke-test the artifact. Note: PyInstaller has a known Defender false-positive problem — document mitigation (code-signing the .exe). |
| **POSIX-ism audit before sensor ships** | `os.path`, `pathlib`, `subprocess`, output dir construction, SQLite path handling — all must work on Windows. Any bash-only operator script the sensor depends on is a blocker. | HIGH | Systematic audit of sensor code paths; replace `os.sep`-sensitive patterns; replace bash scripts with Python equivalents |
| **Windows validation path in CI** | The chaos lab is Linux containers and cannot test a Windows sensor. A CI smoke test must run the sensor binary on a Windows runner, perform a minimal scan, and push results to a Linux console container. Without this, Windows support regresses silently. | MEDIUM | New CI job: `windows-latest` runner + Linux console container; sensor smoke test script in Python (not bash) |
| **Documented Windows install path** | Operators expect step-by-step Windows install instructions as part of the sensor deployment guide. Qualys, Tenable, and Wazuh all provide platform-specific install docs. Missing Windows docs = sensor is "unsupported" in the operator's mind even if it works. | LOW | New section in `docs/operators-guide.md` for Windows sensor installation |

#### DIFFERENTIATORS

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Windows Event Log integration for sensor health** | Enterprise Windows admins monitor via Event Viewer, not a terminal. Sensor startup, scan completion, push success/failure logged to Windows Application Event Log. | LOW | `win32evtlog` via pywin32; only when running as Windows Service |
| **MSI/MSIX installer package** | Enterprise deployments via SCCM/Intune require MSI or MSIX. PyInstaller `.exe` requires manual deployment; MSI enables mass deployment via Group Policy. | HIGH | Separate packaging effort; recommend v5.5 follow-on unless an enterprise user explicitly needs it for v5.4. Do not block v5.4 on it. |

#### ANTI-FEATURES

| Feature | Why It Seems Good | Why It's a Trap | Alternative |
|---------|-------------------|-----------------|-------------|
| **Windows Container / Docker sensor** | "Consistent with Linux deployment" | Enterprise Windows boxes that lack Python are also unlikely to have Docker Desktop (requires Hyper-V, often blocked in locked-down envs). Frozen .exe is more universally deployable. | PyInstaller .exe as primary; Docker as an optional advanced deployment for Windows Server + Docker environments. |
| **PowerShell-based install script** | Windows-native tooling | PowerShell execution policy restrictions are common in locked-down environments; a Python-based installer or simple .exe is more reliable across policy configurations. | Ship a .exe installer; document PowerShell as an optional pre-flight check tool only. |

---

## Feature Dependencies

```
Sensor Enrollment (token + UUID)
    +--required-by--> Results Push (sensor_id in payload)
    +--required-by--> Heartbeat Tracking
    +--required-by--> Sensor Registry (console view)

(sensor_id, host, port) Keying — DATA MODEL CHANGE
    +--required-by--> Per-Segment CBOM
    +--required-by--> Unified CBOM Merge
    +--required-by--> Per-Segment Score
    +--required-by--> Unified Score
    +--required-by--> Segment Filter on Dashboard
    +--BLOCKS-ALL-OTHER-v54-FEATURES (must complete in Phase 1 / arch-doc)

Outbound Push Results Endpoint
    +--requires--> v5.3 auth layer (already built)
    +--requires--> Sensor Enrollment (sensor_id)
    +--required-by--> Store-and-Forward
    +--required-by--> Manual Export/Import (same payload format)

Windows Service Host
    +--requires--> POSIX-ism audit (prerequisite)
    +--requires--> Frozen .exe build (PyInstaller)
    +--required-by--> Windows CI validation path

Unified Score
    +--requires--> (sensor_id, host, port) Keying
    +--requires--> Unified CBOM Merge
    +--design-decision-required--> Scoring methodology (Option A/B/C above)
```

### Critical Dependency Note

The `(sensor_id, host, port)` keying change is a **blocking data model migration** that must
complete before any results ingestion, merge, or scoring code is written. All other v5.4
features are downstream of it. This is why HORIZON puts the architecture doc as Phase 1.

---

## MVP Definition — v5.4

### Must Ship (table stakes, blocking)

- [ ] Architecture doc + `(sensor_id, host, port)` data model design — blocks everything
- [ ] Sensor enrollment via one-time token (console generates, sensor registers)
- [ ] Stable `sensor_id` UUID assigned at enrollment
- [ ] Outbound-push results endpoint (`POST /api/sensors/{id}/results`, v5.3 auth)
- [ ] Idempotent re-push by `(sensor_id, scan_job_id)`
- [ ] Per-segment CBOM stored per sensor
- [ ] Unified CBOM merge (union of components, deduplicated by algorithm identity not bom-ref)
- [ ] Unified org-wide score (Option A: union of findings, existing scoring engine)
- [ ] Heartbeat last-seen tracking + sensor status page on console
- [ ] De-registration (remove sensor)
- [ ] Segment filter on all existing dashboard views
- [ ] Manual export/import for air-gapped sneakernet
- [ ] Windows sensor: POSIX-ism audit + frozen .exe + Windows CI smoke test
- [ ] Windows sensor: Service/Scheduled Task host
- [ ] Store-and-forward queue on sensor (local SQLite, bounded depth)
- [ ] Sensor version skew warning (non-blocking)

### Add When Validated

- [ ] Per-segment score gauges in dashboard (alongside org-wide) — after merge semantics confirmed working
- [ ] Sensor engagement-label at enrollment — after first consulting engagement feedback
- [ ] Cross-segment algorithm frequency map — after first multi-segment report delivered
- [ ] Offline sensor alert (configurable last-seen threshold) — low effort, add when sensor page exists
- [ ] Scan result staleness flag — low effort, add alongside sensor status page
- [ ] Segment coverage table in PDF report — add once per-segment filtering works

### Defer to v5.5

- [ ] MSI/MSIX installer — high effort, enterprise deployment concern, needs explicit demand signal
- [ ] Weighted scoring by host count (Option B) — validate Option A with real consultants first
- [ ] Windows Event Log integration — low value until Windows sensor has real deployment usage
- [ ] Console-scheduled scan intent (sensor picks up on heartbeat) — validate need first

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| (sensor_id, host, port) data model | HIGH | HIGH | P1 — arch blocker |
| Sensor enrollment + UUID | HIGH | MEDIUM | P1 |
| Outbound push + idempotency | HIGH | MEDIUM | P1 |
| Unified CBOM merge | HIGH | MEDIUM | P1 |
| Unified org-wide score | HIGH | LOW (reuse engine) | P1 |
| Windows: POSIX audit + .exe + CI | HIGH | HIGH | P1 |
| Windows: Service/Task host | HIGH | HIGH | P1 |
| Store-and-forward queue | HIGH | MEDIUM | P1 |
| Manual export/import (air-gap) | HIGH | MEDIUM | P1 |
| Sensor status page + last-seen | MEDIUM | LOW | P1 |
| Segment filter on dashboard | MEDIUM | MEDIUM | P1 |
| Per-segment score gauges | MEDIUM | MEDIUM | P2 |
| Version skew warning | MEDIUM | LOW | P2 |
| Staleness flag on results | MEDIUM | LOW | P2 |
| Offline sensor alert | MEDIUM | LOW | P2 |
| Cross-segment algorithm map | MEDIUM | MEDIUM | P2 |
| Segment coverage in PDF report | MEDIUM | LOW | P2 |
| Engagement-label on sensor | LOW | LOW | P2 |
| MSI/MSIX installer | HIGH when needed | HIGH | P3 |
| Weighted scoring (Option B) | MEDIUM | MEDIUM | P3 |

---

## Open Design Questions (require PM decision in v5.4 requirements doc)

1. **Unified score methodology:** Option A (union of findings, single scoring pass), Option B
   (weighted average of per-segment scores by host count), or Option C (weakest-link). This
   document recommends Option A to start, but the tradeoff must be confirmed with the user as PM.

2. **`(sensor_id, host, port)` migration strategy:** The existing `CryptoEndpoint` fingerprint
   formula and all join paths assume global host uniqueness. The migration plan (new column vs.
   namespaced key vs. new table) must be decided in the architecture doc phase before any sensor
   ingestion code is written.

3. **Windows support scope for v5.4 vs. v5.5:** HORIZON explicitly flags this as a "sizing risk
   — balloon" item. The arch-doc phase must decide: (a) full Windows sensor in v5.4 (POSIX audit
   + .exe + Service + CI), or (b) OS-agnostic sensor/console contract in v5.4 + Windows packaging
   as a v5.5 fast-follow. This document recommends committing to full Windows sensor in v5.4
   because the POSIX audit and CI smoke test are best done alongside the sensor implementation,
   not deferred.

4. **Enrollment token expiry:** One-time-use (consumed on enrollment) vs. time-windowed (e.g.,
   60-minute window as Rapid7 does). One-time-use is simpler and more secure for a consulting
   tool where you control the deployment timeline.

5. **Air-gap file format security:** The `results.quirk.json` export file contains scan findings.
   The import path must apply the same `safe_str`/SSRF discipline the v5.3 ingestion layer uses.
   Confirm that the import CLI endpoint applies identical validation to the push endpoint.

---

## Sources

- [Tenable Agent Scanning overview](https://docs.tenable.com/security-center/Content/AgentScanning.htm)
- [Tenable Scan Zones — large enterprise deployment](https://docs.tenable.com/security-center/best-practices/large-enterprise-deployment/Content/ScanZones.htm)
- [Tenable — Export a Scan](https://docs.tenable.com/nessus/Content/ExportAScan.htm)
- [Tenable — Triggered Agent Scans (14-day TTL)](https://docs.tenable.com/vulnerability-management/Content/Scans/TriggeredAgentScans.htm)
- [Rapid7 InsightVM — Configuring Distributed Scan Engines](https://docs.rapid7.com/insightvm/configuring-distributed-scan-engines/) — pairing key (shared secret, 60-min expiry), engine status colors (green/orange/unknown), version must match exactly
- [Rapid7 InsightVM — Linking Assets Across Sites](https://docs.rapid7.com/insightvm/linking-assets-across-sites/) — asset dedup keys: hostname + IP + MAC + UUID; per-site vs cross-site linking modes; same-IP problem
- [Rapid7 InsightVM — Planning Scan Engine Deployment](https://docs.rapid7.com/insightvm/planning-your-scan-engine-deployment/) — scan engines do not store data; push immediately to console
- [Qualys — Heartbeat interval (15-minute default)](https://success.qualys.com/support/s/article/000006611)
- [Qualys — Agent Scan Compatibility Matrix](https://docs.qualys.com/en/conn/latest/scans/qualys_agent_scan_compatibility_matrix.htm)
- [Wazuh — Agent Enrollment](https://documentation.wazuh.com/current/user-manual/agent/agent-enrollment/index.html) — enrollment via agent config or manager API; client key encryption; agent version must not exceed manager version
- [CycloneDX sbom-combiner](https://github.com/CycloneDX/sbom-combiner) — merge utility (archived 2024); dedup by name+version is suboptimal; purl is the correct dedup key
- [CycloneDX CLI](https://github.com/CycloneDX/cyclonedx-cli) — merge subcommand; known issue: does not remove duplicates
- [Running Python as Windows Service — NSSM](https://www.mssqltips.com/sqlservertip/7325/how-to-run-a-python-script-windows-service-nssm/) — NSSM as Windows service wrapper; pywin32 as alternative for locked-down boxes
- [Idempotency in distributed systems](https://aloknecessary.github.io/blogs/idempotency-distributed-systems/) — request fingerprint / idempotency key patterns

---

*Feature research for: v5.4 Distributed On-Prem Scanner Architecture (QU.I.R.K.)*
*Researched: 2026-05-25*
