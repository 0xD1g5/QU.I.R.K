# Phase 147: Backlog Drain — Lifecycle & Ledger Tail - Context

**Gathered:** 2026-08-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Four independent, small debt items accumulated since v5.8/v5.10, unrelated to the Phases 144–146
discovery-at-scale work and safe to sequence in parallel or after:

1. **DRAIN-01** — Fix the `--resume-scan-id` outer-gate skip bug: a resumed scan whose SSH stage
   was already checkpointed complete can still skip OT-only (Modbus/BACnet, no-SSH) hosts.
2. **DRAIN-02** — Give the hardware CVE table an explicit, documented decision on BACnet key
   coverage.
3. **DRAIN-03** — Close out the 2026-05-27 audit ledger to zero undecided/stale rows, with a final
   fix-or-accept-risk call on WR-02 and CD-03 specifically.
4. **DRAIN-04** — Re-triage the deferred human-UAT ledger in STATE.md; resolve or re-confirm each
   actionable item (e.g. Windows Authenticode production cert).

This is a drain phase, not a feature phase — no new capability, no new user-facing surface.

</domain>

<decisions>
## Implementation Decisions

User was offered a multiSelect of discussion areas (BACnet CVE coverage, audit-ledger
fix-or-accept-risk calls, Authenticode cert status) and chose **"None — proceed straight to
research/planning."** No implementation choices were locked by explicit user input. The findings
below are Claude's codebase reconnaissance during discussion, handed to research/planning as
starting material — not user-confirmed decisions. Research and planning should treat the open
questions in each subsection as things to resolve (with a fix-or-accept-risk recommendation), not
as settled.

### DRAIN-01 — Resume-checkpoint bug
- Root cause is already diagnosed in `v5.10-MILESTONE-AUDIT.md` (see canonical refs): the outer
  gate `_run_ot_supplemental_phase()` (141-11's fix) only runs in `run_scan.py`'s non-resume
  `else` branch of the SSH-stage handling. A `--resume-scan-id` continuation from a checkpoint
  where `ssh` was already marked complete never routes through the supplemental OT-only host set.
  Fix is mechanical: route the supplemental-phase call so it also fires on the resume path when
  the ssh stage is checkpointed-complete but the OT-only host set hasn't been probed yet.
- Per CLAUDE.md's chaos-lab-maintenance rule, if the fix touches lab-exercisable behavior,
  research/planning should consider whether a regression scenario belongs in the OT/ICS chaos lab
  profile or is adequately covered by a unit/integration test at the `run_scan.py` resume-path
  level.

### DRAIN-02 — BACnet CVE key coverage
- Traced end-to-end: `quirk/scanner/bacnet_scanner.py` reads BACnet `vendorID` (a raw numeric
  string, e.g. `"5"`) and `model-name` (a raw device string, e.g. `"FX16"`). When the device's
  primary vendor is `"Unknown"`, `quirk/scanner/hardware_scanner.py` (~L499-501) copies these raw
  BACnet values straight into `device.vendor` / `device.model`.
- `quirk/scanner/hw_cve.py`'s `CVE_TABLE` is keyed on `(vendor_name, product_family)` tuples, e.g.
  `("Johnson Controls", "Facility Explorer")` — added specifically to cover the FX16 field
  controller family per a documented research note (RESEARCH.md Open Question 1, quoted inline in
  `hw_cve.py` L123-129).
- **There is no BACnet vendor-ID → vendor-name resolution layer.** `correlate_device()` is called
  with the raw numeric-string vendor (`"5"`) and raw model string (`"FX16"`), which will never
  match the `("Johnson Controls", "Facility Explorer")` key. Net effect: BACnet-identified devices
  get **zero CVE correlation today**, despite an entry existing in the table that was seemingly
  intended to cover exactly this case.
- Two paths forward for research/planning to weigh:
  (a) build a small BACnet vendor-ID → vendor-name lookup (ASHRAE/BACnet maintains a public
      vendor ID registry) so `device.vendor` becomes a real name before `correlate_device()` is
      called — this makes the existing Facility Explorer entry actually reachable;
  (b) formally document current behavior as lab-only/out-of-scope with written rationale (e.g.,
      "BACnet vendor-ID resolution deferred — needs its own registry-ingestion pass") and leave
      the Facility Explorer entry as dead weight or repurpose/remove it.
- Success criterion (roadmap) accepts either outcome as long as the decision is explicit and
  documented — this is a real fix-or-defer call, not purely mechanical.

### DRAIN-03 — Audit ledger closure
- Ledger file: `.planning/audit-2026-05-27/AUDIT-TASKS.md`. Rows currently `[ ]` (not closed):
  SP-06 (wont-fix v5.7), WR-02 (CORS origin/port), WR-03 (rate-limit bucket eviction), WR-04
  (create_job target validation), WR-07 (wont-fix v5.7), CD-03 (SSRF TOCTOU/DNS rebinding), CD-04
  (sensor_id re-validation), CD-07 (SIEM SSRF/format guard), CD-08 (enroll race window), CD-09
  (CEF space escaping), FE-02 (dashboard token in localStorage), UI-01 (HTML report cover-page
  whitespace).
- All are labeled `deferred → v5.8` or `wont-fix vX.Y` from the 2026-05-27 review — several v5.8+
  milestones have shipped since, so some rationale may now be stale or the underlying issue may
  already be fixed by later work (e.g., FE-02's note mentions a planned "v5.8: sessionStorage
  migration + CSP header" — worth checking whether that landed). Re-verifying each row's current
  truth against the live codebase is research work, not something the user needed to weigh in on.
- **Roadmap explicitly calls out only WR-02 and CD-03 for a fresh "fix-or-accept-risk" call** —
  the other ~10 rows just need re-verification and closure with commit citations (or continued
  accept-risk with refreshed rationale if truly still applicable), not a new decision.
- WR-02: default CORS origins omit the port in `quirk/dashboard/server.py`, so real-origin
  requests never match. CD-03: SSRF TOCTOU/DNS-rebinding gap in `quirk/util/url_allowlist.py`
  between the allowlist validator's resolve and the actual urllib/httpx/smtplib resolve at
  connection time — partially mitigated by Phase 123's `PinnedIPAdapter` + `resolved_ip`, but a
  full resolve-and-connect-to-IP-with-SNI fix needs an httpx transport overhaul (noted as
  "acceptable in on-prem threat model" in a code comment). Both are real fix-vs-accept-risk
  tradeoffs for research/planning to size and recommend, then confirm with the user before
  locking in the plan.

### DRAIN-04 — Deferred human-UAT ledger re-triage
- STATE.md's `## Deferred Items` table (lines ~166-193) is the primary ledger to re-triage. It
  currently lists: Phase 132/135/137 verification gaps, UAT-118-01 (Windows install walkthrough),
  UAT-114-03 (operators-guide visual review), UAT-93/95/96 (getpass/PDF/ldaps/fuzzing
  environment-gated items), UAT-101–105 (live delivery infra), Phase 143 items (2 pending
  scenarios + verification gap), and the healthcare-vertical-merge stale-bookkeeping note.
- The roadmap's example item — **"the Windows Authenticode production cert"** — is *not* currently
  listed in STATE.md's Deferred Items table directly; it lives in
  `.planning/milestones/v5.10-MILESTONE-AUDIT.md`'s "Human-UAT Outstanding" section: "mechanism
  SECURED (7/7 threats closed per `/gsd-secure-phase`), awaiting real secrets + a live push to
  fully close runtime confirmation." Research/planning should fold this into STATE.md's ledger
  proper as part of the re-triage (it's currently only tracked in an archived milestone-audit
  file, which is easy to lose track of).
- **Only the user can resolve whether a production Authenticode signing cert now exists** — that's
  the one item in this whole phase that is a pure external-state fact, not a codebase question.
  Flag this explicitly at plan/execute time rather than guessing.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & requirements
- `.planning/ROADMAP.md` §"Phase 147: Backlog Drain — Lifecycle & Ledger Tail" — success criteria
- `.planning/REQUIREMENTS.md` DRAIN-01..04 — requirement text

### DRAIN-01 (resume-checkpoint bug)
- `.planning/milestones/v5.10-MILESTONE-AUDIT.md` — "RESUME-OT-SUPPLEMENTAL-SKIP" tech-debt entry
  (full root-cause description) and "Phase 141's Gap-Closure History" section
- `.planning/ROADMAP.md` line ~470 — backlog entry cross-reference

### DRAIN-02 (BACnet CVE coverage)
- `quirk/scanner/hw_cve.py` — `CVE_TABLE`, `correlate_device()`, staleness gate; see the inline
  comment at L123-129 documenting the Facility Explorer/FX16 keying decision
- `quirk/scanner/bacnet_scanner.py` — raw `bacnet_vendor`/`bacnet_model` extraction (numeric
  vendor ID, raw model string)
- `quirk/scanner/hardware_scanner.py` ~L490-501 — where BACnet raw values get copied into
  `device.vendor`/`device.model` when primary vendor is `"Unknown"`

### DRAIN-03 (audit ledger)
- `.planning/audit-2026-05-27/AUDIT-TASKS.md` — the ledger itself; rows WR-02 (line 81) and CD-03
  (line 91) are the two needing a fresh fix-or-accept-risk call
- `quirk/dashboard/server.py` — CORS origin config (WR-02)
- `quirk/util/url_allowlist.py` — SSRF allowlist validator + `PinnedIPAdapter`/`resolved_ip`
  (CD-03; code comment documents the partial-mitigation rationale)

### DRAIN-04 (deferred UAT ledger)
- `.planning/STATE.md` §"Deferred Items" (lines ~166-193) — the ledger to re-triage
- `.planning/milestones/v5.10-MILESTONE-AUDIT.md` §"Human-UAT Outstanding" — Authenticode item's
  actual current location (not yet folded into STATE.md)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/qramm/model_meta.py` and `quirk/compliance/__init__.py` establish the
  curated-catalog + staleness-gate + status-report pattern that `quirk/scanner/hw_cve.py` already
  follows (Phase 142). Any BACnet vendor-ID registry addition (DRAIN-02 option (a)) should mirror
  this same triad rather than inventing a new pattern.

### Established Patterns
- `correlate_device()` deliberately does NOT gate on `vendor == "Unknown"` — that's a call-site
  responsibility (documented in `hw_cve.py` docstring, citing RESEARCH.md Pitfall 4). Any DRAIN-02
  fix must preserve this contract and gate/resolve vendor names before the call, not inside it.

### Integration Points
- `correlate_device()` has exactly two call sites: `quirk/dashboard/api/routes/scan.py` L788 and
  `quirk/reports/writer.py` L278. A vendor-ID resolution fix needs to land before both, or in a
  shared helper both call.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — user deferred all four items to research/planning without discussion.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope (user declined to discuss further; no scope-creep
ideas surfaced).

</deferred>

---

*Phase: 147-Backlog Drain — Lifecycle & Ledger Tail*
*Context gathered: 2026-08-10*
