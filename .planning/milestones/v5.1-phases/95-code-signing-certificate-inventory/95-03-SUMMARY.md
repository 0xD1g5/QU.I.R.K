---
phase: 95-code-signing-certificate-inventory
plan: "03"
subsystem: scanner,chaos-lab
tags: [codesign, run_scan, wiring, ldap, eku, chaos-lab, csign-01, lab-01]
dependency_graph:
  requires:
    - quirk.scanner.codesign_scanner (scan_codesign_from_ldap, scan_codesign_from_tls_endpoints)
    - quirk/config.py (ConnectorsCfg.codesign_targets / codesign_search_base / codesign_timeout)
  provides:
    - run_scan.py --inventory-code-signing flag (args.inventory_code_signing)
    - run_scan.py _run_codesign_phase (LDAP + TLS-EKU, lazy imports, _wrapped_phase)
    - run_scan.py codesign_endpoints in final assembly
    - run_scan.py CODE_SIGNING in _dar_protocols + resume block
    - quantum-chaos-enterprise-lab ldaps code-signing fixture (LAB-01)
  affects:
    - run_scan.py (CLI flag, _dar_protocols, resume block, phase function, endpoints assembly)
    - quantum-chaos-enterprise-lab/docker-compose.yml (ldaps-codesign-seed sidecar)
    - quantum-chaos-enterprise-lab/ldaps/ldif/codesign-users.ldif (new)
    - quantum-chaos-enterprise-lab/ldaps/certs/codesign-weak.der (new)
    - quantum-chaos-enterprise-lab/ldaps/certs/regen.sh (new)
    - quantum-chaos-enterprise-lab/expected_results_v4.md (ldaps oracle row)
    - quantum-chaos-enterprise-lab/README.md (ldaps profile row updated)
    - tests/test_run_scan_codesign_wiring.py (new)
tech_stack:
  added: []
  patterns:
    - _wrapped_phase invocation (mirrors _run_smime_phase / _run_adcs_phase)
    - lazy imports inside phase function (flag-off path imports nothing)
    - scan_codesign_from_tls_endpoints called AFTER tls_endpoints populated (ordering constraint)
    - LDAP + TLS-EKU dual-source codesign endpoint assembly
    - smime-seed sidecar idempotency pattern (ldapadd -c + exit-68 swallow)
    - RSA-1024/SHA-1 + CodeSigning EKU DER cert (openssl -addext extendedKeyUsage=codeSigning)
    - userCertificate;binary:: (RFC 4523) vs userSMIMECertificate:: (no ;binary)
key_files:
  created:
    - tests/test_run_scan_codesign_wiring.py
    - quantum-chaos-enterprise-lab/ldaps/certs/regen.sh
    - quantum-chaos-enterprise-lab/ldaps/certs/codesign-weak.der
    - quantum-chaos-enterprise-lab/ldaps/ldif/codesign-users.ldif
  modified:
    - run_scan.py
    - quantum-chaos-enterprise-lab/docker-compose.yml
    - quantum-chaos-enterprise-lab/expected_results_v4.md
    - quantum-chaos-enterprise-lab/README.md
decisions:
  - "_run_codesign_phase placed AFTER _run_adcs_phase in the else-branch so tls_endpoints is already populated when scan_codesign_from_tls_endpoints is called (CSIGN-01 TLS source ordering requirement)"
  - "codesign_endpoints initialised in resume block via protocol == CODE_SIGNING filter (mirrors adcs_endpoints pattern)"
  - "test_dar_protocols_contains_codesign uses AST parse of the worktree's run_scan.py (pathlib.Path(__file__).parent.parent / 'run_scan.py') not the cwd-relative path — prevents false-GREEN when test runs from main repo root"
  - "ldaps-codesign-seed sidecar mounts ./ldaps/ldif:/ldif:ro only (not certs) — DER cert already embedded as base64 in LDIF"
  - "lab.sh intentionally not modified — no new profile added; ldaps profile already dynamically discovered by _derive_all_profiles in lab.sh"
  - "userCertificate;binary:: used in LDIF (RFC 4523 correct for X.509 Certificate syntax) vs userSMIMECertificate:: which does NOT use ;binary"
metrics:
  duration: "~22 minutes"
  completed: "2026-05-23"
  tasks_completed: 2
  files_changed: 8
---

# Phase 95 Plan 03: run_scan Wiring + Chaos-Lab ldaps Code-Signing Fixture Summary

**One-liner:** `--inventory-code-signing` wired into run_scan.py via `_wrapped_phase` (LDAP + TLS-EKU dual source) with the ldaps chaos-lab profile gaining an RSA-1024/SHA-1 CodeSigning EKU fixture and full triple update.

## What Was Built

### Task 1: run_scan.py --inventory-code-signing wiring (TDD)

**RED commit:** `9e2b72f` — `tests/test_run_scan_codesign_wiring.py` with 5 tests; 1 failing (test_dar_protocols_contains_codesign — CODE_SIGNING missing from _dar_protocols).

**GREEN commit:** `c14c934` — `run_scan.py` changes:

**CLI flag:**
```python
parser.add_argument(
    "--inventory-code-signing",
    dest="inventory_code_signing",
    action="store_true",
    default=False,
    help="Inventory code-signing certificates from LDAP userCertificate attributes ..."
)
```

**`_dar_protocols` update** (line 1515):
```python
_dar_protocols = ("S3", "AZURE-BLOB", "K8S", "GCS", "VAULT", "DNSSEC", "SAML",
                 "KERBEROS", "SMIME", "ADCS", "CODE_SIGNING")  # Phase 95 CSIGN-01
```

**Resume block** (after adcs_endpoints):
```python
codesign_endpoints = [e for e in _resumed_endpoints if getattr(e, "protocol", "") == "CODE_SIGNING"]
```

**`_run_codesign_phase()`** — placed after `_run_adcs_phase` so `tls_endpoints` is already populated:
- Returns `[]` immediately when `args.inventory_code_signing` is False (no scanner import)
- Lazy-imports `scan_codesign_from_ldap` and `scan_codesign_from_tls_endpoints` only when flag is set
- Calls `scan_codesign_from_ldap` only when `codesign_targets` is non-empty
- Always calls `scan_codesign_from_tls_endpoints(tls_endpoints, ...)` for the in-process EKU check
- Concatenates both result lists

**`_wrapped_phase` invocation:**
```python
codesign_endpoints = _wrapped_phase(
    run_stats, "codesign_scanning", "codesign_scanner",
    _run_codesign_phase, error_endpoints, logger,
) or []
```

**Endpoints assembly** — `codesign_endpoints` added after `adcs_endpoints`:
```python
+ adcs_endpoints
+ codesign_endpoints                              # Phase 95 CSIGN-01
+ vault_endpoints
```

Tests: 5/5 GREEN.

### Task 2: Chaos-lab ldaps code-signing fixture + triple update (LAB-01)

**Commit:** `52b115a`

**`ldaps/certs/regen.sh`** — developer tool generating RSA-1024/SHA-1 + CodeSigning EKU cert:
```bash
openssl req -x509 -newkey rsa:1024 -sha1 ... -addext "extendedKeyUsage=codeSigning"
```
Outputs `codesign-weak.der` (667 bytes) and regenerates `ldaps/ldif/codesign-users.ldif`.

**`ldaps/certs/codesign-weak.der`** — 667-byte DER cert. OpenSSL-verified:
- Public Key: RSA-1024
- Signature Algorithm: sha1WithRSAEncryption
- Extended Key Usage: Code Signing (OID 1.3.6.1.5.5.7.3.3)
- Valid for 100 years (non-expired for deterministic lab signals)

**`ldaps/ldif/codesign-users.ldif`** — seeds:
- `ou=people,dc=chaos,dc=local` (organizational unit)
- `uid=codesign-weak,ou=people,dc=chaos,dc=local` with `userCertificate;binary::` (RFC 4523 correct)
- Base DN: `dc=chaos,dc=local` (NOT `dc=quirk,dc=lab` — Critical Caveat 4)

**`docker-compose.yml`** — `ldaps-codesign-seed` sidecar added:
```yaml
ldaps-codesign-seed:
  image: bitnamilegacy/openldap:2.6.10-debian-12-r4
  profiles: ["ldaps"]
  depends_on:
    ldaps:
      condition: service_started
  entrypoint: ["/bin/sh", "-c"]
  command:
    - "sleep 5 && ldapadd -c -x -H ldap://ldaps:389 -D 'cn=admin,dc=chaos,dc=local' -w admin -f /ldif/codesign-users.ldif; rc=$$?; if [ $$rc -eq 0 ] || [ $$rc -eq 68 ]; then exit 0; else exit $$rc; fi"
  volumes:
    - ./ldaps/ldif:/ldif:ro
  restart: "no"
```

**`expected_results_v4.md`** — new "Profile: ldaps — Code-Signing Fixture" subsection:

| User DN | Certificate | Expected Finding | Severity |
|---|---|---|---|
| uid=codesign-weak,ou=people,dc=chaos,dc=local | RSA-1024 / SHA-1 + CodeSigning EKU | CODE-SIGN/weak-algorithm | HIGH |

**`README.md`** — ldaps profile row updated to include `ldaps-codesign-seed` service and Phase 95 LAB-01 description.

**`lab.sh`** — NOT modified (intentional, CLAUDE.md-compliant). The `_derive_all_profiles()` function reads profiles dynamically from docker-compose.yml; the `ldaps` profile already exists and is already included. No new profile was added — only a sidecar service was added to the existing `ldaps` profile, so ALL_PROFILES enumeration in lab.sh has no drift.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed AST test path resolution**
- **Found during:** Task 1 RED phase test execution
- **Issue:** `test_dar_protocols_contains_codesign` used `pathlib.Path("run_scan.py")` which resolves relative to CWD. When pytest is run from the QUIRK main repo (`cd /Volumes/.../QUIRK`), it read the main repo's `run_scan.py` instead of the worktree's updated copy — the test was always checking the un-modified file and would have passed prematurely (or silently failed after implementation).
- **Fix:** Changed to `pathlib.Path(__file__).parent.parent / "run_scan.py"` which resolves relative to the test file location — always reads the co-located `run_scan.py`.
- **Files modified:** `tests/test_run_scan_codesign_wiring.py`

**2. [Rule 1 - Bug] Fixed AST Constant node attribute (.s vs .value)**
- **Found during:** Task 1 initial test run
- **Issue:** AST `Constant` node uses `.value` attribute in Python 3.8+, not `.s` (legacy attribute removed in Python 3.14).
- **Fix:** Changed `elt.s` to `elt.value` and `isinstance(elt.s, str)` to `isinstance(elt.value, str)`.
- **Files modified:** `tests/test_run_scan_codesign_wiring.py`

## Known Stubs

None — all wiring is functional; the codesign_endpoints assembly is a real list populated from scanner results (or empty list when flag is off).

## Threat Surface Scan

No new network endpoints or auth paths beyond the plan's threat model:

- T-95-08 (EoP — flag scope): mitigated — `_run_codesign_phase` returns `[]` immediately when `args.inventory_code_signing` is False; lazy imports ensure no scanner module is loaded on the flag-off path.
- T-95-09 (Info Disclosure — seed sidecar admin bind): accepted — chaos-lab only, throwaway `admin/admin` credential on loopback.
- T-95-10 (Tampering — package install): accepted — no new packages this plan.

## Self-Check: PASSED

Files present:
- run_scan.py (modified): YES — `grep -c "inventory_code_signing" = 3`
- tests/test_run_scan_codesign_wiring.py (created): YES
- quantum-chaos-enterprise-lab/ldaps/certs/regen.sh (created): YES
- quantum-chaos-enterprise-lab/ldaps/certs/codesign-weak.der (created): YES
- quantum-chaos-enterprise-lab/ldaps/ldif/codesign-users.ldif (created): YES
- quantum-chaos-enterprise-lab/docker-compose.yml (modified): YES — ldaps-codesign-seed present
- quantum-chaos-enterprise-lab/expected_results_v4.md (modified): YES — CODE-SIGN/weak-algorithm present
- quantum-chaos-enterprise-lab/README.md (modified): YES — code-signing referenced

Commits present:
- 9e2b72f (test RED): YES
- c14c934 (feat GREEN): YES
- 52b115a (feat chaos-lab): YES

Tests: 5/5 passed (test_run_scan_codesign_wiring.py)

Triple-update verified: TRIPLE-UPDATE-OK

lab.sh diff: empty (untouched)
