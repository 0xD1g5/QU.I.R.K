---
type: todo
created: 2026-09-05
source: phase-184.3 human-verify gate (UAT step 5 investigation) + 184.3-VERIFICATION.md
priority: high
resolves_phase: 194
---

# Dashboard certificate view renders failed TLS handshakes as phantom certificates

`quirk/dashboard/api/routes/scan.py:1656-1669` builds the `CertItem` list filtered
**only** by `ep.protocol and ep.protocol.upper() == "TLS"` — with no `cert_subject`
or `scan_error` gate. Every **failed** TLS handshake therefore renders as a
certificate-inventory row with em-dashes in Subject, Issuer, Expiry, Algorithm and
Quantum Safety.

**Why it matters:** because `certs.length` is non-zero, the honest
"No TLS certificates discovered in this scan" empty state at
`src/dashboard/src/pages/certificates.tsx:29-33` is **suppressed**. Worse, the same
unfiltered array feeds `src/dashboard/src/pages/print.tsx:453` → `PrintCerts`
(`:79-110`), which has the identical unfiltered render and the same empty-state
suppression — so phantom certificates reach a **client deliverable**.

`CertItem` (`quirk/dashboard/api/schemas.py:87-95`) carries no `scan_error`,
`tls_blocker_reason`, or success flag, so the failure evidence is structurally
dropped at the API boundary and the client cannot re-derive it.

**Scale:** 44 of 237 `protocol='TLS'` rows DB-wide (18.6%) have `scan_error` set and
every `cert_*` column NULL. On the 2026-09-05 localhost self-scan
(`scan_run_id 2026-09-05T20:23:35.142679+00:00`) this meant **5 phantom rows and zero
real certificates**, with the empty state never firing. Observed failure modes on
those rows: `TLS_ERROR: SSLEOFError`, `RESET_BY_PEER: ConnectionResetError [Errno 54]`,
`TIMEOUT: handshake operation timed out`.

**Why it stayed hidden for ~179 phases:** `_cert_expiry_key`
(`quirk/dashboard/api/routes/scan.py:1426-1427`) maps a NULL expiry to `datetime.max`,
so phantom rows sort to the **bottom** of the table. Whenever real certificates
coexisted — i.e. every chaos-lab scan — the phantoms were pushed below the fold. They
only became visible on a scan that produced zero real certificates. A defect that
hides itself under exactly the conditions you normally test under.

**Not a Phase 184.3 regression — verified, not assumed.** All 35 `184.3-*` commits
touch zero files under `quirk/scanner/`; the filter is byte-unchanged and `git blame`s
to Phase 5 (`922809cb feat(05-04)`). Phase 184.3's only change to `certificates.tsx`
swapped `new Date(...).toLocaleDateString` for `formatDateOnly`; the `"—"` fallback and
the absent filter both predate it.

**Inconsistent with every other consumer of the same rows**, all of which gate on
non-empty cert fields:
- `quirk/cbom/builder.py:471` and `:489` — `if subj and alg and not_after`
- `quirk/intelligence/evidence.py:200-202` — `certs_observed` only counts an actual
  `datetime` `cert_not_after`

The dashboard certificate view is the sole outlier.

**Work:**
1. Add the missing gate so the empty state is honest — e.g.
   `and (ep.cert_subject or ep.cert_not_after)` at `scan.py:1656-1669`.
2. Preferred over silently dropping them: surface the excluded endpoints **separately**
   as "TLS ports probed, no certificate retrieved", carrying `tls_blocker_reason`, so
   real coverage signal is not lost. Requires adding that field to `CertItem` or a
   sibling schema.
3. Apply the same fix to `print.tsx`'s `PrintCerts` — the client-deliverable path is the
   higher-severity half.
4. Add a regression test with a fixture endpoint carrying `protocol='TLS'` +
   `scan_error` + NULL certs, asserting it does NOT appear in the certificate inventory
   and that the empty state fires when it is the only TLS row.

**Related measurement gotcha, worth recording alongside:** `crypto_endpoints` has 4989
distinct `scanned_at` values but only **4** distinct `scan_run_id`s (10069 of 10143 rows
predate the column). Grouping scans by `scanned_at` fragments every run and produces
false readings such as "the newest scan has zero TLS endpoints". `scan.py:1316` already
groups by `scan_run_id` first — analysis should do the same.
