---
phase: 01-foundation-fixes
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - qcscan/scanner/ssh_scanner.py
  - qcscan/models.py
  - tests/test_ssh_scanner.py
autonomous: true
requirements: [CORE-04, SCAN-02]

must_haves:
  truths:
    - "Running a 100-host SSH scan completes meaningfully faster than sequential and does not drop results"
    - "An SSH scan returns KEX algorithms, host key types, and MAC algorithms — not just the banner string"
    - "ssh-audit JSON output is stored in ssh_audit_json column on CryptoEndpoint"
    - "tls_version field is no longer misused for SSH banner data"
  artifacts:
    - path: "qcscan/scanner/ssh_scanner.py"
      provides: "Threaded SSH scanner with ssh-audit integration"
      contains: "ThreadPoolExecutor"
    - path: "qcscan/models.py"
      provides: "CryptoEndpoint with ssh_audit_json column"
      contains: "ssh_audit_json"
    - path: "tests/test_ssh_scanner.py"
      provides: "Tests for threaded SSH scan and ssh-audit JSON parsing"
  key_links:
    - from: "qcscan/scanner/ssh_scanner.py"
      to: "qcscan/models.py"
      via: "CryptoEndpoint.ssh_audit_json field population"
      pattern: "ssh_audit_json"
    - from: "qcscan/scanner/ssh_scanner.py"
      to: "ssh-audit subprocess"
      via: "subprocess.run with -j flag"
      pattern: "subprocess\\.run.*ssh-audit"
---

<objective>
Replace the sequential banner-only SSH scanner with a threaded scanner that runs ssh-audit
for full algorithm enumeration (KEX, host keys, MACs, encryption).

Purpose: The current SSH scanner is sequential (blocking on 100+ hosts) and only grabs the
SSH banner string — missing all algorithm detail needed for CBOM and quantum-readiness scoring.

Output: ssh_scanner.py uses ThreadPoolExecutor matching TLS scanner pattern, runs ssh-audit
subprocess for each host, stores full JSON in ssh_audit_json column, falls back to banner
grab if ssh-audit is not installed.
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

<interfaces>
<!-- Key types and contracts the executor needs. -->

From qcscan/scanner/tls_scanner.py (ThreadPoolExecutor pattern to replicate):
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def scan_tls_targets(
    cfg,
    targets: List[Tuple[str, int]],
    logger: Optional[Logger] = None,
    progress_cb: Optional[Callable[[int], None]] = None
) -> List[CryptoEndpoint]:
    results: List[CryptoEndpoint] = []
    with ThreadPoolExecutor(max_workers=cfg.scan.concurrency) as ex:
        futures = [
            ex.submit(scan_one, host, port, cfg.scan.timeout_seconds, cfg.scan.include_sni, logger, tls_enum_mode)
            for (host, port) in targets
        ]
        for f in as_completed(futures):
            results.append(f.result())
            if progress_cb:
                progress_cb(1)
    return results
```

From run_scan.py (SSH concurrency config):
```python
ssh_timeout = _get_scan_int(cfg, "ssh_timeout_seconds", cfg.scan.timeout_seconds)
ssh_conc = _get_scan_int(cfg, "ssh_concurrency", cfg.scan.concurrency)
cfg.scan.timeout_seconds = ssh_timeout
cfg.scan.concurrency = ssh_conc
ssh_endpoints = scan_ssh_targets(cfg, ssh_targets, logger=logger, progress_cb=None)
```

From qcscan/models.py (current CryptoEndpoint):
```python
class CryptoEndpoint(Base):
    __tablename__ = "crypto_endpoints"
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    protocol = Column(String(32), nullable=True)
    tls_version = Column(String(64), nullable=True)
    cipher_suite = Column(String(255), nullable=True)
    # ... cert fields ...
    # ssh_audit_json does NOT exist yet — must be added
```

ssh-audit JSON output schema (from RESEARCH.md):
```json
{
  "target": "hostname:22",
  "banner": {"raw": "SSH-2.0-OpenSSH_8.9p1", "protocol": "2.0", "software": "OpenSSH_8.9p1"},
  "kex": [{"algorithm": "curve25519-sha256", "keysize": null, "notes": {...}}],
  "key": [{"algorithm": "ssh-rsa", "keysize": 3072, "notes": {...}}],
  "enc": [{"algorithm": "aes128-ctr", "notes": {...}}],
  "mac": [{"algorithm": "hmac-sha2-256", "notes": {...}}],
  "fingerprints": [{"hash_alg": "SHA256", "hash": "SHA256:..."}]
}
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add ssh_audit_json column to CryptoEndpoint model</name>
  <files>qcscan/models.py</files>
  <read_first>
    - qcscan/models.py (full file — understand existing column layout and placement conventions)
  </read_first>
  <action>
    Per D-05: Add a single new column `ssh_audit_json` to CryptoEndpoint. Place it after
    the existing `tls_enum_notes` field (the last v3.6 TLS capability field). This is an
    additive-only schema change.

    Add this line after `tls_enum_notes = Column(Text, nullable=True)`:
    ```python
    # ==========================
    # v4.0 SSH audit fields
    # ==========================
    ssh_audit_json = Column(Text, nullable=True)  # Full ssh-audit JSON output
    ```

    SQLite handles additive columns transparently — existing databases will get NULL for
    this column on old rows. No migration script needed.
  </action>
  <verify>
    <automated>cd /Volumes/Digs-1TB/Development/quantum-apps/QuRisk && python -c "from qcscan.models import CryptoEndpoint; assert hasattr(CryptoEndpoint, 'ssh_audit_json'); print('OK: ssh_audit_json column exists')"</automated>
  </verify>
  <acceptance_criteria>
    - grep -n "ssh_audit_json" qcscan/models.py returns a match with Column(Text, nullable=True)
    - python -c "from qcscan.models import CryptoEndpoint; print(CryptoEndpoint.ssh_audit_json)" does not error
  </acceptance_criteria>
  <done>CryptoEndpoint model has ssh_audit_json TEXT column</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Rewrite ssh_scanner.py with ThreadPoolExecutor and ssh-audit integration</name>
  <files>qcscan/scanner/ssh_scanner.py, tests/test_ssh_scanner.py</files>
  <read_first>
    - qcscan/scanner/ssh_scanner.py (current implementation — understand exact function signatures that run_scan.py calls)
    - qcscan/scanner/tls_scanner.py (ThreadPoolExecutor pattern to replicate exactly)
    - qcscan/models.py (CryptoEndpoint fields including new ssh_audit_json)
    - run_scan.py (lines 334-354 — how scan_ssh_targets is called, cfg.scan.concurrency/timeout_seconds usage)
    - .planning/phases/01-foundation-fixes/01-RESEARCH.md (sections 2 and 3 — ssh-audit subprocess pattern and thread pool pattern)
  </read_first>
  <behavior>
    - test_scan_ssh_one_with_ssh_audit: Mock subprocess.run to return valid ssh-audit JSON, verify CryptoEndpoint.ssh_audit_json is populated, tls_version is NOT set to banner
    - test_scan_ssh_one_without_ssh_audit: Mock shutil.which to return None, verify banner fallback works, ssh_audit_json is None
    - test_scan_ssh_one_ssh_audit_timeout: Mock subprocess.run to raise TimeoutExpired, verify fallback to banner, no crash
    - test_scan_ssh_targets_uses_threadpool: Mock scan_ssh_one, call scan_ssh_targets with 5 targets, verify all 5 results returned
    - test_scan_ssh_one_sets_cipher_suite_ssh: Verify cipher_suite is set to "SSH" marker (per D-06)
    - test_scan_ssh_one_does_not_set_tls_version: Verify tls_version is NOT set for SSH endpoints (per D-06)
  </behavior>
  <action>
    **Write tests/test_ssh_scanner.py FIRST (RED phase):**
    - Use unittest.mock to mock subprocess.run and shutil.which
    - Create a sample ssh-audit JSON dict matching the schema from RESEARCH.md section 2.4
    - Test all behaviors listed above

    **Then rewrite qcscan/scanner/ssh_scanner.py (GREEN phase):**

    Per D-04, D-05, D-06, D-07:

    New imports at top:
    ```python
    import json
    import shutil
    import socket
    import subprocess
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from datetime import datetime, timezone
    from typing import List, Tuple, Optional, Callable

    from qcscan.models import CryptoEndpoint
    from qcscan.logging_util import Logger
    ```

    New internal function `_run_ssh_audit(host, port, timeout)`:
    ```python
    def _run_ssh_audit(host: str, port: int, timeout: int) -> Optional[dict]:
        exe = shutil.which("ssh-audit")
        if not exe:
            return None
        try:
            proc = subprocess.run(
                [exe, "-j", host, str(port)],
                capture_output=True,
                text=True,
                timeout=timeout + 5,
            )
            if proc.stdout.strip():
                return json.loads(proc.stdout)
            return None
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
            return None
    ```

    Rewrite `scan_ssh_one(host, port, timeout, logger)`:
    - Create CryptoEndpoint with protocol="SSH", scanned_at=now, cipher_suite="SSH" (D-06 marker)
    - Do NOT set tls_version (D-06 — stop misusing this field)
    - Try ssh-audit first via _run_ssh_audit()
    - If ssh-audit returns data:
      - Set ep.ssh_audit_json = json.dumps(audit_data)
      - Extract banner from audit_data["banner"]["raw"] if present, store in ep.service_detail
      - Log success with algorithm counts
    - If ssh-audit unavailable or fails:
      - Log warning: "ssh-audit not found — install with: pip install ssh-audit. Falling back to banner scan."
      - Fall back to socket banner grab (existing logic minus the tls_version assignment)
      - Store banner in ep.service_detail instead of ep.tls_version
    - Catch all exceptions, set ep.scan_error, never raise

    Rewrite `scan_ssh_targets(cfg, targets, logger, progress_cb)`:
    - Keep EXACT same function signature (run_scan.py depends on it)
    - Use ThreadPoolExecutor(max_workers=cfg.scan.concurrency) — matches TLS pattern (D-07)
    - Submit scan_ssh_one for each (host, port) target
    - Collect results via as_completed(futures)
    - Call progress_cb(1) per completed future
    - Log start/completion counts like TLS scanner does
  </action>
  <verify>
    <automated>cd /Volumes/Digs-1TB/Development/quantum-apps/QuRisk && python -m pytest tests/test_ssh_scanner.py -x -v 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - grep -n "ThreadPoolExecutor" qcscan/scanner/ssh_scanner.py returns a match
    - grep -n "ssh-audit" qcscan/scanner/ssh_scanner.py returns matches (subprocess invocation)
    - grep -n "ssh_audit_json" qcscan/scanner/ssh_scanner.py returns a match (field population)
    - grep -n "cipher_suite.*SSH" qcscan/scanner/ssh_scanner.py returns a match (SSH marker per D-06)
    - grep -cn "tls_version" qcscan/scanner/ssh_scanner.py returns 0 (no longer misused per D-06)
    - python -m pytest tests/test_ssh_scanner.py -x -v passes all tests
  </acceptance_criteria>
  <done>SSH scanner uses ThreadPoolExecutor for concurrent scanning, runs ssh-audit subprocess for full algorithm enumeration, stores JSON in ssh_audit_json, falls back to banner on ssh-audit absence, tls_version no longer misused</done>
</task>

</tasks>

<verification>
- `python -m pytest tests/ -x -q` passes (all existing + new tests)
- `grep -n "ThreadPoolExecutor" qcscan/scanner/ssh_scanner.py` shows thread pool usage
- `grep -n "ssh_audit_json" qcscan/models.py` shows new column
- `grep -cn "tls_version" qcscan/scanner/ssh_scanner.py` returns 0
- `python -c "from qcscan.scanner.ssh_scanner import scan_ssh_targets; print('import OK')"` succeeds
</verification>

<success_criteria>
- SSH scanner uses ThreadPoolExecutor with cfg.scan.concurrency workers (CORE-04)
- ssh-audit subprocess integration with JSON parsing (SCAN-02)
- ssh_audit_json column exists on CryptoEndpoint (SCAN-02)
- tls_version field no longer misused for SSH data (D-06)
- Graceful fallback when ssh-audit not installed
- All tests pass
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation-fixes/01-02-SUMMARY.md`
</output>
