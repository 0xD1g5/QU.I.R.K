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

---

# RE-SOURCING WORK MATRIX (added 2026-09-13)

Exact claim text pulled from `quirk/scanner/hardware_meta.py`. Each row's **Confirm** column is
what D-03's claim-match bar requires — the replacement document must support *that*, not merely
mention the vendor and PQC.

## Class A — public document, dead or moved (6 vendors)

| # | Vendor | `pqc_status` | Confirm (verbatim claim) | Current URL state | Where to look next | Claim type | Effort |
|---|--------|--------------|--------------------------|-------------------|--------------------|-----------|--------|
| 1 | **Palo Alto** | `partial` | "PAN-OS 11.1+ supports X25519MLKEM768 hybrid KEM for TLS decryption; management plane and older releases remain unsupported." | 404 (both 11-1 path and restructured `network-security/…` path) | Current PAN-OS admin guide → Decryption section (11.2 / 12.x); PAN-OS release notes | **positive + specific** — named algorithm, named version | **S** |
| 2 | **Thales** | `partial` | "Luna Network HSM 7 firmware 7.7.1+ supports PQC key generation (ML-KEM, ML-DSA) via PKCS#11 extension; older firmware and Luna 6 are VENDOR-SILENT." | `AccessDenied` in a real browser (S3-backed docs host) | thalesdocs.com Luna 7 current docs tree; Luna firmware release notes; Thales PQC product pages | **positive + specific** | **S–M** |
| 3 | **HPE** | `partial` | "iLO 6 (Gen11 servers) supports PQC hybrid TLS via firmware 1.60+; iLO 3/4/5 do not." | fetch times out (60s, 0 bytes); no extractable text in Chrome | HPE Support Center → iLO 6 firmware release notes / changelog; doc ID `a00128516en_us` may live at a different URL form | **mixed** — positive for iLO 6, negative for 3/4/5 | **M** (HPE URLs are notoriously unstable, PDF-heavy) |
| 4 | **F5** | `partial` | "PQC support via SPK (Service Proxy for Kubernetes) module only; core TMOS does not support PQC cipher suites as of 2026-Q2." | 301 → `my.f5.com/manage/s/article/K000141701` → **404** | MyF5 KB by K-number; F5 PSIRT / security advisories; BIG-IP release notes cipher-support lists; F5 Trust Center | **negative-dominant** — "TMOS does *not*" is the load-bearing half | **M** |
| 5 | **Cisco** | `unsupported` | "ASA and FTD do not support PQC cipher suites; Cisco roadmap lists PQC for future FTD releases." | HTTP 200 + "No Data Found For This Page."; 3 same-domain attempts all 404 | Cisco Trust Center post-quantum page; Cisco "Next-Generation Cryptography" / CNSA docs; ASA & FTD release-notes cipher lists | **negative + roadmap** — roadmaps are rarely documented publicly | **M–L** |
| 6 | **IPMI (Intel)** | `VENDOR-SILENT` | "IPMI 2.0 specification predates PQC; individual BMC vendors have made no public PQC statements. VENDOR-SILENT assigned — no advisory found." | HTTP 200, generic Intel Server Products **product selector** — wrong subject | Intel's current IPMI 2.0 spec PDF location | **unfalsifiable as written** — see note | **S** for the spec, **M** if the claim is re-expressed |

**Note on row 6 — this one probably needs a claim rewrite, not just a URL.** It bundles two
different things: (a) *"IPMI 2.0 predates PQC"* — a historical fact, trivially supportable by the
spec's own date, and (b) *"individual BMC vendors have made no public PQC statements"* — a
**negative-existence claim that no single source can ever support.** No document proves an absence
across all BMC vendors. Options: narrow (b) to the specific vendors QUIRK actually fingerprints,
drop it and let `VENDOR-SILENT` mean only "the IPMI spec itself is silent", or keep it but mark it
explicitly as a survey finding with a re-survey cadence rather than a sourced claim.

## Class B — access-gated (1 vendor)

| # | Vendor | `pqc_status` | Confirm | Current URL state | Options | Effort |
|---|--------|--------------|---------|-------------------|---------|--------|
| 7 | **Juniper** | `unsupported` | "Junos OS does not support PQC algorithms as of 2026-Q2; roadmap items pending." | **"You do not have the required access privileges"** — support login required | (a) operator verifies with a Juniper support account; (b) re-source to public `juniper.net/documentation` Junos docs or Juniper security advisories; (c) re-express the claim against something publicly checkable | **S with credentials, M without** |

## Already fixed in Phase 203 — do not redo

| Vendor | Change |
|---|---|
| **Fortinet** | `url-corrected` + `corrected` → `8.0.0/527690/post-quantum-preshared-key-support`. Version floor fixed (6.0+, not 7.4+); PQC KEM (ML-KEM, 7.6.1+) added |
| **NSA (top-level)** | `url-corrected` → `nsa.gov/Cybersecurity/Post-Quantum-Cryptography/` |

## Per-vendor repair procedure

For each row, in order:

1. **Locate** a current authoritative document **on the vendor's own domain**. No blogs, no
   vendor-adjacent summaries, no third-party roundups.
2. **Compare** the page against the entry's `pqc_status` AND every assertion in `notes`. If the
   page is silent on the claim, that is **not** verification — it is still a deferral.
3. **Decide** the outcome: `verified` / `corrected` / `url-corrected` / `unreachable-deferred`.
   Expect corrections — the 1 vendor verified in Phase 203 was wrong on two counts.
4. **Apply**: update `source_url` with an inline provenance note in the established shape
   (`source_url corrected <date>: the prior <old-url> now <failure mode>; <new-url> is the live
   replacement.`), apply any `pqc_status`/`notes` correction, then set **that entry's**
   `last_verified` — never the top-level, which is computed.
5. **Chaos-lab check**: `quantum-chaos-enterprise-lab/expected_results_hwcompat.md` asserts
   `pqc_status` for **HPE** (`hwcompat-http`) and **Cisco** (`hwcompat-snmp`). If either changes,
   update the oracle in the same change per CLAUDE.md §Chaos Lab Maintenance. Record a checked
   no-op if it doesn't.
6. **Gate**: the top-level date recomputes to `min()` of the entries automatically — it only goes
   green once **all 8** carry current dates. `test_hardware_matrix_top_level_is_min_of_entries`
   enforces this; if it goes red you moved something you shouldn't have.

## The structural problem — re-sourcing alone will rot again

**7 of 8 URLs died in roughly three months.** That is not bad luck; it is what the catalog's
sourcing strategy selects for. Every rotted entry pinned a **deep link into a version-numbered
documentation tree** (`fortigate/7.6.0/…/761917`, `pan-os/11-1/…`, `luna/7/docs/…`), and vendors
rotate those on every release. Replacing seven deep links with seven newer deep links buys one
release cycle.

Worth doing alongside the re-sourcing:

- **Prefer stable anchors** — PSIRT/security-advisory indexes, trust centers, product landing
  pages — over versioned doc deep links, even when the deep link is more precise today.
- **Record the document identity separately from its URL.** F5's `K000141701` and Fortinet's
  `527690` survived their URL changes; the article ID is the durable key, the URL is not. A
  `doc_id` field would turn re-sourcing from a search into a lookup.
- **Add an `evidence` quote + `evidence_checked` date per entry** (offered and deferred at Phase
  203's discuss — see `203-CONTEXT.md` §Deferred Ideas). This rot pattern is the argument for it:
  the next re-verification becomes a diff rather than a re-read, and a silent vendor rewrite becomes
  detectable.
- **A link-health check that reads content, not status codes.** Cisco, Intel, and Fortinet-before-fix
  all returned **HTTP 200** while serving the wrong thing. Any checker keyed on status codes passes
  all three. A useful check asserts the page still contains the entry's evidence string.

## Effort summary (estimates, not measurements)

| Scope | Estimate |
|---|---|
| Re-source 6 public URLs + verify claims | **M** — ~1 focused session; Palo Alto/Thales likely quick, Cisco/HPE/F5 slower (negative claims are hard to source) |
| Juniper | **S** with credentials, **M** without |
| IPMI claim rewrite | **S–M**, and it is a design decision, not a lookup |
| Structural fixes (`doc_id`, `evidence`, content-aware link check) | **M** on top — and the thing that stops a third round |
