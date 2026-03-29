---
phase: 01-foundation-fixes
plan: 03
type: execute
wave: 2
depends_on: [02]
files_modified:
  - qcscan/scanner/tls_scanner.py
  - qcscan/models.py
  - tests/test_sslyze_integration.py
autonomous: true
requirements: [SCAN-01]

must_haves:
  truths:
    - "A TLS scan against a target returns cipher suite details, certificate chain, and protocol version sourced from sslyze"
    - "If sslyze is not installed or fails for a target, the existing ssl+cryptography scanner runs as fallback"
    - "sslyze-only data (full cipher list, chain depth, curves) is stored in tls_capabilities_json"
  artifacts:
    - path: "qcscan/scanner/tls_scanner.py"
      provides: "sslyze primary scanner with existing code as fallback"
      contains: "from sslyze import"
    - path: "qcscan/models.py"
      provides: "CryptoEndpoint with tls_capabilities_json column"
      contains: "tls_capabilities_json"
    - path: "tests/test_sslyze_integration.py"
      provides: "Tests for sslyze primary path and fallback path"
  key_links:
    - from: "qcscan/scanner/tls_scanner.py"
      to: "sslyze library"
      via: "Scanner.queue_scans() and get_results()"
      pattern: "from sslyze import"
    - from: "qcscan/scanner/tls_scanner.py"
      to: "qcscan/models.py"
      via: "CryptoEndpoint.tls_capabilities_json population"
      pattern: "tls_capabilities_json"
---

<objective>
Integrate sslyze as the primary TLS scanner, with the existing ssl+cryptography code as
fallback when sslyze fails or is not installed.

Purpose: The current TLS scanner uses Python's ssl module which only sees the negotiated
cipher — not the full list of supported ciphers, protocol versions, and curves. sslyze
provides deep enumeration needed for accurate quantum-readiness scoring and CBOM.

Output: tls_scanner.py tries sslyze first for each target, maps results to CryptoEndpoint
fields, stores extended data in tls_capabilities_json, falls back to existing scanner on
sslyze errors.
</objective>

<execution_context>
@/Users/digs/.claude/get-shit-done/workflows/execute-plan.md
@/Users/digs/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-foundation-fixes/01-CONTEXT.md
@.planning/phases/01-foundation-fixes/01-RESEARCH.md
@.planning/phases/01-foundation-fixes/01-02-SUMMARY.md

<interfaces>
<!-- Key types and contracts the executor needs. -->

From qcscan/scanner/tls_scanner.py (current functions that become fallback):
```python
def scan_one(host, port, timeout, include_sni, logger=None, tls_enum_mode="fast") -> CryptoEndpoint:
    # Creates CryptoEndpoint, does ssl handshake, populates cert_* fields
    # This becomes the FALLBACK path

def scan_tls_targets(cfg, targets, logger=None, progress_cb=None) -> List[CryptoEndpoint]:
    # ThreadPoolExecutor orchestration — stays as-is but calls new scan_one_sslyze first

def _pubkey_info(pubkey) -> Tuple[str, Optional[int]]:
    # Returns (alg_name, key_size) from cryptography public key object
    # Reusable with sslyze since sslyze returns cryptography x509 objects

def _extract_sans(cert) -> str:
    # Extracts SANs from cryptography x509 cert — reusable with sslyze

def _categorize_tls_error(e) -> str:
    # Error classification — reusable
```

From qcscan/models.py (after Plan 02 adds ssh_audit_json):
```python
class CryptoEndpoint(Base):
    tls_version = Column(String(64), nullable=True)
    cipher_suite = Column(String(255), nullable=True)
    cert_subject = Column(Text, nullable=True)
    cert_issuer = Column(Text, nullable=True)
    cert_sans = Column(Text, nullable=True)
    cert_sig_alg = Column(String(128), nullable=True)
    cert_pubkey_alg = Column(String(64), nullable=True)
    cert_pubkey_size = Column(Integer, nullable=True)
    cert_not_before = Column(DateTime, nullable=True)
    cert_not_after = Column(DateTime, nullable=True)
    tls_supported_versions = Column(Text, nullable=True)
    tls_supported_ciphers_sample = Column(Text, nullable=True)
    tls_weak_ciphers_present = Column(Boolean, default=False)
    tls_legacy_suites_present = Column(Boolean, default=False)
    tls_pfs_supported = Column(Boolean, default=False)
    tls_enum_mode = Column(String(16), nullable=True)
    tls_enum_notes = Column(Text, nullable=True)
    ssh_audit_json = Column(Text, nullable=True)
    # tls_capabilities_json does NOT exist yet — must be added in this plan
```

sslyze API (from RESEARCH.md section 1):
```python
from sslyze import (
    Scanner, ServerScanRequest, ServerNetworkLocation,
    ScanCommand, ServerNetworkConfiguration,
    ScanCommandAttemptStatusEnum, ServerScanStatusEnum,
)

# ScanCommands to use (no vuln checks — those are Phase 3):
SCAN_COMMANDS = {
    ScanCommand.CERTIFICATE_INFO,
    ScanCommand.SSL_2_0_CIPHER_SUITES,
    ScanCommand.SSL_3_0_CIPHER_SUITES,
    ScanCommand.TLS_1_0_CIPHER_SUITES,
    ScanCommand.TLS_1_1_CIPHER_SUITES,
    ScanCommand.TLS_1_2_CIPHER_SUITES,
    ScanCommand.TLS_1_3_CIPHER_SUITES,
    ScanCommand.ELLIPTIC_CURVES,
}

# Cert chain access:
deployment = cert_result.result.certificate_deployments[0]
leaf = deployment.received_certificate_chain[0]  # cryptography x509.Certificate
chain_depth = len(deployment.received_certificate_chain)
is_trusted = deployment.verified_certificate_chain is not None
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add tls_capabilities_json column to CryptoEndpoint</name>
  <files>qcscan/models.py</files>
  <read_first>
    - qcscan/models.py (full file — check tls_capabilities_json does NOT already exist, find correct placement)
  </read_first>
  <action>
    Per D-03: Add `tls_capabilities_json` column to CryptoEndpoint. Check if it already
    exists first (RESEARCH.md confirms it does NOT). Place it after `tls_enum_notes`:

    ```python
    tls_capabilities_json = Column(Text, nullable=True)  # sslyze deep scan results (JSON)
    ```

    This goes between the existing `tls_enum_notes` line and the `ssh_audit_json` line
    (added by Plan 02).
  </action>
  <verify>
    <automated>cd /Volumes/Digs-1TB/Development/quantum-apps/QuRisk && python -c "from qcscan.models import CryptoEndpoint; assert hasattr(CryptoEndpoint, 'tls_capabilities_json'); print('OK: tls_capabilities_json column exists')"</automated>
  </verify>
  <acceptance_criteria>
    - grep -n "tls_capabilities_json" qcscan/models.py returns a match with Column(Text, nullable=True)
  </acceptance_criteria>
  <done>CryptoEndpoint has tls_capabilities_json TEXT column for sslyze extended data</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Integrate sslyze as primary TLS scanner with fallback</name>
  <files>qcscan/scanner/tls_scanner.py, tests/test_sslyze_integration.py</files>
  <read_first>
    - qcscan/scanner/tls_scanner.py (full file — understand scan_one, scan_tls_targets, helper functions)
    - qcscan/models.py (CryptoEndpoint fields — all cert_* fields and new tls_capabilities_json)
    - .planning/phases/01-foundation-fixes/01-RESEARCH.md (section 1 — sslyze API patterns, ScanCommand set, error handling, field mapping)
    - qcscan/scanner/tls_capabilities.py (existing capability enumeration — may overlap with sslyze)
  </read_first>
  <behavior>
    - test_sslyze_available_success: Mock sslyze imports and Scanner to return completed result, verify CryptoEndpoint fields populated from sslyze data, verify tls_capabilities_json contains sslyze extended data
    - test_sslyze_not_installed: Mock ImportError on sslyze import, verify fallback to existing scan_one, verify warning logged
    - test_sslyze_scan_error_falls_back: Mock sslyze to return ERROR_NO_CONNECTIVITY status, verify fallback to existing scan_one runs
    - test_sslyze_maps_cert_fields: Verify cert_subject, cert_issuer, cert_pubkey_alg, cert_pubkey_size, cert_sig_alg populated from sslyze cert result
    - test_tls_capabilities_json_structure: Verify tls_capabilities_json contains accepted_by_version, chain_depth, elliptic_curves keys
  </behavior>
  <action>
    **Write tests/test_sslyze_integration.py FIRST (RED phase):**
    - Mock sslyze classes (Scanner, ServerScanRequest, etc.) since sslyze may not be installed
    - Create mock ServerScanResult objects with completed status
    - Create mock certificate deployment with cryptography x509 cert objects
    - Test field mapping and fallback behavior

    **Then modify qcscan/scanner/tls_scanner.py (GREEN phase):**

    Per D-01, D-02, D-03:

    **Add sslyze availability check at module level:**
    ```python
    try:
        from sslyze import (
            Scanner as SslyzeScanner,
            ServerScanRequest,
            ServerNetworkLocation,
            ScanCommand,
            ServerNetworkConfiguration,
            ScanCommandAttemptStatusEnum,
            ServerScanStatusEnum,
        )
        SSLYZE_AVAILABLE = True
    except ImportError:
        SSLYZE_AVAILABLE = False
    ```

    **Create new function `_scan_one_sslyze(host, port, timeout, include_sni, logger)`:**
    - Returns Optional[CryptoEndpoint] — None means "sslyze failed, use fallback"
    - If not SSLYZE_AVAILABLE: log warning once, return None
    - Build ServerScanRequest with the ScanCommand set from RESEARCH.md section 1.3:
      CERTIFICATE_INFO, SSL_2_0 through TLS_1_3_CIPHER_SUITES, ELLIPTIC_CURVES
    - Use ServerNetworkConfiguration with tls_server_name_indication and network_timeout
    - Create Scanner(per_server_concurrent_connections_limit=2), queue and get results
    - If scan_status != COMPLETED: return None (triggers fallback)
    - Map certificate info to CryptoEndpoint fields using existing _pubkey_info() and _extract_sans():
      - leaf = deployment.received_certificate_chain[0]
      - ep.cert_subject = leaf.subject.rfc4514_string()
      - ep.cert_issuer = leaf.issuer.rfc4514_string()
      - ep.cert_sans = _extract_sans(leaf)
      - ep.cert_sig_alg = leaf.signature_hash_algorithm.name
      - alg, size = _pubkey_info(leaf.public_key())
      - ep.cert_pubkey_alg = alg
      - ep.cert_pubkey_size = size
      - ep.cert_not_before / cert_not_after from leaf (same date handling as existing code)
    - Determine highest TLS version from accepted cipher suites:
      - Check TLS 1.3, 1.2, 1.1, 1.0 in order; first with accepted suites = ep.tls_version
      - ep.cipher_suite = first accepted cipher from highest version
    - Map to existing v3.6 capability fields:
      - ep.tls_supported_versions = comma-joined list of versions with accepted suites
      - ep.tls_supported_ciphers_sample = first 10 accepted cipher names comma-joined
      - ep.tls_weak_ciphers_present = True if SSL2 or SSL3 have accepted suites
      - ep.tls_legacy_suites_present = True if TLS 1.0 or 1.1 have accepted suites
      - ep.tls_pfs_supported = True if any ECDHE/DHE cipher accepted
      - ep.tls_enum_mode = "sslyze"
    - Build tls_capabilities_json dict per D-03 / RESEARCH.md section 1.7:
      ```python
      import sslyze
      caps = {
          "source": "sslyze",
          "sslyze_version": sslyze.__version__,
          "accepted_by_version": { version: [cipher_names...] for each protocol },
          "chain_depth": len(deployment.received_certificate_chain),
          "chain_verified": deployment.verified_certificate_chain is not None,
          "elliptic_curves": [curve.name for curve in elliptic_curves_result.supported_curves] if available,
      }
      ep.tls_capabilities_json = json.dumps(caps)
      ```
    - Wrap entire function in try/except: any exception returns None (triggers fallback)

    **Modify existing scan_one() to become the fallback:**
    - Rename current `scan_one` to `_scan_one_fallback` (D-02 — existing code NOT deleted)
    - Create new `scan_one` that:
      1. Tries `_scan_one_sslyze()` first
      2. If returns None: calls `_scan_one_fallback()` (the old scan_one)
      3. Returns the CryptoEndpoint from whichever succeeded

    ```python
    def scan_one(host, port, timeout, include_sni, logger=None, tls_enum_mode="fast") -> CryptoEndpoint:
        if SSLYZE_AVAILABLE:
            try:
                ep = _scan_one_sslyze(host, port, timeout, include_sni, logger)
                if ep is not None:
                    return ep
            except Exception as e:
                if logger:
                    logger.v(f"sslyze failed for {host}:{port}, falling back: {e}")
        return _scan_one_fallback(host, port, timeout, include_sni, logger, tls_enum_mode)
    ```

    **scan_tls_targets() stays unchanged** — it already calls scan_one() via ThreadPoolExecutor.
  </action>
  <verify>
    <automated>cd /Volumes/Digs-1TB/Development/quantum-apps/QuRisk && python -m pytest tests/test_sslyze_integration.py -x -v 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - grep -n "from sslyze import" qcscan/scanner/tls_scanner.py returns a match inside a try block
    - grep -n "SSLYZE_AVAILABLE" qcscan/scanner/tls_scanner.py returns matches
    - grep -n "_scan_one_sslyze" qcscan/scanner/tls_scanner.py returns a function definition
    - grep -n "_scan_one_fallback" qcscan/scanner/tls_scanner.py returns a function definition (old scan_one renamed)
    - grep -n "tls_capabilities_json" qcscan/scanner/tls_scanner.py returns a match (field population)
    - python -m pytest tests/test_sslyze_integration.py -x -v passes all tests
    - python -m pytest tests/ -x -q passes (no regressions)
  </acceptance_criteria>
  <done>sslyze is primary TLS scanner path, existing ssl+cryptography code is fallback, tls_capabilities_json populated with extended data, graceful handling when sslyze not installed, all tests pass</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/ -x -q` passes
- `grep -n "SSLYZE_AVAILABLE" qcscan/scanner/tls_scanner.py` confirms conditional import
- `grep -n "tls_capabilities_json" qcscan/models.py` confirms column exists
- `python -c "from qcscan.scanner.tls_scanner import scan_one; print('import OK')"` succeeds
</verification>

<success_criteria>
- sslyze is primary TLS scanner when installed (SCAN-01)
- Existing scanner code preserved as fallback (D-01, D-02)
- tls_capabilities_json stores extended sslyze data (D-03)
- Graceful fallback on sslyze absence or per-target failure
- All existing and new tests pass
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation-fixes/01-03-SUMMARY.md`
</output>
