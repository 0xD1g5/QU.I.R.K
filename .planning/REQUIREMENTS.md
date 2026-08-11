# Requirements: QU.I.R.K. — v5.11 Discovery at Scale + Backlog Drain

**Defined:** 2026-08-03
**Core Value:** Produce a complete, defensible cryptographic inventory with a CBOM deliverable
and quantum-readiness score that a consultant can hand to a client in under two hours.

## v5.11 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Discovery at Scale (anchor — closes backlog 999.90)

- [x] **DISC-01**: Operator can submit a large (>1024-host) IP range scan via the dashboard and
      have discovery actually complete, instead of being rejected (422) or timing out at 300s
- [x] **DISC-02**: A single unresponsive subnet/batch within a large range does not fail the
      entire discovery job — other batches still complete and get scanned
- [x] **DISC-03**: Discovery uses a TCP-SYN/ACK liveness pre-pass (not ICMP) to skip full port
      sweeps on non-responsive hosts, preserving reliability in segmented/firewalled networks
- [x] **DISC-04**: Operator sees incremental discovery progress (batch N of M / hosts checked)
      while a large-range scan runs, instead of silence until success or failure
- [x] **DISC-05**: Discovery timeout and parallelism scale to each batch's size rather than one
      fixed value guessed for any range size
- [x] **DISC-06**: The CLI's `--discovery nmap` path gets the same chunking fix as the
      dashboard, via one shared implementation
- [x] **DISC-07**: A scan report/summary discloses how many hosts were undetermined
      (unreachable/filtered) vs. successfully scanned

### Backlog Drain (stabilization tail)

- [x] **DRAIN-01**: A `--resume-scan-id` continuation no longer skips OT-only hosts when the
      SSH stage was already checkpointed complete
- [x] **DRAIN-02**: The hardware CVE table has an explicit, documented decision on BACnet key
      coverage (real vendor entry added, or formally marked lab-only/out of scope)
- [x] **DRAIN-03**: The 2026-05-27 audit ledger has zero rows with an undecided or stale
      disposition — already-fixed rows flipped to `[x] closed` with commit citations, WR-02/CD-03
      get a final fix-or-accept-risk call
- [x] **DRAIN-04**: The deferred human-UAT ledger in STATE.md is re-triaged — actionable items
      (e.g., the Windows Authenticode production cert) resolved or explicitly re-confirmed as
      still blocked

## Future Requirements

Deferred to future release. Tracked but not in current roadmap.

### Discovery at Scale (v5.11.x / v5.12+)

- **DISC-08**: Sub-batch (mid-discovery) checkpoint/resume granularity — only worth the
  `scan_checkpoints` schema extension if real-world discovery batches start taking long enough
  to make restart-from-batch-1 genuinely costly; not evidenced today
- **DISC-09**: Segmented-network chaos lab profile for empirical chunking/partial-result
  regression coverage — heavier scope (new Docker network topology), deferred past the core fix

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Sub-batch resumability within a single discovery invocation | `--resume-scan-id` restarts discovery from batch 1 on a resumed scan; batches are cheap (~30-60s) relative to the downstream phases the checkpoint system was built to protect — accepted boundary, not a gap |
| Masscan / custom raw-socket scanner adoption | New heavy dependency, needs root/raw sockets — conflicts with QU.I.R.K.'s existing non-admin-friendly `-sT` design constraint; the actual bottleneck is sparse-range waste, not raw packet throughput |
| ICMP-based liveness pre-pass | Regresses the deliberate `-Pn` decision (ICMP unreliable in segmented/firewalled corporate networks) — would silently drop real hosts from a consulting deliverable |
| Fully parallel/concurrent batch execution across all CPU cores | Multiplies outbound connection/packet rate uncontrollably — IDS/IPS false-positive risk on a client's network; complicates progress reporting and error attribution |
| Real-time streaming progress (websockets/SSE) for discovery | Scope increase disproportionate to the anchor fix; existing `ScanJob` polling loop already handles "a few batches over a few minutes" granularity |
| Undetermined-host report disclosure, segmented-network chaos lab profile | Both are valid P2 add-ons but explicitly deferred to v5.11.x per user confirmation — v5.11 stays scoped to the P1 core fix + drain tail (undetermined-host disclosure is IN as DISC-07; chaos lab profile is OUT as DISC-09) |
| SaaS multi-tenancy | Still parked — no business-model signal, unchanged since v5.4 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DISC-01 | Phase 144 | Complete |
| DISC-02 | Phase 144 | Complete |
| DISC-03 | Phase 145 | Complete |
| DISC-04 | Phase 146 | Complete |
| DISC-05 | Phase 146 | Complete |
| DISC-06 | Phase 146 | Complete |
| DISC-07 | Phase 146 | Complete |
| DRAIN-01 | Phase 147 | Complete |
| DRAIN-02 | Phase 147 | Complete |
| DRAIN-03 | Phase 147 | Complete |
| DRAIN-04 | Phase 147 | Complete |
