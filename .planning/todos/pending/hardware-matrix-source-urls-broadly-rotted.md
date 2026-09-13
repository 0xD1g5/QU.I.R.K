---
type: todo
created: 2026-09-13
source: phase-203 plans 03/04 — Chrome-driven source re-verification (STALE-01)
priority: high
requirement: STALE-01 (partially discharged — 1 of 8 vendors verified)
resolves_phase: null
---

# 7 of 8 `HARDWARE_MATRIX` vendor `source_url`s are dead, moved, or access-gated

Phase 203 re-verified `quirk/scanner/hardware_meta.py` against its real sources using Chrome
browser automation. **Only 1 of 8 vendors could be verified.** The other 7 could not be read at
their recorded URLs — not because of tooling limits, but because the documents are gone.

This is the follow-up for re-sourcing them. D-04 deliberately bounded Phase 203 to **one attempt
per vendor**, precisely so a re-verification pass could not turn into an open-ended URL hunt.
That limit was correct and was honoured; this todo is the work it fenced off.

## Current state (verified 2026-09-13, in a real browser)

| Vendor | Recorded `source_url` | What it actually serves |
|--------|----------------------|--------------------------|
| F5 | `support.f5.com/csp/article/K000141701` | 301 → `my.f5.com/manage/s/article/K000141701` → **"404: Page not found"** |
| Cisco | `sec.cloudapps.cisco.com/security/center/resources/pqc-readiness` | **HTTP 200 + "No Data Found For This Page."** |
| Palo Alto | `docs.paloaltonetworks.com/pan-os/11-1/.../post-quantum-cryptography` | **404** (restructured `network-security/...` path also 404) |
| Juniper | `supportportal.juniper.net/s/article/Junos-Post-Quantum-Cryptography-Status` | **"You do not have the required access privileges"** — support login required |
| HPE | `hpe.com/h20195/v2/GetPDF.aspx/a00128516en_us.pdf` | fetch **times out (60s, 0 bytes)**; no extractable text in Chrome |
| IPMI (Intel) | `intel.com/.../ipmi-second-gen-interface-spec-v2-rev1-1.html` | **HTTP 200**, generic Intel Server Products **product selector** — wrong subject |
| Thales | `thalesdocs.com/gphsm/luna/7/.../pqc.htm` | **`AccessDenied`** in a real browser (not bot-blocking) |
| **Fortinet** | ~~`7.6.0/761917/...`~~ | **RESOLVED in Phase 203** → `8.0.0/527690/post-quantum-preshared-key-support` |

Already fixed in Phase 203: Fortinet's URL and claim, and the top-level NSA `source_url`
(`CNSA-2-0/` → `Post-Quantum-Cryptography/`).

## Why this matters more than a stale date

Three of these rot patterns **pass a naive freshness check**:

- **Cisco and Intel return HTTP 200 with real, well-formed content on the wrong subject.** A
  status-code check calls both healthy.
- **Fortinet's old URL silently 301'd to "Getting started"** — 200, real content, unrelated. Even a
  "did I receive a page?" check passes it.

So the catalog can be simultaneously "all URLs return 200" and "no URL supports its entry's claim".
Only D-03's claim-match bar catches this, and only a browser distinguishes bot-blocking from rot.

## Consequence today

Under D-01 the top-level `last_verified` is `min()` of the entry dates, so 7 unverified vendors
pin it at `2026-06-13` and `tests/test_hardware_staleness.py::test_hardware_matrix_not_stale`
**stays RED**. That is the invariant working, not a bug — but it means this gate is red until this
todo is worked, and a future session must not "fix" it by bumping the date.

## What closing this looks like

1. For each of the 6 dead/moved vendors, find a current authoritative document **on that vendor's
   own domain** and re-verify the entry's `pqc_status` + `notes` against it (D-03's bar). Update
   `source_url` with the established inline provenance note, then bump that entry's date.
2. Juniper needs a support-portal account. Either the operator verifies it with their own
   credentials, or the entry is re-sourced to a public Juniper document, or its claim is
   re-expressed against something publicly checkable.
3. Expect corrections, not just URL swaps. The one vendor that *was* verified (Fortinet) turned out
   to be **wrong on two counts** — a bad version floor (`7.4+` vs the vendor's `6.0+`) and an
   entirely missing capability (PQC KEM / ML-KEM from 7.6.1+). A 1-for-1 sample suggests the rest
   of the catalog should not be assumed accurate.
4. Consider whether entries should carry an evidence quote or content fingerprint so the *next*
   re-verification is a diff rather than a re-read — offered and deliberately deferred at Phase
   203's discuss (see `203-CONTEXT.md` §Deferred Ideas). This rot pattern is the argument for it.

## Do NOT

- Bump any `last_verified` without actually re-reading the source (CLAUDE.md §Staleness Review
  Cadence).
- Use `QUIRK_CI_STALENESS_OVERRIDE_DATE` to clear the gate — it exists for boundary tests.
- Accept a secondary source (blog, vendor-adjacent summary) in place of the vendor's own document.
- Treat a `VENDOR-SILENT` entry as confirmed by a page that no longer exists. A document that isn't
  there attests to nothing — the IPMI/Intel row is the live example of that trap.

Full evidence: `.planning/phases/203-catalog-freshness-drain/203-ATTESTATION.md` (per-vendor rows
with outcome + evidence) and `203-RECON-source-reachability.md`.
