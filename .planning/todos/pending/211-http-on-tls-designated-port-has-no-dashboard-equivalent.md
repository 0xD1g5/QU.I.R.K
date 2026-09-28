---
type: todo
created: 2026-09-28
source: 211-04 (DENOM-04 residual coverage gate) — filed per plan Task 3, disposition
  "unbridgeable-latent-divergence" in quirk/dashboard/api/finding_title_bridge.py::SCORING_TITLE_DISPOSITIONS
priority: low  # measures 0 on the reference estate; disclosed, not blocking
requirement: null
resolves_phase: null
tag_blocking: false  # see "Tag-blocking verdict" below
---

# "HTTP on TLS-designated port" has no dashboard equivalent — latent Hygiene divergence

**Filed as required by 211-04's must-haves**: every `unbridgeable-latent-divergence` disposition
must carry a tracked todo naming the affected counter, the scoring category and weight, the estate
condition that makes it non-zero, why bridging is unsafe, and two candidate fix shapes.

## The gap

`quirk/intelligence/evidence.py:512` — `http_on_tls_port_targets = _finding_targets(finding_list,
"HTTP on TLS-designated port")` — feeds `http_on_tls_port_count`, which
`quirk/intelligence/scoring.py:443` reads as `http_on_tls_count`, and
`quirk/intelligence/scoring.py:493` weights into the **Hygiene** category:

```python
("HTTP on TLS-designated ports", -_ratio(http_on_tls_count, endpoint_denom) * w["hygiene_http_on_tls_ratio"]),
```

`hygiene_http_on_tls_ratio = 16.0` (`scoring.py:88`), inside a `score_cap = 25.0` category
(`scoring.py:327`) — a single-finding penalty of up to `16.0 / endpoint_denom * 100`... i.e. a
material fraction of the 25-point Hygiene ceiling, not a rounding-error term.

**No dashboard emission site exists for this CLI title.** Confirmed two ways: (1) a `grep -n` for
`"HTTP on TLS-design"` and `"designated"` against `quirk/dashboard/api/routes/scan.py` returns zero
hits; (2) `tests/test_evidence_scoring_title_coverage.py`'s run-time CLI-vocabulary extractor
(which unions the `title=` kwarg form and the `f["title"] = ` rewrite form — this title is emitted
**only** via the rewrite form, `findings_evaluator.py:433`) has no dashboard-side counterpart
extractor find it either, because `tests/test_finding_title_bridge.py`'s own
`test_every_dashboard_emission_site_is_dispositioned` gate has never seen this title from the
dashboard side in the first place — it isn't there to disposition.

The CLI condition itself (`findings_evaluator.py:414-436`, inside `_postprocess_findings`) upgrades
a `"Plaintext HTTP service detected"` finding to `"HTTP on TLS-designated port"` when: the port is
in `tls_ports` (`WELL_KNOWN_TLS_PORTS` unioned with the operator's `cfg.scan.tls_designated_ports`
override — `quirk/config_template.yaml:69`, empty by default), AND the endpoint's protocol
classifies as `HTTP` (not `TLS`) on that port, AND it is NOT one of the `MTLS_REQUIRED` /
`TLS_HANDSHAKE_FAILED` / `TIMEOUT` blocker categories (those upgrade to different titles instead).
In plain terms: **a service that responded in plaintext HTTP on a port the operator or QUIRK's
well-known-port table expects to be TLS/HTTPS.**

## Why it did not show up in Phase 210's 17-vs-18 measurement

It measured **0 on both pipelines** on the reference (`multihost` chaos lab) estate — the report
and dashboard `http_on_tls_port_count`-equivalent values happened to coincide at zero, which is why
this divergence was invisible in the live comparison that drove Phase 210/211's investigation. That
coincidence is NOT evidence of correctness on the dashboard side: the dashboard pipeline is
**structurally** incapable of ever producing a non-zero value for this counter, regardless of the
estate, because `build_evidence_summary` (shared by both pipelines) can only match the CLI title via
a finding that carries it, and the dashboard finding generator never emits it under any endpoint
condition. A report-side scan finding even ONE plaintext-HTTP service on a TLS-designated port would
reproduce a live report-vs-dashboard divergence in Hygiene, identical in shape to the already-fixed
`plaintext_http_count` (211-02) and `legacy_tls_count` (211-03) defects — this is the third leg of
that same defect class, currently dormant rather than closed.

## Estate condition that makes it non-zero

Any endpoint where: (a) the port is in `WELL_KNOWN_TLS_PORTS` (443, 8443, 9443, 10443, 4433, 5001)
**or** the operator's `tls_designated_ports` config override, **and** (b) the service on that port
responds in plaintext HTTP rather than negotiating TLS, **and** (c) the connection does not fail
with an `MTLS_REQUIRED`/`TLS_HANDSHAKE_FAILED`/`TIMEOUT` blocker reason (those are separately
disposed under different titles that carry their own — currently unverified — parity status). This
is a realistic real-world misconfiguration (a service moved off its HTTPS port default without
updating firewall/LB expectations), not a synthetic edge case; it simply did not occur in the
reference multihost lab's current container set.

## Why bridging is unsafe

No dashboard emission site exists to bridge FROM. Phase 202's `schemas.py:126-129` "DO NOT UNIFY"
comment explicitly forbids adding a synthetic dashboard-side title purely to satisfy a bridge
entry — the two generators are independently maintained by design (operator console vs. client
deliverable), and inventing a title in one to make a mapping table balance is exactly the kind of
change that comment exists to block. A real fix must change WHAT the dashboard measures, not
paper over the absence with a translation-table trick.

## Candidate fix shapes

1. **Add a dashboard emission site.** `quirk/dashboard/api/routes/scan.py`'s
   `findings_for_endpoint` would need a new branch mirroring
   `findings_evaluator.py:414-436`'s logic: given `ep.protocol == "HTTP"` and `ep.port` in the
   TLS-designated set, emit a dashboard-vocabulary title (e.g. `"HTTP service on TLS-designated
   port"`) and add a `DASHBOARD_TITLE_BRIDGE` entry mapping it to the CLI's `"HTTP on
   TLS-designated port"`. This preserves the two-vocabulary design (operator-facing wording differs
   from client-facing wording) while giving the dashboard pipeline a real signal to bridge.
   Requires plumbing the TLS-designated-ports config value to wherever `findings_for_endpoint`
   currently resolves its config (need to verify config threading at execution time — not yet
   checked as part of this todo's filing).

2. **Make the counter endpoint-derived, mirroring 211-03's `legacy_tls_count` shape.** Since the
   condition is fully expressible from endpoint fields alone (`protocol == "HTTP"`, `port` in the
   TLS-designated set, no MTLS/handshake/timeout blocker) rather than requiring the finding-upgrade
   machinery, `evidence.py` could compute `http_on_tls_port_count` directly from `endpoint_list` in
   its existing single pass, the same way `legacy_tls_count` and `motion_email_plaintext_count`
   already work. This is the shape that eliminated the DEFECT CLASS rather than one instance of it
   in 211-03, and is the disposition-ledger's own recommendation (see
   `finding_title_bridge.py::SCORING_TITLE_DISPOSITIONS["mTLS required"]`'s `endpoint-derived`
   sibling entry for the established pattern). **Recommended shape** — narrower diff, no new
   dashboard-side title/config-threading work, and directly precedented in this same phase.

## Feasibility & Effort

- **Feasibility: LIKELY** for shape 2 (endpoint-derived) — the exact mechanical pattern (single-pass
  endpoint-field counter, `scoring.py`'s `evidence.get(counter, fallback)` read unchanged) was
  applied successfully in 211-03 (`c1245a55`) for `legacy_tls_count`, a structurally identical
  shape (a counter previously proxied from finding-severity counts, now computed from endpoint
  fields in the same pass that already computes `tls_enum_success_count` /
  `assessable_endpoint_count`). Shape 1 (dashboard emission site) is **UNKNOWN** — not yet verified
  whether `findings_for_endpoint` has straightforward access to `cfg.scan.tls_designated_ports` at
  execution time (checked: `findings_evaluator.py`'s `_postprocess_findings` receives `cfg`
  directly as a parameter; `quirk/dashboard/api/routes/scan.py`'s config threading for
  `findings_for_endpoint` was not inspected as part of filing this todo).
- **Effort: S** for shape 2 — one counter, one existing loop, one `scoring.py` line already reads
  the right key name (`http_on_tls_port_count`) via the existing `evidence.get(..., 0)` fallback
  pattern, so no `scoring.py` change is even required, only `evidence.py`'s counter computation.
  Effort for shape 1 is **UNKNOWN** pending the config-threading check above; plausibly S-M.
  Either shape needs a pinned-oracle cross-vocabulary parity test extending
  `tests/test_evidence_finding_vocabulary_parity.py`, per this phase's established red/green/revert
  discipline (see 211-02/211-03 SUMMARY.md for the pattern to follow).
- **Spike needed: no** for shape 2 (the pattern is fully precedented in this phase); a short check
  (not a full spike) is needed for shape 1's config-threading question before choosing it.

## Owner phase and tag-blocking verdict

**Owner: unassigned — next phase that touches `quirk/intelligence/evidence.py` scoring counters,
or a dedicated follow-up phase if none is otherwise scheduled before Phase 214.** Not assigned to
Phase 212 (P2b dilution decision only, no implementation) or Phase 213 (UI-only, Series 7 shipped
product defects).

**Tag-blocking verdict: NO — this divergence must NOT block Phase 214's release tag, but MUST be
disclosed in the release notes / known-issues section Phase 214 produces.** Rationale: it measures
**0 on the reference estate today** (confirmed by both the live Phase 210 re-run and this phase's
unit-scale coverage gate), so tagging now does not freeze a *known-wrong* number the way an active
17-vs-18-shaped divergence would — Phase 211's two active legs (`plaintext_http_count`,
`legacy_tls_count`) were tag-blocking precisely because they were non-zero on the reference estate;
this one is not. However, because the mechanism is a **latent, not absent**, defect (identical
defect class to the two just fixed, dormant only because no reference-estate endpoint happens to
trip it), an honest release disclosure must name it explicitly rather than let "the two pipelines
now agree" ship as an unqualified claim — matching the exact prior mistake `.continue-here.md`
records for 210-07/210-06 (a documentation claim outrunning its evidence). A future scan estate
that does trip this condition would silently ship a wrong Hygiene score on the dashboard side with
no error, no warning, and no test failure — GAP-worthy, not tag-blocking.
