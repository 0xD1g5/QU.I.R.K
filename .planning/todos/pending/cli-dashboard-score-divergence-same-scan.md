# CLI and dashboard report DIFFERENT scores and CRITICAL counts for the same scan

**Filed:** 2026-09-14 (demo-prep task 1, measured multihost run)
**Priority:** P1 — client-visible. The report PDF and the dashboard disagree in front of the client.
**Status:** open, reproduced twice

## Symptom

One scan (`scan_run_id 2026-09-14T14:25:49.899977+00:00`, multihost profile, 31 hosts), three
numbers depending on which surface you read:

| Surface | Score | CRITICAL | Certificates |
|---|---|---|---|
| CLI / report artifacts | **15** (computed 61) | **5** | 17 |
| `GET /api/scan/latest?scan_id=<that run>` | **19** (computed 76) | **7** | 17 |
| `GET /api/scan/latest` (no `scan_id`) | **19** (computed 76) | **14** | **34** |

## Three independent causes, confirmed

### A. ONE certificate produces TWO CRITICALs (root cause found 2026-09-14)

`GET /api/scan/latest?scan_id=...` returns two findings with an identical host, port and title:

```
10.80.0.41 8080 | Weak SAML signing certificate: RSA-1024
10.80.0.41 8080 | Weak SAML signing certificate: RSA-1024
```

**Not a naive duplicate — two legitimate endpoint rows for the SAME certificate.** The SAML IdP
publishes one cert under two `use` values, and both rows carry the identical serial:

```
10.80.0.41 8080 SAML RSA 1024  ...metadata.php|use=signing|serial=109f9643580ecbdd7587dcfc19672af0d2512b1
10.80.0.41 8080 SAML RSA 1024  ...metadata.php|use=encryption|serial=109f9643580ecbdd7587dcfc19672af0d2512b1
```

`quirk/dashboard/api/routes/scan.py:480-498` emits one `IdentityFinding` per endpoint, so a single
weak key yields two CRITICALs. Two consequences:

1. **The score cap is driven by CRITICAL count**, so one 1024-bit key inflates the cap input by two.
   This is the whole of the 6 -> 7 difference, and the whole of the dashboard's 19-vs-15.
2. **The `use=encryption` row is mislabelled** — its title says "Weak SAML **signing** certificate".

**Fix shape (decide before changing anything):** either dedupe SAML identity findings by
`(host, port, cert serial)` so one certificate yields one finding, or keep both rows and give them
accurate, distinct titles (`signing` / `encryption`). The first changes CRITICAL counts and
therefore scores — that is a *correctness* fix, not tuning, but it moves fixtures and must not be
done casually near a demo. 999.113 D5 (never tune to a target) is not in tension with fixing a
genuine double-count, but the distinction should be stated explicitly in whatever plan does it.

### B. The CLI omits the SAML finding entirely

`grep SAML` over `findings-20260914-142606.json` returns **nothing**, yet the CLI's own
`evidence_summary` in `intelligence-20260914-142606.json` carries
`identity_saml_weak_signing_ratio: 0.0054`. **The CLI scored the weakness and never reported it.**

A and B are opposite failures of the same finding: reported twice on one surface, zero times on the
other. Neither surface is currently correct.

### C. SESSION_BRACKET merges distinct scan runs

`quirk/dashboard/api/routes/scan.py` — `SESSION_BRACKET = timedelta(minutes=5)` (mirrored at
`quirk/merge/scan.py:31`). The no-`scan_id` branch resolves endpoints by a time window around
`MAX(scanned_at)` with **no `scan_run_id` filter**, so two scans less than 5 minutes apart merge
into one "latest scan". Two runs 4m26s apart yielded 34 certificates (17x2) and 14 CRITICAL.

This is **documented and accepted** at `202-REVIEW.md` WR-02(b) and in `get_latest_scan`'s own
docstring — but recorded there only as a `score_lift` divergence between the roadmap and the
storyline drawer. The docstring does not say it also inflates the **headline score, the CRITICAL
count, and the certificate inventory**, which is the client-visible part.

## Demo mitigation (2026-09-18)

- Do **not** re-scan within 5 minutes of a previous scan, or pin the dashboard with `?scan_id=`.
- Expect the dashboard to read 19/POOR where the report reads 15/POOR. Both are POOR, so the
  narrative holds, but do not put the two surfaces side by side.

## Fix sketch (not yet attempted)

- A: find the SAML finding producer and dedupe on `(host, port, title)` — or find why it runs twice.
- B: the SAML connector's evidence path and its finding-emission path have diverged; the evidence
  path is the one that works.
- C: filter the no-`scan_id` branch by the resolved `scan_run_id` once one is determined, rather
  than by time window alone. Note the docstring's accounting of why the window exists (legacy
  NULL-`scan_run_id` rows) before changing it — the window is load-bearing for old data.

## Evidence

Both scan runs of 2026-09-14 in `quirk-output/`; per-host extraction at
`$CLAUDE_JOB_DIR/tmp/perhost.py`. Recorded in
`quantum-chaos-enterprise-lab/expected_results_v4.md` under "Cross-surface parity".
