---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-19); ledger rows DCL-CBOM-* (CNSA 2.0 narrowing)
priority: medium
area: quirk/reports/html_renderer.py, quirk/dashboard/api/routes/scan.py, quirk/scanner/hardware_tier.py, quirk/reports/docx_renderer.py
status: pending
resolves_phase: null
---

# Report and API code present "CNSA 2.0 deadline" years that no primary source in the repo supports

While removing unverified CNSA 2.0 years from `docs/cbom-guide.md` (NSA's publication returns HTTP 403 to automated
fetches: `curl -sS -o /dev/null -A Mozilla/5.0 -w '%{http_code}' https://www.nsa.gov/Cybersecurity/CNSA-2-0/` -> 403),
the same unverified years turned up in shipped code and output:

- `quirk/reports/html_renderer.py:346-351` (`CNSA_DEADLINE`): "Replace by 2030 (CNSA 2.0 deadline)", "Firmware upgrade
  target: 2030-2033", "Accept and monitor; re-evaluate by 2033". These render in the HTML report's Hardware PQC Advisory
  table.
- `quirk/dashboard/api/routes/scan.py:803` (`_CNSA_DEADLINE`): the same strings in the dashboard API response.
- `quirk/scanner/hardware_tier.py:27` (`_PQC_WINDOW_START = date(2030, 1, 1)`): the tier boundary, documented as
  "CNSA-2.0 remediation tier assignment".
- `quirk/reports/docx_renderer.py:808`: "Listed for CNSA 2.0 migration planning purposes only."

`quirk/scanner/pqc_deadlines.py` deliberately omits CNSA 2.0 dates for exactly this reason: "No CNSA 2.0 date literal
appears anywhere in this module" and "Do NOT add CNSA 2.0 dates from secondary sources". The hardware advisory contradicts
that stance, and a client report can carry a compliance deadline attributed to NSA that QU.I.R.K. never verified.

- [ ] Re-attempt a primary-source fetch of NSA's CNSA 2.0 publication through a browser-like path, and either attach the
      quoted dates to the code comments or remove the attribution.
- [ ] If the dates cannot be verified, relabel the strings as QU.I.R.K.'s own planning windows ("migration window
      2030-2033") with no "CNSA 2.0 deadline" claim, and add the source to `PQC_DEADLINE_TABLE_META`-style staleness
      pressure if the dates stay.
- [ ] Update the report renderer tests that pin these strings.

## Feasibility & Effort

**CONFIRMED** (file:line above; HTTP 403 reproduced 2026-10-12). Effort **S** to relabel, **M** if the dates are kept
and a staleness-gated source catalog is added. Unknown: whether NSA's PDF is reachable without a browser. **Spike
worthwhile** (a browser-driven fetch) before deciding.
