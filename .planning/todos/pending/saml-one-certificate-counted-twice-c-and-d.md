# SAML: one certificate is counted twice, into both the finding list and the score

**Filed:** 2026-09-14
**Scheduled:** operator decision — **after the next milestone completes**, NOT before the
2026-09-18 demo. Both parts change the emitted readiness score.
**Priority:** P2 (correctness, not client-facing breakage)
**Prerequisite done:** option B shipped 2026-09-14 — the two findings now carry accurate,
distinct titles (`signing` / `encryption`). That fixed the wrong *claim* without touching counts.

## The defect

A SAML IdP publishes a KeyDescriptor per USE, so ONE certificate appears as TWO
`crypto_endpoints` rows with an identical serial:

```
10.80.0.41 8080 SAML RSA 1024  ...metadata.php|use=signing|serial=109f9643580ecbdd7587dcfc19672af0d2512b1
10.80.0.41 8080 SAML RSA 1024  ...metadata.php|use=encryption|serial=109f9643580ecbdd7587dcfc19672af0d2512b1
```

Both consumers iterate rows, so a single weak 1024-bit key is counted twice.

## Option C — collapse the two findings into one

`quirk/dashboard/api/routes/scan.py::_derive_identity_findings`, the
`alg not in OIDC_ALG_SEVERITY and size < 2048` branch (two constructor calls as of option B).

Emit ONE finding per certificate, naming both uses:

> `Weak SAML certificate (signing, encryption): RSA-1024`

Preferred over a plain dedupe that drops one row silently: the fact that the SAME weak key serves
both signing AND encryption is real information a consultant would want, not noise to discard.

**Score impact:** CRITICAL 7 -> 6 on the multihost reference estate. CRITICAL count feeds the
consequence ceiling, so the emitted score moves.

**Constraints when doing this:**
- The title f-string must stay INLINE at `title=` — `tests/fixtures/chaos_lab_findings.py::
  collect_dashboard_titles` walks the AST for `title=` keywords holding an f-string literal, and a
  title built into a local variable first is invisible to it. That is how option B's first attempt
  broke the gate (it hid BOTH templates, not just the new one).
- Adding/removing a title requires a matching `TITLE_IDENTITY_CLASS` entry in
  `quirk/compliance/__init__.py` AND a bump of the literal in
  `tests/test_compliance_normalizer.py::test_title_identity_class_is_exhaustive_and_closed_vocabulary`
  (the real exhaustiveness check is `test_every_interpolated_title_is_classified`, which
  regenerates from source in BOTH directions — unclassified and stale).

## Option D — stop double-counting into the score ratio

`quirk/intelligence/evidence.py:236-242` increments `saml_weak_signing_count` per endpoint row.
Measured: `identity_saml_weak_signing_ratio: 0.0054` == **2**/370, not 1/370. So the double-count
reaches the score independently of the finding display — fixing C alone leaves D's distortion in
place.

Count distinct certificates (serial is available in `service_detail`).

## Do C and D together

They are one defect with two consumers. Shipping only one leaves the surfaces disagreeing about how
many weak SAML keys exist, which is worse than the current consistent-but-wrong state.

## What this does NOT fix

**The CLI and dashboard will still report different scores.** That gap is architectural, not this
defect: `quirk/engine/findings_evaluator.py` (CLI/reports, at scan time) has **zero** SAML/Kerberos/
DNSSEC rules, while `quirk/dashboard/api/routes/scan.py` (dashboard, at request time) has all three.
Identity findings exist on one path only. The two producers also name the same condition
differently — `Plaintext HTTP service detected` vs `Unencrypted HTTP service` — which is why
`quirk/dashboard/api/finding_title_bridge.py` exists. See
`.planning/todos/pending/cli-dashboard-score-divergence-same-scan.md`; that is the larger item and
should probably be scoped as its own phase.

## Scope caveat recorded honestly

Only SAML writes a serial into `service_detail`, so SAML is the only protocol where this
duplication is *checkable* today. That is NOT evidence that no other protocol double-counts — it is
evidence that nothing else exposes a comparable identity. Do not read the narrow blast radius as a
clean bill of health for the other producers.
