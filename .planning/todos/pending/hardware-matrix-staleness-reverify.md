---
type: todo
created: 2026-09-12
source: phase-201 plan 08 full-suite verification; operator-deferred at the orchestrator's close
priority: medium
requirement: none (standing staleness-cadence obligation, not a phase requirement)
---

# `HARDWARE_MATRIX.last_verified` is 91 days old (>90) — `tests/test_hardware_staleness.py` is RED on `main`

**Operator decision 2026-09-12: deferred with a record.** Phase 201's close-out surfaced this; it
is pure calendar drift, unrelated to anything Phase 201 changed, and a docs/close-out plan has no
domain basis to attest to a vendor hardware catalog's currency. Deferring is honest; bumping the
date to clear the gate would not be — see the new "Never bump a `last_verified` without
re-verifying" clause added to CLAUDE.md §Staleness Review Cadence on the same day.

## Current state

```
AssertionError: HARDWARE_MATRIX.last_verified is 91 days old (>90).
Re-verify against https://www.nsa.gov/Cybersecurity/CNSA-2-0/ and bump
last_verified in quirk/scanner/hardware_meta.py.
```

`last_verified: "2026-06-13"`, `STALENESS_THRESHOLD_DAYS = 90`. This is the **only** node in the
full-suite failing SET as of 2026-09-12 (4960 passed, 1 failed) — the other 7 failures present
earlier that day were a genuine Phase 201 regression and were fixed in commit `d1f1351f`.

## What re-verification actually requires (do not shortcut this)

`HARDWARE_MATRIX` carries a top-level `source_url` **plus a per-vendor `source_url` on every
entry**. Re-verifying means reading the vendor advisories, not just the NSA page:

| Vendor | `source_url` |
|--------|--------------|
| (top level) | `https://www.nsa.gov/Cybersecurity/CNSA-2-0/` |
| F5 | `https://support.f5.com/csp/article/K000141701` |
| Cisco | `https://sec.cloudapps.cisco.com/security/center/resources/pqc-readiness` |
| Palo Alto | `https://docs.paloaltonetworks.com/pan-os/11-1/pan-os-admin/decryption/post-quantum-cryptography` |
| Fortinet | `https://docs.fortinet.com/document/fortigate/7.6.0/administration-guide/761917/post-quantum-preshared-keys` |
| Juniper | `https://supportportal.juniper.net/s/article/Junos-Post-Quantum-Cryptography-Status` |
| HPE | `https://www.hpe.com/h20195/v2/GetPDF.aspx/a00128516en_us.pdf` |
| Intel | `https://www.intel.com/content/www/us/en/products/docs/servers/ipmi/ipmi-second-gen-interface-spec-v2-rev1-1.html` |
| Thales | `https://thalesdocs.com/gphsm/luna/7/docs/network/Content/admin_partition/pqc.htm` |

**Expected obstacle:** NSA / `media.defense.gov` sources return HTTP 403 to non-browser agents —
the same caveat CLAUDE.md already records for `pqc_deadlines.py`, where CNSA 2.0 dates are a
deliberate omission for exactly this reason. If the NSA page is unreachable, say so and re-verify
the per-vendor entries (which are the catalog's actual PQC-readiness claims) rather than silently
treating the top-level URL as checked.

## Acceptance

- Each vendor entry's PQC-readiness claim re-checked against its own `source_url`; any drift
  corrected in `quirk/scanner/hardware_meta.py` (a correction found is a success, not a failure).
- Any source that could not be reached is named explicitly in the commit message — not papered over.
- `last_verified` bumped to the real verification date, only for what was really verified.
- `chore: re-verify HARDWARE_MATRIX catalog (YYYY-MM-DD)` per CLAUDE.md's standard remediation.
- `tests/test_hardware_staleness.py` green; full-suite failing-node SET back to EMPTY.

## Worth folding in while here

`quirk/scanner/hw_cve.py` has the tightest cadence at 30 days (`last_verified: 2026-09-02`, trips
≈2026-10-02). A staleness-focused session should check it in the same pass rather than leaving it
to trip days later. Ages as computed 2026-09-12: model_meta 32/90, bacnet_vendors 32/365,
hardware_eol 29/365, **hardware_meta 91/90 STALE**, hw_cve 10/30, pqc_deadlines 10/90,
snmp_meta 10/90.
