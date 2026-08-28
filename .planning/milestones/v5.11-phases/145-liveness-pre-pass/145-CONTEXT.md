# Phase 145: Liveness Pre-Pass - Context

**Gathered:** 2026-08-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a TCP-SYN/ACK liveness check (`-sn -PS<port-list>`) ahead of each batch's existing full port
sweep in the Phase 144 batch loop (`run_scan.py` ~line 1302). Hosts the pre-pass finds
non-responsive are skipped from the expensive `-sT` sweep — but recorded, not silently dropped —
and any silent privilege downgrade of the pre-pass itself (SYN probe → connect-style probe when
not running as root) is explicitly detected and disclosed rather than degrading invisibly.

Out of scope for this phase (explicitly deferred per ROADMAP.md phase sequencing): full
undetermined-host counts in the operator-facing scan report/summary (DISC-07 / Phase 146),
per-batch progress disclosure, timeout/parallelism scaling by batch size, and CLI/dashboard
shared-implementation parity work (all Phase 146 — DISC-04/05/06). This phase produces the raw
data Phase 146 will surface, but does not build the surfacing itself.

</domain>

<decisions>
## Implementation Decisions

### Privilege-fallback disclosure
- **D-01:** When the `-PS` SYN pre-pass silently degrades to a connect-based probe because QUIRK
  is not running with raw-socket privileges, disclose it the same way `_emit_missing_extra_advisory`
  (`run_scan.py:167`) already discloses other degraded-mode conditions: a logger message AND a
  CryptoEndpoint advisory row, not console-only logging. This keeps the fallback visible to anyone
  reading the scan artifact/report, not just live console output.
- **D-02:** Determine privilege level once per scan (e.g. `os.geteuid() == 0` on POSIX), before the
  batch loop starts, and reuse that single result for every batch's fallback-advisory decision.
  Root/non-root is a process-level fact that doesn't change mid-run — no per-batch re-derivation
  from nmap's own output is needed.
- **Rejected:** hard-failing the batch on fallback detection — no existing precedent in this
  codebase treats a privilege gap this strictly (even nmap-binary-absent only hard-fails for wide
  port scopes, not for privilege gaps); log-only was also rejected because it leaves the fallback
  invisible to anyone who only reads the report.

### Liveness-probe port scope
- **D-03:** The `-PS<port-list>` pre-pass reuses the batch's own full-sweep port list
  (`ports_for_nmap` / `port_spec_override`) rather than a small fixed fast-probe subset (e.g.
  80,443,22). A host reachable only on a sweep-scoped port outside a fixed subset (e.g. 636 LDAPS,
  5671 AMQPS) must not be wrongly marked non-responsive and skipped — that would undermine DISC-03's
  reliability goal in exactly the segmented/firewalled networks it's meant to help. The
  optimization's cost now scales with how targeted the scan already is (narrow "Common TLS" scope
  → narrow, fast pre-pass; `--top-ports 1000`/`-p-` wide scope → costlier but accurate pre-pass).

### Non-responsive host accounting (interim, pre-Phase-146)
- **D-04:** Record each liveness-skipped host as a CryptoEndpoint row (host, port=0), mirroring the
  Phase 144 batch-failure precedent (`error_endpoints.append(...)`, `run_scan.py:1318-1324`) — not a
  bare `run_stats` counter and not log-only. This gives Phase 146 a ready-made queryable source for
  DISC-07's undetermined-host disclosure with per-host identity already intact, rather than 146
  having to rebuild host-level tracking from scratch.
- **D-05:** Use a distinct `scan_error_category` for liveness-skip rows (e.g. `"liveness_skip"`),
  separate from Phase 144's batch-failure category (`"exception"`). These are semantically different
  outcomes — one host individually non-responsive vs. an entire batch subprocess failing — and
  Phase 146's undetermined-count reporting will need to tell them apart (or at least tally them
  separately) rather than have that disambiguation pushed downstream.

### Non-root verification approach
- **D-06:** Verify the pre-pass and its fallback-detection behavior against a real non-root nmap
  run via a chaos lab scenario, gated as a documented human-UAT checkpoint — consistent with how
  this project already gates other environment-dependent checks (e.g. UAT-118-01, live Windows host,
  tracked in STATE.md). Automated verification (unit/integration tests with mocked subprocess calls)
  covers everything up to that point; the final non-root confirmation is a human-run pass the user
  signs off on. A CI-runner-based automated non-root job was considered and set aside as more
  implementation work than this phase needs — it can be revisited later if the manual pass proves
  insufficient.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — DISC-03 (this phase's requirement); DISC-04..07 for what's
  explicitly deferred to Phase 146
- `.planning/ROADMAP.md` §"Phase 145: Liveness Pre-Pass" — goal, success criteria, dependency on
  Phase 144
- Phase 144 (Chunked Discovery Core, v5.11) — phase artifacts lost in the documented v5.12-open
  incident, see `.planning/milestones/v5.11-phases/ARCHIVE-MANIFEST.md`; shipped summary in
  `.planning/milestones/v5.11-ROADMAP.md`'s "Phase 144" section — the batch loop this phase's
  pre-pass slots into; D-04's `ScanCheckpoint`/partial-failure precedent this phase's D-04/D-05
  extend

### Code this phase touches directly
- `run_scan.py` lines ~1290-1330 — the Phase 144 sequential batch loop (`for batch in
  _chunked(host_iter, _MAX_HOSTS_PER_CIDR)`); the liveness pre-pass slots in immediately before
  each batch's `run_nmap_discovery()` call
- `run_scan.py:167` — `_emit_missing_extra_advisory()`, the advisory-row-plus-logger precedent D-01
  follows for privilege-fallback disclosure
- `run_scan.py:1318-1324` — the Phase 144 batch-failure `error_endpoints.append(CryptoEndpoint(...))`
  pattern D-04 mirrors for liveness-skip accounting
- `quirk/discovery/nmap_provider.py` — `run_nmap_discovery()` and `_default_nmap_args()`; the new
  pre-pass likely needs a sibling function (e.g. `run_nmap_liveness_check()`) using `-sn -PS<ports>`
  rather than modifying the existing `-sT` sweep call
- `quirk/discovery/nmap_parser.py` — `parse_nmap_xml()` currently only extracts open ports from
  `state="open"`; the pre-pass needs host-up/down state from `<host><status state="...">`, which
  this parser does not currently expose (it only reads host status as a filter, not a return value)
- `quirk/models.py` — `CryptoEndpoint` model, `scan_error_category` field — D-05's new
  `"liveness_skip"` category value goes here

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_emit_missing_extra_advisory()` (`run_scan.py:167`) — logger + CryptoEndpoint advisory-row
  pattern, reused as-is in spirit for D-01's privilege-fallback disclosure
- Phase 144's `error_endpoints.append(CryptoEndpoint(...))` batch-failure pattern
  (`run_scan.py:1318-1324`) — direct precedent for D-04's liveness-skip row shape

### Established Patterns
- `_default_nmap_args()` in `nmap_provider.py` already hardcodes `-sT` (non-admin-friendly TCP
  connect) for the full sweep, specifically so QUIRK never needs root for the sweep itself. Only
  the new liveness pre-pass (`-PS`) introduces any privilege sensitivity — the sweep's own
  arguments are unaffected by this phase.
- No existing precedent for privilege detection (`os.geteuid()` or equivalent) anywhere in the
  codebase today — this is genuinely new for D-02, not a pattern to mirror.
- No existing `-sn`/ping-sweep/liveness code anywhere in `quirk/discovery/` — this phase is
  greenfield for the liveness mechanism itself, though it reuses `nmap_provider.py`'s existing
  subprocess/XML-output plumbing as scaffolding.

### Integration Points
- The pre-pass sits strictly inside the Phase 144 per-batch loop, before `run_nmap_discovery()` is
  called for that batch's sweep — it filters `batch` down to only responsive hosts before the sweep
  call, not before the loop as a whole.
- `nmap_parser.py::parse_nmap_xml()` will need either a new sibling parser function or an extension
  to also return per-host up/down status (currently it silently treats non-"up" hosts as invisible
  rather than surfacing them) — this is an implementation detail for research/planning, not
  re-litigated here, but the gap is worth flagging since it's not just "call the same parser again."

</code_context>

<specifics>
## Specific Ideas

No UI/UX references — this phase is backend/reliability-only, matching Phase 144's shape (no
dashboard changes; DISC-04's progress UI is Phase 146). All four discussed gray areas were resolved
by picking the recommended, precedent-matching option in each case: advisory-row disclosure over
log-only or hard-fail, full-port-list probe scope over a fast fixed subset, CryptoEndpoint rows with
a distinct category over a bare counter, and chaos-lab human-UAT verification over a new CI job.

</specifics>

<deferred>
## Deferred Ideas

- CI-runner-based automated non-root verification job — considered as an alternative to the
  chaos-lab human-UAT approach (D-06) and set aside as more implementation work than this phase
  needs; could be revisited if the manual verification pass proves insufficient or too slow to
  repeat regularly.
- Per-batch (rather than once-per-scan) privilege re-derivation from nmap's own output — considered
  and rejected for D-02; root/non-root doesn't change mid-scan, so per-batch re-checking would add
  parsing complexity for a static fact.

### Reviewed Todos (not folded)
None — no pending todos matched Phase 145 (`gsd-sdk query todo.match-phase 145` returned zero
matches).

</deferred>

---

*Phase: 145-Liveness Pre-Pass*
*Context gathered: 2026-08-10*
