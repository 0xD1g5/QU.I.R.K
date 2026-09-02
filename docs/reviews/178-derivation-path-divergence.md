# 178: Derivation-Path Identity Divergence (IDENT-03)

**Phase:** 178-finding-identity-repair, Plan 03
**Requirement:** IDENT-03
**Decision:** `.planning/phases/178-finding-identity-repair/178-CONTEXT.md` decision 12 —
"if the two paths disagree today, report it as a finding and bound it in writing — do not
silently pick a winner."

## Scope

QU.I.R.K. has two independent finding-derivation paths describing the same scanned endpoint to
two different audiences:

- **Report path** — `quirk.engine.findings_evaluator.evaluate_endpoints`, which produces the
  client-facing CLI/report deliverable.
- **Dashboard path** — `quirk.dashboard.api.routes.scan._derive_findings` (and its four
  `_derive_*_findings` siblings), which produces the operator console.

IDENT-03's contract is **fingerprint equality only** — for a condition BOTH paths detect, does
`TicketingChannel.compute_fingerprint({"host", "port", "title"})` produce the same value from
both paths' output? This is deliberately narrower than full field parity. Merging the two
derivation paths into one engine is RVW-002's design-judgment refactor and remains **excluded
since v5.16** (see `tests/test_finding_engine_parity.py` module docstring and
`.planning/phases/178-finding-identity-repair/178-CONTEXT.md` "Out of scope"). This document does
not propose that merge, and no production title string in either file was changed to produce it.

## Method

Both engines were run over the three fixture endpoints already defined in
`tests/test_finding_engine_parity.py` (`_UNDERSIZED_RSA` at 10.0.0.1:443, `_SELF_SIGNED` at
10.0.0.2:443, `_EXPIRED` at 10.0.0.3:443). For each endpoint, both paths' emitted `(host, port,
title)` tuples were collected verbatim (no normalization applied), and identity was measured as
`TicketingChannel.compute_fingerprint({"host": host, "port": port, "title": title})` per
`quirk/ticketing/base.py:75-88` — `SHA256(f"{host}:{port}::{title}")`. Two titles produce the
same fingerprint if and only if they are byte-identical, since the formula concatenates the
literal title string with no normalization step.

## Result: agreement

| Host | Condition | Report title | Dashboard title | Fingerprints |
|------|-----------|---------------|------------------|---------------|
| 10.0.0.1:443 | undersized RSA key | `TLS certificate uses undersized RSA key` | `TLS certificate uses undersized RSA key` | equal |
| 10.0.0.2:443 | self-signed | `TLS certificate is self-signed` | `TLS certificate is self-signed` | equal |

Both titles are byte-identical across both paths, so their fingerprints already match today with
**no code change required**. Research Assumption A2 ("the titles diverge") is falsified for these
two conditions — 2 of the 3 shared conditions agree out of the box.

## Result: bounded divergence D-178-A (wording)

The third shared condition — expired certificate at 10.0.0.3:443 — diverges:

- **Report literal:** `"TLS certificate expired"` — `quirk/engine/findings_evaluator.py:593`
- **Dashboard literal:** `Certificate expired` — `quirk/dashboard/api/routes/scan.py:185`

Both are FIXED strings, not f-strings — neither is among the 22 `title=f"..."` interpolation
sites in `quirk/`, so title normalization work (Plan 178-04's `TITLE_PREFIX_ALIASES` extension)
does not and cannot resolve this divergence; it is a categorically different problem.

**Operator consequence:** the same host, same port, same underlying certificate condition
produces two different SHA256 fingerprints depending on which path derived it. An expired
certificate ticketed from the CLI/report path via `TicketingChannel.dispatch_finding` and the
same certificate later ticketed from the dashboard path will not collide in
`find_by_fingerprint` — Jira/ServiceNow dedup silently fails, and the client sees two open
tickets for one certificate.

**This phase does not pick a winner.** Two candidate resolutions are named for a future phase to
decide between, neither applied here:

1. **Align the dashboard literal to the report literal** (`"Certificate expired"` ->
   `"TLS certificate expired"`) — a user-visible string change on the operator console.
2. **Add a cross-engine synonym alias** mapping `"Certificate expired"` to
   `"TLS certificate expired"` (or vice versa) at fingerprint-compute time. This is a materially
   different mechanism from the volatile-value stripping `TITLE_PREFIX_ALIASES` performs (it
   equates two entirely different literals rather than stripping an interpolated suffix) and
   **must not** be folded into `TITLE_PREFIX_ALIASES` — doing so would make one normalizer serve
   two unrelated jobs and risk exactly the kind of silent scope creep this phase is bounding.

## Result: bounded divergence D-178-B (detection coverage)

A second, distinct divergence was observed and must not be conflated with D-178-A:

- The report path emits `"TLS certificate uses quantum-vulnerable RSA key"` on both 10.0.0.2:443
  (self-signed, RSA-4096) and 10.0.0.3:443 (expired, RSA-4096).
- The dashboard path emits this title on **neither** endpoint.

This is a **detection-coverage gap** — one path detects a condition the other does not detect at
all — not an identity-agreement failure. There is no fingerprint to compare because the
dashboard never produces a finding for this condition in the first place. IDENT-03's
fingerprint-equality contract does not cover detection coverage, and closing this gap (adding
quantum-vulnerable-RSA detection to the dashboard path) is out of scope for this plan. Recorded
here as D-178-B so it is not lost, and so it is never mistaken for a wording divergence when a
future phase triages this document.

## Enforcement

`tests/test_finding_engine_parity.py::TestIdentityParity` enforces this document machine-readably:

- `test_shared_condition_titles_yield_identical_fingerprints` proves the two agreeing conditions
  above produce equal fingerprints.
- `test_expired_certificate_divergence_is_bounded_not_silent` proves the D-178-A pair produces
  different fingerprints AND that the pair is present in the module-level
  `_KNOWN_IDENTITY_DIVERGENCES` allowlist.
- `test_no_unbounded_identity_divergence` is the catch-all: for every needle in
  `_SHARED_CONDITION_NEEDLES`, if both paths produce a title and the fingerprints differ, the pair
  MUST be in `_KNOWN_IDENTITY_DIVERGENCES` or the test fails.

The allowlist in `tests/test_finding_engine_parity.py` is the machine-readable form of this
document. Adding a divergence row here without adding the matching `_KNOWN_IDENTITY_DIVERGENCES`
entry (or vice versa) is a drift that `test_no_unbounded_identity_divergence` will catch as a
test failure the next time either file is touched without the other.

## Status

`open — bounded, carried into the v5.18 backlog` — 2026-09-02.

D-178-A (wording divergence) and D-178-B (detection-coverage gap) are both bounded in writing and
guarded by tests, but neither is resolved. Resolving D-178-A requires a human decision between the
two candidates above (a user-visible string change vs. a new normalizer class). Resolving D-178-B
requires adding quantum-vulnerable-RSA detection to the dashboard derivation path. Both are
follow-up work for a future phase, not this one.
