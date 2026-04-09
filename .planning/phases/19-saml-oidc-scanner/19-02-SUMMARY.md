---
phase: 19-saml-oidc-scanner
plan: "02"
subsystem: scanner
tags: [saml, oidc, lxml, defusedxml, cryptography, cbom, chaos-lab, docker]

requires:
  - phase: 19-01
    provides: saml_scanner.py stub with LXML_AVAILABLE guard, SAML_NS, SHA1_INDICATORS, OIDC_ALG_SEVERITY, static helpers, 26-test RED scaffold

provides:
  - quirk/scanner/saml_scanner.py — full SAML/OIDC scanner implementation (300 lines)
  - quirk/cbom/builder.py — SAML protocol branch in build_cbom()
  - quirk/cbom/classifier.py — sha1 short-form entry in _ALGORITHM_TABLE
  - run_scan.py — SAML scan phase block with _phase_timer and lazy import
  - quantum-chaos-enterprise-lab/simplesamlphp/cert/ — RSA-1024 X.509 cert + key
  - quantum-chaos-enterprise-lab/docker-compose.yml — simplesamlphp service under profile saml

affects:
  - CBOM pipeline now dispatches SAML endpoints through _register_algorithm
  - run_scan.py aggregates saml_endpoints alongside tls/ssh/jwt/dnssec endpoints

tech-stack:
  added:
    - lxml 6.0.2 (lxml + defusedxml.lxml installed in venv for XXE-safe XML parsing)
  patterns:
    - "defusedxml.lxml.fromstring() for XXE-safe SAML metadata parsing"
    - "lxml ElementPath subset — [not(@use)] not supported, use Python-level filter on tag iteration"
    - "Lazy import pattern for scan_saml_targets inside if-guard in run_scan.py (matches DNSSEC style)"
    - "RSA-1024 chaos lab cert pre-generated with openssl, committed to repo for SimpleSAMLphp volume mount"

key-files:
  created:
    - quantum-chaos-enterprise-lab/simplesamlphp/cert/server.crt
    - quantum-chaos-enterprise-lab/simplesamlphp/cert/server.key
  modified:
    - quirk/scanner/saml_scanner.py
    - quirk/cbom/builder.py
    - quirk/cbom/classifier.py
    - run_scan.py
    - quantum-chaos-enterprise-lab/docker-compose.yml

key-decisions:
  - "lxml ElementPath does not support not(@use) XPath predicate — iterate all KeyDescriptor elements and filter in Python (avoids lxml full XPath engine dependency)"
  - "lxml installed in venv as runtime dependency (not just test dep) — required for defusedxml.lxml.fromstring()"
  - "classifier.py already had rs256/es256/eddsa entries from JWT/JOSE section — only added sha1 short-form entry for SHA-1 URI findings"
  - "saml_timeout uses getattr() with default 10s matching DNSSEC pattern — config field optional"

requirements-completed: [SAML-01, SAML-02, SAML-03, SAML-04, SAML-05, SAML-06]

duration: 3min
completed: 2026-04-09
---

# Phase 19 Plan 02: SAML/OIDC Scanner — Full Implementation Summary

**Full SAML/OIDC scanner with defusedxml XXE-safe XML parsing, RSA-1024/2048 cert extraction, SHA-1 URI detection, OIDC discovery enumeration, CBOM integration, run_scan.py wiring, and SimpleSAMLphp RSA-1024 chaos lab profile — all 25 RED tests from Plan 01 go GREEN**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-09T11:36:42Z
- **Completed:** 2026-04-09T11:39:44Z
- **Tasks:** 2
- **Files modified:** 5 + 2 created

## Accomplishments

- Implemented `_fetch_metadata` using httpx with `verify=False`, `follow_redirects=True` (D-13, D-14)
- Implemented `_classify_target` — `.well-known` URL check then JSON content sniff (D-01)
- Implemented `_parse_cert_element` — whitespace-stripped base64 decode, load DER, extract key_alg/bits/serial/not_after (D-11 pitfall 7)
- Implemented `_parse_saml_metadata` — defusedxml XXE-safe parsing, signing/encryption cert extraction, SHA-1 URI detection from both ds:SignatureMethod and alg:SigningMethod elements
- Implemented `_parse_oidc_discovery` — id_token_signing_alg_values_supported and request_object_signing_alg_values_supported enumeration (D-03, Pitfall 6)
- Implemented `scan_saml_targets` — sequential target loop with LXML_AVAILABLE guard, graceful error handling
- Added `elif ep.protocol == "SAML":` branch to `quirk/cbom/builder.py` calling `_register_algorithm`
- Added `"sha1"` short-form entry to `quirk/cbom/classifier.py` _ALGORITHM_TABLE
- Added SAML scan block to `run_scan.py` after DNSSEC block with `_phase_timer` and lazy import
- Added `simplesamlphp` Docker Compose service under profile `saml` with RSA-1024 cert volume mount
- Generated RSA-1024 X.509 cert (`CN=idp.chaos.local`, 3650-day validity) for chaos lab

## Task Commits

Each task was committed atomically:

1. **Task 1: Full saml_scanner.py implementation** — `419b3c3` (feat)
2. **Task 2: CBOM + classifier + run_scan.py + chaos lab** — `fef094e` (feat)

## Test Results

- **25 PASS** — all SAML-01 through SAML-06 test coverage
- **1 SKIP** — integration test (requires `QUIRK_INTEGRATION_TESTS=1` + chaos lab running)
- **0 regressions** — 10 pre-existing DNSSEC failures unchanged (dnspython not installed in venv)

## Files Created/Modified

- `quirk/scanner/saml_scanner.py` — full 300-line implementation replacing Plan 01 stubs
- `quirk/cbom/builder.py` — SAML protocol branch added after DNSSEC branch
- `quirk/cbom/classifier.py` — `"sha1"` entry added to SAML/OIDC section
- `run_scan.py` — SAML scan block with `_phase_timer`, lazy import, endpoints aggregation updated
- `quantum-chaos-enterprise-lab/docker-compose.yml` — simplesamlphp service added under profile saml
- `quantum-chaos-enterprise-lab/simplesamlphp/cert/server.crt` — RSA-1024 X.509 cert (created)
- `quantum-chaos-enterprise-lab/simplesamlphp/cert/server.key` — RSA-1024 private key (created)

## Decisions Made

- lxml ElementPath subset does not support `not(@use)` predicate — iterate all `md:KeyDescriptor` elements via tag namespace string and filter `kd.get("use") is None` in Python; avoids needing lxml full XPath engine
- `classifier.py` already had all OIDC JWT algorithm entries (rs256, ps256, es256, eddsa) from the JWT/JOSE section — only added `sha1` (no-hyphen form) as the new entry for SAML SHA-1 URI findings; avoided duplicate entries
- lxml installed in venv via `pip install lxml` — required at runtime for defusedxml.lxml.fromstring(); was missing from venv at plan start (Rule 3 auto-fix)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed lxml in venv (runtime dependency missing)**
- **Found during:** Task 1 verification
- **Issue:** `ModuleNotFoundError: No module named 'lxml'` — scanner module could not parse SAML XML; tests patching `LXML_AVAILABLE=True` would call `defused_ET.fromstring` which is not importable without lxml
- **Fix:** `pip install lxml defusedxml` in venv; lxml 6.0.2 installed successfully
- **Files modified:** venv only (no source changes)
- **Verification:** `python -c "import lxml; import defusedxml.lxml as de"` passes

**2. [Rule 1 - Bug] lxml ElementPath does not support not(@use) XPath predicate**
- **Found during:** Task 1 verification (test_signing_cert_rsa_1024_extraction failed with "invalid predicate")
- **Issue:** Plan specified `root.findall(".//md:KeyDescriptor[not(@use)]/..."`)` — lxml's ElementPath subset raises `invalid predicate` for `not()` function
- **Fix:** Iterate all `{md_ns}KeyDescriptor` elements, check `kd.get("use") is None` in Python, collect X509Certificate children directly
- **Files modified:** quirk/scanner/saml_scanner.py
- **Verification:** All 25 tests pass after fix

---

**Total deviations:** 2 auto-fixed (Rule 3 + Rule 1)
**Impact on plan:** Both fixes required for correct test GREEN state; no architectural changes

## Known Stubs

None — all plan stubs replaced with working implementations.

## User Setup Required

To run the SimpleSAMLphp chaos lab integration test:
```bash
cd quantum-chaos-enterprise-lab
docker compose --profile saml up -d
QUIRK_INTEGRATION_TESTS=1 pytest tests/test_saml_scanner.py -m integration
```
