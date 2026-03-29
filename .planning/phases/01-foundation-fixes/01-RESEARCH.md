# Phase 1: Foundation Fixes — Research

**Researched:** 2026-03-28
**Domain:** Python scanner internals — sslyze, ssh-audit subprocess, SQLAlchemy SQLite, package rename
**Confidence:** HIGH (all findings verified against live source code or official documentation)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** sslyze is the primary TLS scanner. If sslyze fails for a target, fall back to the existing `ssl`+`cryptography` scanner. Two code paths — sslyze primary, existing as else/except.
- **D-02:** `tls_scanner.py` is NOT deleted — it becomes the fallback code path.
- **D-03:** sslyze results map to existing `CryptoEndpoint` fields. New sslyze-only data (cipher suite list, chain depth, protocol version matrix) goes into `tls_capabilities_json` — check if this field exists, if not add it additively.
- **D-04:** Run ssh-audit as a subprocess (`ssh-audit --json`), parse JSON output. Library import NOT used.
- **D-05:** Store full ssh-audit JSON output in a single new column `ssh_audit_json TEXT` on `CryptoEndpoint`. One additive schema change. No typed columns.
- **D-06:** `tls_version` field is no longer misused for SSH data. `cipher_suite = "SSH"` marker identifies SSH endpoints.
- **D-07:** Replace sequential loop in `scan_ssh_targets()` with `ThreadPoolExecutor`. Match existing TLS scanner concurrency patterns.
- **D-08:** `intelligence/scoring.py` → `compute_readiness_score(evidence)` is the single authoritative scoring path.
- **D-09:** Remove `assessment.readiness_score.compute_readiness_score()` call from `writer.py` line ~586.
- **D-10:** Replace `_score_from_evidence()` in `writer.py` with a call to `intelligence.scoring.compute_readiness_score(evidence)`.
- **D-11:** `assessment/readiness_score.py` is dead code after D-09. Delete it and its imports from `writer.py`.
- **D-12:** Fix `_extract_cert_key_type()` in `writer.py`. Replace the probe list with `cert_pubkey_alg` as the first (and primary) check.
- **D-13:** Full package rename — `qcscan/` → `quirk/`. All Python imports updated `from qcscan.xxx` → `from quirk.xxx`. Sed sweep across all `.py` files.
- **D-14:** `pyproject.toml` / `setup.py` package name updated to `quirk`.
- **D-15:** CLI entry point renamed: `run_scan.py` becomes the `quirk` command entry point. `quirk --help`, `quirk scan`, etc.
- **D-16:** User-facing strings updated: `PLATFORM_VERSION` stays `"3.9"` but product name in report headers → `"QU.I.R.K."`. Config keys `qcscan` → `quirk`. Markdown report headers updated.
- **D-17:** The one remaining `QuRisk` reference in `validate.py` is updated.

### Claude's Discretion

- Exact sslyze `ScanCommand` set (which commands to run per target)
- sslyze async vs synchronous scan execution model
- ThreadPoolExecutor pool size for SSH scanner (infer from existing TLS pool config)
- How to handle ssh-audit not installed (clear error message + install instructions)
- How to handle sslyze not installed (graceful fallback to existing scanner, warning logged)

### Deferred Ideas (OUT OF SCOPE)

- sslyze ROBOT/DROWN/HEARTBLEED vulnerability checks — Phase 3
- ssh-audit remediation suggestions in the report — Phase 6
- Making sslyze/ssh-audit hard requirements with version pinning — Phase 7
- `quirk serve` (dashboard command) — Phase 5
- pip install quirk distribution — Phase 7
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORE-01 | Scoring system consolidation — single authoritative path through writer.py evidence model | §5 Scoring Consolidation: documents the exact impedance mismatch and fix required |
| CORE-02 | Fix cert_pubkey_alg field propagation in writer.py (_extract_cert_key_type mismatch) | §6 cert_pubkey_alg Fix: confirms field exists on model, shows exact bug and one-line fix |
| CORE-03 | Rename QuRisk → QU.I.R.K. / quirk throughout codebase | §4 Package Rename: enumerates all files, counts, sed commands, packaging gap |
| CORE-04 | SSH scanner thread-pool — replace sequential per-host loop | §3 Thread Pool Pattern: exact TLS pattern to replicate |
| SCAN-01 | sslyze TLS deep scan integration | §1 sslyze Python API: full API, ScanCommands, field mapping, error handling |
| SCAN-02 | ssh-audit KEX/hostkey/MAC full enumeration | §2 ssh-audit Subprocess: exact command, JSON schema, error handling |
</phase_requirements>

---

## 1. sslyze Python API

**Version to target:** 6.3.1 (latest as of 2026-03-28)
**Install:** `pip install sslyze`
**Python requirement:** 3.10+
**Confidence:** HIGH — verified against official sslyze documentation

### 1.1 sslyze is NOT currently installed

Neither the project venv nor the system Python has sslyze installed. The implementation plan must include an install step (or a conditional import with graceful fallback). Per D-01, sslyze absence should trigger silent fallback to the existing scanner with a warning logged.

### 1.2 Core API Pattern

```python
from sslyze import (
    Scanner,
    ServerScanRequest,
    ServerNetworkLocation,
    ScanCommand,
    ServerNetworkConfiguration,
    ScanCommandAttemptStatusEnum,
    ServerScanStatusEnum,
)

# Build the request — only the commands we need
scan_request = ServerScanRequest(
    server_location=ServerNetworkLocation(hostname=host, port=port),
    network_configuration=ServerNetworkConfiguration(
        tls_server_name_indication=host if include_sni and not is_ip else None,
        network_timeout=timeout,
    ),
    scan_commands={
        ScanCommand.CERTIFICATE_INFO,
        ScanCommand.SSL_2_0_CIPHER_SUITES,
        ScanCommand.SSL_3_0_CIPHER_SUITES,
        ScanCommand.TLS_1_0_CIPHER_SUITES,
        ScanCommand.TLS_1_1_CIPHER_SUITES,
        ScanCommand.TLS_1_2_CIPHER_SUITES,
        ScanCommand.TLS_1_3_CIPHER_SUITES,
        ScanCommand.ELLIPTIC_CURVES,
    },
)

scanner = Scanner(per_server_concurrent_connections_limit=2)
scanner.queue_scans([scan_request])

for server_result in scanner.get_results():
    if server_result.scan_status != ServerScanStatusEnum.COMPLETED:
        # Host unreachable — use fallback scanner
        raise RuntimeError(f"sslyze could not reach {host}:{port}")

    scan = server_result.scan_result
    ...
```

### 1.3 Recommended ScanCommand Set

For this phase (SCAN-01), run only these commands per CONTEXT.md D-03 (no vulnerability checks — those are Phase 3):

| Command | Purpose | Maps To |
|---------|---------|---------|
| `CERTIFICATE_INFO` | Leaf cert subject/issuer/expiry/pubkey/chain | `cert_*` fields + chain data → `tls_capabilities_json` |
| `TLS_1_0_CIPHER_SUITES` through `TLS_1_3_CIPHER_SUITES` | Accepted/rejected cipher list per version | `tls_supported_ciphers_sample`, `tls_weak_ciphers_present`, `tls_capabilities_json` |
| `SSL_2_0_CIPHER_SUITES`, `SSL_3_0_CIPHER_SUITES` | Legacy protocol detection | `tls_legacy_suites_present`, `tls_capabilities_json` |
| `ELLIPTIC_CURVES` | Named curves supported | `tls_capabilities_json` |

Do NOT include `ROBOT`, `HEARTBLEED`, `OPENSSL_CCS_INJECTION`, `SESSION_RESUMPTION`, `HTTP_HEADERS` — these are Phase 3 scope.

### 1.4 Accessing Cipher Suite Results

```python
# Accepted cipher suites for a given protocol version
tls13_attempt = scan.tls_1_3_cipher_suites
if tls13_attempt.status == ScanCommandAttemptStatusEnum.COMPLETED:
    for suite in tls13_attempt.result.accepted_cipher_suites:
        name = suite.cipher_suite.name   # e.g. "TLS_AES_256_GCM_SHA384"

# tls_version_used tells you the actual version negotiated
tls_version = tls13_attempt.result.tls_version_used   # TlsVersionEnum
```

The `.tls_version_used` field is a `TlsVersionEnum`. Map to the string the existing scanner returns (e.g., `"TLSv1.3"`) for consistency with the `CryptoEndpoint.tls_version` field.

### 1.5 Accessing Certificate Info

```python
cert_attempt = scan.certificate_info
if cert_attempt.status == ScanCommandAttemptStatusEnum.COMPLETED:
    # certificate_deployments is a list; index 0 is the SNI-matched deployment
    deployment = cert_attempt.result.certificate_deployments[0]

    # The leaf cert is a cryptography.x509.Certificate object
    leaf = deployment.received_certificate_chain[0]

    # All standard cryptography library attributes apply:
    leaf.subject.rfc4514_string()
    leaf.issuer.rfc4514_string()
    leaf.not_valid_before_utc   # or .not_valid_before on older cryptography
    leaf.not_valid_after_utc
    leaf.public_key()           # → use same _pubkey_info() helper from tls_scanner.py
    leaf.signature_hash_algorithm.name

    # Chain depth
    chain_depth = len(deployment.received_certificate_chain)

    # Trust verification — None means chain validation failed (self-signed or untrusted)
    is_trusted = deployment.verified_certificate_chain is not None
```

The `cryptography` library objects returned by sslyze are identical to those already used in `tls_scanner.py`. The existing `_pubkey_info()`, `_extract_sans()`, and date-handling code can be reused without modification.

### 1.6 Error Handling (sslyze Error States)

```python
# Scan-level failure (host unreachable, connection refused)
if server_result.scan_status != ServerScanStatusEnum.COMPLETED:
    # server_result.scan_status is ServerScanStatusEnum.ERROR_NO_CONNECTIVITY
    # Fall through to fallback scanner

# Per-command failure (e.g., certificate_info could connect but cert fetch failed)
if cert_attempt.status == ScanCommandAttemptStatusEnum.ERROR:
    error_reason = cert_attempt.error_reason   # string
    error_trace = cert_attempt.error_trace     # optional traceback

# ScanCommandAttemptStatusEnum values:
# COMPLETED — result is available
# ERROR — command failed; result is None; check error_reason
# NOT_SCHEDULED — command was not in the scan_commands set
```

**Fallback trigger:** Any `ServerScanStatusEnum.ERROR_NO_CONNECTIVITY` on the outer scan result. Per D-01, log a warning and call `tls_scanner.scan_one()` directly.

### 1.7 `tls_capabilities_json` Column

The column `tls_capabilities_json` does NOT currently exist on `CryptoEndpoint` (verified in `qcscan/models.py`). Add it additively as `Column(Text, nullable=True)`. Structure for this column:

```json
{
  "source": "sslyze",
  "sslyze_version": "6.3.1",
  "accepted_by_version": {
    "TLSv1.0": ["cipher1", "cipher2"],
    "TLSv1.2": ["cipher1"],
    "TLSv1.3": ["TLS_AES_256_GCM_SHA384"]
  },
  "rejected_by_version": {...},
  "chain_depth": 3,
  "chain_verified": true,
  "elliptic_curves": ["x25519", "secp256r1"]
}
```

### 1.8 sslyze Dependency Compatibility Warning

sslyze 6.3.1 requires `cryptography>=43,<47`. The project currently pins `cryptography==44.0.1` in `requirements.txt` — this is within the acceptable range. No conflict.

---

## 2. ssh-audit Subprocess Interface

**Version to target:** 3.3.0 (latest on PyPI as of 2026-03-28; same project as jtesta/ssh-audit)
**Install:** `pip install ssh-audit`
**Confidence:** HIGH — verified against jtesta/ssh-audit source and PyPI

### 2.1 ssh-audit is NOT Currently Installed

Neither the venv nor system PATH has `ssh-audit`. The implementation must check for its presence at runtime, and fall back to the existing banner-grab with a warning if not found. Per CONTEXT.md specifics: "if not installed, SSH endpoints fall back to banner-grab with a warning."

### 2.2 Exact Command Syntax

```bash
# Single target with JSON output (compact)
ssh-audit -j <hostname> <port>

# Single target with pretty-printed JSON
ssh-audit -jj <hostname> <port>

# Use -j (compact) for subprocess parsing — easier to handle single-line output
```

The `-j` flag (not `--json`) is the correct flag. Port is a positional argument, not a flag.

### 2.3 Subprocess Invocation Pattern

```python
import subprocess, json, shutil

def _run_ssh_audit(host: str, port: int, timeout: int) -> Optional[dict]:
    exe = shutil.which("ssh-audit")
    if not exe:
        return None   # caller logs warning and uses banner fallback

    try:
        proc = subprocess.run(
            [exe, "-j", host, str(port)],
            capture_output=True,
            text=True,
            timeout=timeout + 5,   # generous timeout: ssh-audit has its own timeout logic
        )
        # Non-zero exit code on connection failure — check stdout before trusting
        if proc.stdout.strip():
            return json.loads(proc.stdout)
        return None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None
```

### 2.4 JSON Output Schema

```json
{
  "target": "hostname:22",
  "banner": {
    "raw": "SSH-2.0-OpenSSH_8.9p1",
    "protocol": "2.0",
    "software": "OpenSSH_8.9p1"
  },
  "kex": [
    {
      "algorithm": "curve25519-sha256",
      "keysize": null,
      "notes": {
        "info": ["available since OpenSSH 6.5, Dropbear SSH 2013.62"],
        "warn": [],
        "fail": []
      }
    }
  ],
  "key": [
    {
      "algorithm": "ssh-rsa",
      "keysize": 3072,
      "ca_algorithm": null,
      "casize": null,
      "notes": {
        "fail": ["using broken SHA-1 hash algorithm"],
        "warn": ["2048-bit modulus only provides 112 bits of symmetric strength"],
        "info": []
      }
    }
  ],
  "enc": [
    {
      "algorithm": "aes128-ctr",
      "notes": {"info": [...], "warn": [...], "fail": [...]}
    }
  ],
  "mac": [
    {
      "algorithm": "hmac-sha2-256",
      "notes": {"info": [...], "warn": [...], "fail": [...]}
    }
  ],
  "fingerprints": [
    {"hash_alg": "MD5", "hash": "xx:xx:..."},
    {"hash_alg": "SHA256", "hash": "SHA256:..."}
  ],
  "recommendations": {
    "critical": {...},
    "warning": {...},
    "good": {...}
  }
}
```

### 2.5 Extracting Algorithm Lists

For CBOM purposes (Phase 2), the planner needs to know how to extract algorithm names from the raw JSON. The entire JSON blob is stored in `ssh_audit_json` (D-05) — no parsing is needed during Phase 1 beyond storing it. However the implementation should confirm parse succeeds:

```python
kex_algorithms  = [item["algorithm"] for item in data.get("kex", [])]
host_key_types  = [item["algorithm"] for item in data.get("key", [])]
mac_algorithms  = [item["algorithm"] for item in data.get("mac", [])]
enc_algorithms  = [item["algorithm"] for item in data.get("enc", [])]
```

### 2.6 Error and Unreachable Host Handling

- **Connection failure:** ssh-audit exits with `exitcodes.CONNECTION_ERROR` (non-zero). stdout may be empty or contain partial JSON. The subprocess wrapper must check `proc.returncode != 0` and/or empty `proc.stdout` before JSON parsing.
- **Timeout:** Use `subprocess.TimeoutExpired` handling. ssh-audit has its own internal timeout, but wrapping with `subprocess.run(timeout=...)` prevents infinite hang.
- **Not installed:** `shutil.which("ssh-audit")` returns `None`. Log warning: "ssh-audit not found — install with: pip install ssh-audit. Falling back to banner scan."

### 2.7 Storing in `ssh_audit_json`

Store `json.dumps(data)` if parse succeeded, `None` if ssh-audit was unavailable or failed. Do NOT store partial/error output.

---

## 3. Thread Pool Pattern (Exact Pattern to Replicate)

**Confidence:** HIGH — read directly from source

### 3.1 The Existing TLS Pattern (from `tls_scanner.py`)

```python
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

Key characteristics:
- `max_workers=cfg.scan.concurrency` — pulled directly from config, no hardcoded value
- `as_completed(futures)` — results collected as they finish (not in submission order)
- `progress_cb(1)` called per completed future — increment by 1 each time
- The per-host function (`scan_one`) handles its own exceptions and returns a populated `CryptoEndpoint` with `scan_error` set on failure — it never raises

### 3.2 How run_scan.py Sets SSH Concurrency

```python
ssh_timeout = _get_scan_int(cfg, "ssh_timeout_seconds", cfg.scan.timeout_seconds)
ssh_conc = _get_scan_int(cfg, "ssh_concurrency", cfg.scan.concurrency)

cfg.scan.timeout_seconds = ssh_timeout
cfg.scan.concurrency = ssh_conc

ssh_endpoints = scan_ssh_targets(cfg, ssh_targets, logger=logger, progress_cb=None)

cfg.scan.timeout_seconds = base_timeout
cfg.scan.concurrency = base_conc
```

`_get_scan_int(cfg, "ssh_concurrency", cfg.scan.concurrency)` reads `cfg.scan.ssh_concurrency` if it exists, otherwise falls back to `cfg.scan.concurrency`. The SSH scanner receives the already-modified `cfg.scan.concurrency` — it does not need to know about `ssh_concurrency` directly.

### 3.3 SSH Scanner Replacement Pattern

The new `scan_ssh_targets()` must match this exact signature and behavior:

```python
def scan_ssh_targets(
    cfg,
    targets: List[Tuple[str, int]],
    logger: Optional[Logger] = None,
    progress_cb: Optional[Callable[[int], None]] = None
) -> List[CryptoEndpoint]:
    results: List[CryptoEndpoint] = []

    with ThreadPoolExecutor(max_workers=cfg.scan.concurrency) as ex:
        futures = [
            ex.submit(scan_ssh_one, host, port, cfg.scan.timeout_seconds, logger)
            for (host, port) in targets
        ]
        for f in as_completed(futures):
            results.append(f.result())
            if progress_cb:
                progress_cb(1)

    return results
```

The `scan_ssh_one()` function must never raise — it catches all exceptions and returns a `CryptoEndpoint` with `scan_error` set. This is the same contract as `tls_scanner.scan_one()`.

### 3.4 Imports Required for SSH Scanner

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
```

These are already in `tls_scanner.py` and stdlib — no new dependencies.

---

## 4. Python Package Rename: qcscan → quirk

**Confidence:** HIGH — verified by reading all affected files

### 4.1 No Formal Packaging Exists

There is no `pyproject.toml`, no `setup.py`, no `setup.cfg` at the project root. The project runs as a local package (Python adds the repo root to sys.path). This means:

- No `[project]` name to update in pyproject.toml
- No `entry_points` to rename
- The `quirk` CLI entry point (D-15) must be created as a new mechanism

Per D-14, the plan must include creating a `pyproject.toml` (or `setup.py`) as part of this phase to give the package a proper name and the `quirk` console script entry point.

### 4.2 Scope of Import Changes

**Count of `from qcscan.` / `import qcscan` references:**
- Within `qcscan/` package itself: **38 occurrences** across all submodules
- In `run_scan.py`: **18 import lines** + 1 inline import at line 134 = 19 occurrences
- In `tests/`: **7 occurrences** across 6 test files

**Total: approximately 64 `qcscan` import references** to update.

### 4.3 The Rename Sequence

1. Rename directory: `mv qcscan quirk`
2. Update all imports: `find . -name "*.py" -not -path "./.venv/*" | xargs sed -i '' 's/from qcscan\./from quirk./g; s/import qcscan\./import quirk./g'`
3. Update string references: `find . -name "*.py" -not -path "./.venv/*" | xargs sed -i '' "s/'qcscan'/'quirk'/g; s/\"qcscan\"/\"quirk\"/g"`
4. Rename `run_scan.py` to `quirk.py` (or keep as `run_scan.py` and create a `quirk` entry point wrapper — see §4.4)
5. Update config.yaml references if any say `qcscan`
6. Verify: `grep -r "qcscan" . --include="*.py" --exclude-dir=.venv`

**macOS `sed` note:** On macOS, `sed -i ''` (with empty string after `-i`) is required. Linux uses `sed -i`. The `-i ''` form works on macOS; Linux users need `sed -i` without the empty string.

### 4.4 CLI Entry Point: `quirk` Command

Since there is no `pyproject.toml`, the simplest approach that satisfies D-15 is:

**Option A (recommended):** Keep `run_scan.py` as the implementation, create a thin `quirk.py` wrapper at the repo root:
```python
#!/usr/bin/env python3
from run_scan import main
if __name__ == "__main__":
    main()
```
Then users run `python quirk.py` or `./quirk.py`.

**Option B (proper, also recommended):** Create a minimal `pyproject.toml` with a console script:
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "quirk"
version = "3.9.0"
requires-python = ">=3.10"

[project.scripts]
quirk = "run_scan:main"
```
Then `pip install -e .` makes `quirk` available in the venv's bin. This is cleaner and aligns with D-14 and the Phase 7 packaging goal.

Given D-14 explicitly says `setup.py`/`pyproject.toml` must be updated, Option B is required. The existing lack of a `pyproject.toml` means it must be created from scratch.

### 4.5 User-Facing String Updates

Locations that say "qcscan" or "QuRisk" in user-visible strings (not just imports):

| File | Line | Current | Change To |
|------|------|---------|-----------|
| `qcscan/validate.py` | 2, 4, 7 | `qcscan.validate`, `QuRisk`, `python -m qcscan.validate` | `quirk.validate`, `QU.I.R.K.`, `python -m quirk.validate` |
| `run_scan.py` | 75 | `"Quantum Crypto Scanner (qcscan)"` | `"QU.I.R.K. — Quantum Infrastructure Readiness Kit"` |
| `qcscan/reports/writer.py` | 23 | `PLATFORM_VERSION = "3.9"` | Keep version; update product name strings in print/report output |
| `config.yaml` | TBD | Any `qcscan:` keys | `quirk:` |

Run `grep -rn "qcscan\|QuRisk" . --include="*.py" --include="*.yaml" --include="*.md" --exclude-dir=.venv` after rename to catch stragglers.

---

## 5. Scoring Consolidation

**Confidence:** HIGH — read all three scoring modules in full

### 5.1 The Critical Impedance Mismatch

This is the most complex part of the consolidation. There are **two different evidence dict schemas** in use:

**Schema A — `writer.py` `_normalize_evidence()` output:**
```python
{
    "endpoint_count": int,
    "finding_count": int,
    "protocol_counts": {"TLS": n, "HTTP": n, ...},
    "plaintext_http_count": int,
    "http_on_tls_port_count": int,
    "mtls_present_count": int,
    "cert_key_type_counts": {"RSA": n, ...},
    "expired_cert_count": int,
    "expiring_cert_count": int,
    "self_signed_cert_count": int,
    "scan_error_rate": float,
    "unknown_service_ratio": float,
}
```

**Schema B — `intelligence/evidence.py` `build_evidence_summary()` output (what `intelligence/scoring.py` expects):**
```python
{
    "totals": {"endpoints": int, "findings": int},
    "protocol_counts": {"TLS": n, ...},
    "plaintext_http_count": int,
    "http_on_tls_port_count": int,
    "mtls_present_count": int,
    "cert_key_type_counts": {"RSA": n, "ECDSA": n},
    "certificate_observations": {
        "certs_observed": int,
        "expired_count": int,
        "expiring_count": int,
        "self_signed_count": int,
    },
    "scan_error": {"count": int, "rate": float},
    "finding_severity_counts": {"CRITICAL": n, "HIGH": n, ...},
    "tls_enum_coverage_ratio": float,
    "finding_severity_counts": {...},
    ...
}
```

`intelligence/scoring.py:compute_readiness_score()` reads from Schema B. The existing `writer.py` `_score_from_evidence()` reads from Schema A. These are incompatible.

### 5.2 The Fix

Per D-10, replace `_score_from_evidence()` in `writer.py` with a call to `intelligence.scoring.compute_readiness_score(evidence)`. For this to work, `writer.py` must produce Schema B evidence — which means **replacing `_normalize_evidence()` with a call to `intelligence.evidence.build_evidence_summary()`**.

`build_evidence_summary(endpoints, findings)` is already the canonical evidence builder (used by `scorecard.py`). The fix is:

```python
# In writer.py write_reports(), replace:
evidence = _normalize_evidence(endpoints, findings)
score = _score_from_evidence(evidence)

# With:
from qcscan.intelligence.evidence import build_evidence_summary
from qcscan.intelligence.scoring import compute_readiness_score

evidence = build_evidence_summary(endpoints, findings)
score = compute_readiness_score(evidence)
```

The `_normalize_evidence()` function itself can be deleted (it becomes dead code). The `_score_from_evidence()`, `_confidence_from_evidence()`, `_drivers_from_evidence()`, and `_roadmap_from_evidence()` inline functions in `writer.py` are also dead code after this change — delete them.

### 5.3 What Else Uses the Legacy Assessment Path

In `writer.py` around line 584-588:
```python
confidence_legacy = compute_confidence(cfg, endpoints)
readiness_legacy = compute_readiness_score(cfg, endpoints, findings).to_dict()
transition_legacy = build_transition_roadmap(cfg, endpoints, findings).to_dict()
```

These produce `assessment-TIMESTAMP.json`. Per D-09, this entire block is removed. The `assessment/readiness_score.py` import at the top of `writer.py` (line 12) is deleted with it.

The `compute_confidence()` import from `assessment.confidence` is also removed. Note: there is a separate `intelligence.confidence.compute_confidence()` — this is a different function with a different signature. Do not confuse them.

### 5.4 Surviving Functions in writer.py After Consolidation

After the consolidation, `writer.py` retains:
- `write_reports()` — main orchestration
- `_extract_cert_key_type()` — fixed (see §6)
- `_extract_cert_dates()`, `_is_self_signed()`, `_mtls_present()` — still used by the evidence pipeline internally (but `_normalize_evidence()` itself is replaced)
- `_scorecard_markdown()`, `_roadmap_markdown()`, `_delta_*` helpers — still used
- `_delta_from_intelligence()`, `_delta_markdown()` — still used for delta reports

Functions to DELETE from `writer.py`:
- `_normalize_evidence()` — replaced by `build_evidence_summary()`
- `_score_from_evidence()` — replaced by `compute_readiness_score()`
- `_confidence_from_evidence()` — replaced by `intelligence.confidence.compute_confidence()`
- `_drivers_from_evidence()` — was a helper for `_score_from_evidence()`
- `_roadmap_from_evidence()` — replaced by `intelligence.roadmap.build_phased_roadmap()`

**Verify:** Check `scorecard.py` (the correct reference implementation) to see the exact call pattern before writing the new `writer.py` logic.

---

## 6. cert_pubkey_alg Field Fix

**Confidence:** HIGH — confirmed by reading both models.py and writer.py

### 6.1 The Bug

`writer.py` `_extract_cert_key_type()` at line 235:

```python
def _extract_cert_key_type(ep: Any) -> Optional[str]:
    for attr in ("cert_key_type", "cert_pubkey_type", "cert_public_key_type", "cert_key_algo", "cert_pubkey_algo"):
        v = getattr(ep, attr, None)
        if v:
            return str(v).upper()
    ...
    return None
```

The probe list contains **none of the actual field names**. `CryptoEndpoint` in `models.py` has `cert_pubkey_alg` — not `cert_pubkey_algo`, not `cert_key_type`, not any of the others.

### 6.2 The Fix

```python
def _extract_cert_key_type(ep: Any) -> Optional[str]:
    # cert_pubkey_alg is the canonical field on CryptoEndpoint
    v = getattr(ep, "cert_pubkey_alg", None)
    if v:
        return str(v).upper()
    # Fallback probe for any legacy/duck-typed endpoints
    for attr in ("cert_key_type", "cert_pubkey_type", "cert_public_key_type", "cert_key_algo", "cert_pubkey_algo"):
        v = getattr(ep, attr, None)
        if v:
            return str(v).upper()
    cert = getattr(ep, "cert", None)
    if isinstance(cert, dict):
        for k in ("key_type", "public_key_type", "pubkey_type", "algo"):
            if cert.get(k):
                return str(cert.get(k)).upper()
    return None
```

The key change: `cert_pubkey_alg` is probed FIRST, before the legacy list. Per D-12, the existing fallback chain can stay as a safety net (doesn't hurt).

### 6.3 Where This Field Is Populated

`tls_scanner.py` correctly sets `ep.cert_pubkey_alg = alg` at line 113. The bug is entirely in the consumer (`_extract_cert_key_type`), not the producer.

`intelligence/evidence.py` reads `cert_pubkey_alg` correctly at line 91: `key_alg = str(getattr(ep, "cert_pubkey_alg", "") or "").upper()`. Only `writer.py` has the bug.

---

## 7. SQLAlchemy Additive Migration

**Confidence:** HIGH — verified by reading db.py and models.py

### 7.1 No Alembic — Raw `create_all` Pattern

The project uses `Base.metadata.create_all(engine)` in `db.py:init_db()`. There is no Alembic, no migration scripts, no version table.

`create_all()` is **additive-only for new tables** but does NOT add new columns to existing tables. This is SQLAlchemy's behavior: if a table already exists, `create_all()` does nothing to it.

### 7.2 Adding Columns to Existing Databases

For both `ssh_audit_json` and `tls_capabilities_json`, the migration pattern must handle existing SQLite databases:

```python
from sqlalchemy import inspect, text

def _migrate_add_column(engine, table_name: str, col_name: str, col_type: str):
    """Add a column to an existing table if it doesn't exist yet."""
    inspector = inspect(engine)
    existing_cols = [col["name"] for col in inspector.get_columns(table_name)]
    if col_name not in existing_cols:
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"))
            conn.commit()
```

Call this in `db.py:init_db()` after `Base.metadata.create_all(engine)`:

```python
Base.metadata.create_all(engine)
_migrate_add_column(engine, "crypto_endpoints", "ssh_audit_json", "TEXT")
_migrate_add_column(engine, "crypto_endpoints", "tls_capabilities_json", "TEXT")
```

### 7.3 SQLite ALTER TABLE Limitations

SQLite's `ALTER TABLE ADD COLUMN` only supports a limited subset of constraints:
- The column must be nullable OR have a DEFAULT value
- Cannot add NOT NULL columns without a DEFAULT to existing tables
- Cannot add PRIMARY KEY or UNIQUE constraints via ALTER TABLE

Both `ssh_audit_json TEXT` (nullable) and `tls_capabilities_json TEXT` (nullable) are safe to add via `ALTER TABLE`. No issues.

### 7.4 Model Changes Required

Add to `CryptoEndpoint` in `models.py`:

```python
# Phase 1: sslyze deep scan data
tls_capabilities_json = Column(Text, nullable=True)

# Phase 1: ssh-audit full algorithm enumeration
ssh_audit_json = Column(Text, nullable=True)
```

These are additive. Existing scan data is unaffected (new columns are NULL for old rows).

---

## 8. Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| sslyze | SCAN-01 (TLS deep scan) | No | Not installed | Existing ssl+cryptography scanner (D-01) |
| ssh-audit | SCAN-02 (SSH algorithm enum) | No | Not installed | Existing banner-grab (D-06) |
| Python stdlib `concurrent.futures` | CORE-04 (SSH thread pool) | Yes | stdlib | None needed |
| SQLite | Schema migration | Yes | Bundled with Python | None needed |
| cryptography 44.0.1 | Already in requirements.txt | Yes | 44.0.1 | None needed — compatible with sslyze 6.3.1 |

**Missing dependencies with no fallback:** None — both sslyze and ssh-audit have specified fallbacks per CONTEXT.md.

**Missing dependencies requiring install steps:** Both sslyze and ssh-audit must be installed before Phase 1 work is testable end-to-end. The plan must include:
```bash
pip install sslyze==6.3.1 ssh-audit==3.3.0
```
And update `requirements.txt` with these pins.

---

## 9. Key Risks and Gotchas

### Risk 1: Evidence Schema Mismatch is a Silent Bug

The `_normalize_evidence()` / `_score_from_evidence()` pair in `writer.py` produces scores from Schema A. The `intelligence/scoring.py:compute_readiness_score()` expects Schema B. If you replace `_score_from_evidence()` with `compute_readiness_score()` without ALSO replacing `_normalize_evidence()` with `build_evidence_summary()`, the new scoring function will receive the wrong structure and silently return incorrect scores (it won't crash — it uses `.get()` with defaults throughout).

**Mitigation:** The task for D-10 must explicitly replace both functions together. Verify by running `tests/test_intelligence_scoring.py` — but those tests call `compute_readiness_score()` directly with Schema B data, so they won't catch a bad wiring in `writer.py`. Need an integration test or manual verification.

### Risk 2: sslyze Scanner Object is Not Thread-Safe at the `Scanner` Level

The sslyze `Scanner` object manages its own internal worker pool. Do NOT create one `Scanner` per thread in the TLS thread pool. The correct pattern for Phase 1 is: sslyze's `Scanner` handles its own concurrency internally (`per_server_concurrent_connections_limit`, `concurrent_server_scans_limit`). The outer `ThreadPoolExecutor` in `tls_scanner.py` should either:

- **Option A:** Call sslyze in the existing per-host thread (`scan_one`), creating a new `Scanner(per_server_concurrent_connections_limit=1)` per call — simple and isolated.
- **Option B:** Batch all TLS targets into a single sslyze `Scanner` call with `concurrent_server_scans_limit=cfg.scan.concurrency`, bypass the outer thread pool for the sslyze path entirely.

Option A is simpler and preserves the existing thread pool structure. Option B is more efficient. The planner should choose — both are valid.

### Risk 3: macOS sed -i Syntax

The sed rename sweep works differently on macOS vs Linux. On macOS: `sed -i ''`. On Linux: `sed -i`. The project is currently on macOS (Darwin 25.4.0). If the sweep is a shell script, it must handle both. Use Python's `pathlib` + `str.replace()` for a portable rename script instead.

### Risk 4: run_scan.py Must Be Renamed or Wrapped

D-15 says `run_scan.py` becomes the `quirk` command entry point. The file itself is named `run_scan.py` and the argparse description says `"Quantum Crypto Scanner (qcscan)"`. The plan must decide: rename the file to `quirk.py` (breaking the `python run_scan.py` invocation that existing documentation references) or keep `run_scan.py` and add a `pyproject.toml` entry point pointing to `run_scan:main`. The latter preserves backward compat; the former is cleaner. Since Phase 7 is for polish, keeping `run_scan.py` + adding the entry point is the lower-risk Phase 1 choice.

### Risk 5: `assessment/readiness_score.py` Has a Different Signature Than `intelligence/scoring.py`

The legacy function: `compute_readiness_score(cfg, endpoints, findings) → ReadinessScore`
The authoritative function: `compute_readiness_score(evidence: dict, *, weights=None) → dict`

These have completely different signatures. Any code that calls the legacy version will break if it tries to call the new one with the same arguments. The only known caller being removed is in `writer.py`. Verify no other callers exist before deleting:

```bash
grep -rn "from qcscan.assessment.readiness_score\|assessment.readiness_score" . --include="*.py" --exclude-dir=.venv
```

From the codebase read, the only import is in `writer.py` line 12. Safe to delete.

### Risk 6: `tls_version` Field Currently Misused for SSH Banners

`ssh_scanner.py` line 23 sets `ep.tls_version = banner`. Per D-06 this must stop. The `tls_version` field on SSH endpoints should be set to `None` or left unset. Any downstream code that reads `tls_version` on an SSH endpoint to get the banner string will break — but there should be no such code since it was a known MVP hack. The `ssh_audit_json` blob will contain the banner in `data["banner"]["raw"]`.

### Risk 7: Tests Import `from qcscan.*` — Must All Be Updated

All 6 test files import from `qcscan.*`. After the rename, they will all fail with `ModuleNotFoundError` until updated. The rename sed sweep must include the `tests/` directory. A verification step (`python -m pytest tests/` after rename) is required.

### Risk 8: ssh-audit Port Argument Position

The ssh-audit command takes hostname and port as positional arguments, not flags:
- Correct: `ssh-audit -j hostname 22`
- Wrong: `ssh-audit -j hostname --port 22` (this flag doesn't exist)

Always pass port as the second positional argument.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Python `unittest` (stdlib) |
| Config file | None (no pytest.ini, no pyproject.toml) |
| Quick run command | `python -m pytest tests/ -x` (if pytest installed) or `python -m unittest discover tests/` |
| Full suite command | `python -m unittest discover tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-01 | Scoring consolidation produces correct score | unit | `python -m unittest tests/test_intelligence_scoring.py` | Yes |
| CORE-01 | writer.py produces one score from one path | integration | Manual / new test | No — Wave 0 |
| CORE-02 | cert_pubkey_alg appears in output | unit | New test for `_extract_cert_key_type` | No — Wave 0 |
| CORE-03 | No qcscan references remain | smoke | `grep -r "qcscan" . --include="*.py"` returns empty | N/A (grep check) |
| CORE-04 | 100 SSH hosts scan faster than sequential | integration | Manual timing test | No |
| SCAN-01 | sslyze returns cipher suites and cert data | integration | New test with mock/real target | No — Wave 0 |
| SCAN-02 | ssh-audit JSON stored in ssh_audit_json column | integration | New test with mock ssh-audit | No — Wave 0 |

### Wave 0 Gaps

- [ ] `tests/test_writer_scoring.py` — covers CORE-01 end-to-end wiring (writer uses intelligence.scoring)
- [ ] `tests/test_cert_key_extract.py` — covers CORE-02 (confirms `cert_pubkey_alg` is read correctly)
- [ ] `tests/test_sslyze_scanner.py` — covers SCAN-01 (mock sslyze or skip if not installed)
- [ ] `tests/test_ssh_audit_scanner.py` — covers SCAN-02 (mock subprocess, verify JSON stored)

---

## Sources

### Primary (HIGH confidence)
- Live source: `/Volumes/Digs-1TB/Development/quantum-apps/QuRisk/qcscan/` — all scanner, model, and writer code read directly
- Official sslyze docs: https://nabla-c0d3.github.io/sslyze/documentation/ — API, ScanCommands, result structure
- Official ssh-audit source: https://github.com/jtesta/ssh-audit/blob/master/src/ssh_audit/ — JSON schema, error codes, command syntax

### Secondary (MEDIUM confidence)
- PyPI sslyze 6.3.1: version and dependency compatibility confirmed
- PyPI ssh-audit 3.3.0: version and GitHub alignment confirmed

---

## Metadata

**Confidence breakdown:**
- sslyze API: HIGH — official documentation verified
- ssh-audit interface: HIGH — source code and README verified
- SQLAlchemy migration: HIGH — code pattern read directly from db.py
- Package rename: HIGH — all files enumerated from source
- Thread pool pattern: HIGH — read directly from tls_scanner.py and run_scan.py
- Scoring consolidation: HIGH — all three scoring modules read in full

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (30 days — stable APIs, unlikely to change)
