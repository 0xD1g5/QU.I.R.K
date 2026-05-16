# Phase 69: Deferred BLOCKERs — Scanner + Cloud - Research

**Researched:** 2026-05-14
**Domain:** Resource leak / control-flow / schema-misuse fixes in scanner + engine subsystems
**Confidence:** HIGH

## Summary

Phase 69 closes six BLOCKER-tier audit findings deferred from the 2026-05-08 audit. All decisions
are locked in CONTEXT.md (D-01..D-10); this is **execution research**, not exploration. The
targets are small, well-localized code paths with high test coverage already in place. The
sequencing risk is low: only two of the six BLOCKERs share a file (BLOCK-03 in `k8s_connector.py`
shares no editable region with the existing K8S-03 helper). The chief surprises are:

1. **`CryptoEndpoint` has NO `finding_id` column** — D-04's `BLOB-PLATFORM` / `BLOB-UNKNOWN` /
   `BLOB-CMK` values must be encoded in `service_detail` (existing convention: `BLOB/cmk`,
   `BLOB/platform-managed`) and/or `dat_scan_json`. Adding a new column would be schema work
   out of scope for this phase. **Recommendation:** new `service_detail` values
   `BLOB/platform-managed` (unchanged for `microsoft.storage`), `BLOB/unknown` (new for
   absent/null), `BLOB/cmk` (unchanged); `dat_scan_json.finding_id` carries the dotted ID for
   programmatic consumers.
2. **`TokenBucket` has exactly one caller** (`run_scan.py:716`) and no existing tests. The D-01
   `ValueError` change cannot break any caller — `run_scan.py` always calls `acquire(1.0)`
   implicitly (no `tokens=` argument in TokenBucket usage today). New tests must be created from
   scratch.
3. **GCP Cloud SQL fix breaks 3 existing tests** (`test_gcp_cloud_sql_plaintext_allowed`,
   `_encrypted_only`, `_null_ssl_mode`) which assert `"HIGH"/"MEDIUM" in ep.cert_pubkey_alg`.
   These tests must be **rewritten** in the same wave as the BLOCK-02 source fix to assert
   `ep.severity == "HIGH"`/etc instead.
4. **`fingerprint.py` line 154 `with s:` is sufficient** for the SSH banner branch — but the
   audit (CR-08) flags that the socket from `_tcp_connect` is exposed BEFORE the `with` block
   is entered. If `_try_read_ssh_banner` raised between connection and entering the `with`,
   the socket would leak. Today `_try_read_ssh_banner` is wrapped in its own `try/except`
   returning `None`, so the leak surface is narrow but real (e.g., a `KeyboardInterrupt` between
   `_tcp_connect` returning and `with s:` being entered).
5. **`_scan_one_sslyze` does not use a context manager on `Scanner`** — sslyze 6.x `Scanner`
   does NOT expose `__enter__` / `__exit__` or `close()` in the public API. The leak is the
   internal nassl/concurrent-futures pool that sslyze itself owns. The mitigation in D-05
   ("`try/finally`") cannot directly close sslyze's pool; the pragmatic close is to bound the
   sslyze invocation in a `try/finally` that ensures `del scanner` and re-raises, allowing
   sslyze's `__del__` to release internal handles. See Pitfall 2 below.

**Primary recommendation:** Plan as **6 atomic plans**, one per BLOCKER, in **2 parallel waves**:
Wave A (BLOCK-02, BLOCK-04, BLOCK-05, BLOCK-06 — independent files) and Wave B (BLOCK-01,
BLOCK-03 — touch scanner files with downstream test assertion changes). Each plan ≤ ~25 LOC of
production code + dedicated pytest cases.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Token-bucket rate limiting | Engine (quirk/engine) | — | `run_scan.py` consumes; logic stays in engine |
| Discovery/fingerprint cache | Engine (quirk/engine) | — | I/O + TTL semantics belong in engine |
| TLS scan + sslyze pool | Scanner (quirk/scanner) | — | TLS connection lifecycle is scanner concern |
| TCP fingerprint socket | Scanner (quirk/scanner) | — | Socket lifecycle is scanner concern |
| GCP Cloud SQL severity emission | Scanner (quirk/scanner) | Models (read severity column) | Scanner produces `CryptoEndpoint`; severity column already exists |
| K8s AKS control flow guards | Scanner (quirk/scanner) | — | Existing K8S-03 invariant pattern in same file |
| Azure Blob finding differentiation | Scanner (quirk/scanner) | Intelligence (consumes `service_detail`) | `evidence.py` already keys on `BLOB/platform-managed` substring |

## User Constraints (from CONTEXT.md)

### Locked Decisions

**BLOCK-06: TokenBucket Fix**
- D-01: `acquire(tokens)` raises `ValueError` immediately when `tokens > self.capacity` (CR-07 close).
- D-02: Replace `threading.Lock` + `time.sleep(0.01)` busy-wait with `threading.Condition`. Threads block on `self._cond.wait(timeout=wait_secs)`. On token grant, call `self._cond.notify_all()`. Final shape per CONTEXT.md code snippet.
- D-03: When `rate <= 0`, return immediately before entering Condition path.

**BLOCK-04: Azure Blob**
- D-04: Same MEDIUM severity tier for both `microsoft.storage` and absent/null. Distinguished by finding_id + description: `BLOB-PLATFORM` ("Platform-managed AES-256 (Microsoft.Storage) — not customer-managed") vs `BLOB-UNKNOWN` ("Encryption key source unavailable — could not determine key management type"). `microsoft.keyvault` path unchanged (`BLOB-CMK`, no severity).

**BLOCK-01: Resource Leaks**
- D-05: `try/finally` in `_scan_one_sslyze` to ensure sslyze `Scanner` cleanup on mid-scan exception.
- D-06: Audit `fingerprint.py` line 154 `with s:` block; add explicit `try/finally` if any code path between `_tcp_connect` (line 146) and `with s:` (line 154) can raise.
- D-07: Tests use `monkeypatch` / `unittest.mock.patch` to inject exceptions and assert `.close()` called.

**BLOCK-02 / BLOCK-03 / BLOCK-05**
- D-08: GCP Cloud SQL — move SSL severity from `cert_pubkey_alg` into `severity` and `description`. Test asserts `cert_pubkey_alg` is absent/None on Cloud SQL findings.
- D-09: K8s `scan_k8s_targets` — guard `_scan_aks_encryption` against `azure_cred is None` by emitting K8S-03-conformant inaccessible finding instead. Empty `aks_clusters` returns `[]` without raising.
- D-10: `cache.py:load_cache` — `if ttl_hours <= 0: return None`. Semantics: 0 = cache disabled.

### Claude's Discretion
- Test file placement (new vs append to existing).
- Wave grouping / parallelization.
- Exact exception message text for `ValueError` (D-01) and inaccessible-finding `reason` strings (D-09).

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BLOCK-01 | TLS scanner + fingerprint resource cleanup on all exception paths | `tls_scanner.py:_scan_one_sslyze` outer `try` already exists; sslyze `Scanner` cleanup needs `try/finally` + `del scanner`. `fingerprint.py:_tcp_connect`→line 154 leak surface narrow but real |
| BLOCK-02 | GCP Cloud SQL writes severity to severity field, not `cert_pubkey_alg` | `gcp_connector.py:267` — single-line fix. Existing tests at `test_cloud_connectors.py:224-313` assert old buggy behavior; must be rewritten same plan |
| BLOCK-03 | K8s connector guards None `azure_cred`, K8S-03 invariant preserved on empty cluster list | `_emit_inaccessible_finding(provider, cluster_name, reason)` helper exists at `k8s_connector.py:327-352`. CR-02 close (Phase 29 gap) at line 460 already handles credential failure case for AKS — verify empty `aks_clusters` path emits K8S-03 finding |
| BLOCK-04 | Azure Blob distinguishes platform-managed from absent key_source | `_scan_blob_encryption` at `azure_connector.py:120-226`. `service_detail`-based finding ID convention is established (`BLOB/cmk`, `BLOB/platform-managed`); add `BLOB/unknown`. NO `finding_id` column on `CryptoEndpoint` — encode in `service_detail` + `dat_scan_json` |
| BLOCK-05 | `cache.load_cache` treats `ttl_hours <= 0` as cache-disabled | `cache.py:59-60` — single-line fix. **No callers in production code today** (verified 2026-05-14: `grep -rn 'load_cache\|cache_ttl' quirk/` returned only `cache.py` itself). The fix is an internal-API behavior change; no `--cache-ttl-hours` CLI flag exists. UAT-SERIES note describes the API contract only. |
| BLOCK-06 | TokenBucket: ValueError on `tokens > capacity`; `Condition` replaces busy-wait | `rate_limiter.py:7-32`. Only caller is `run_scan.py:716` via `TokenBucket(rate, capacity=max(1, rate))`. No `tokens=` ever passed by current callers |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | already pinned | Test runner | Established project convention |
| unittest.mock (stdlib) | 3.11+ | `MagicMock`, `patch` | Already used in `test_cloud_connectors.py`, `test_k8s_connector.py`, `test_azure_blob.py` |
| pytest's `monkeypatch` fixture | bundled | Injection of exceptions / module attribute swaps | Project pattern in `test_sslyze_integration.py` |
| `threading.Condition` (stdlib) | 3.11+ | Replaces `threading.Lock` + `time.sleep` in TokenBucket | Per D-02; pure stdlib, no new deps |

### Supporting
None — phase intentionally adds zero new dependencies.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `threading.Condition` | `queue.Queue` for fair queueing | More invasive change; D-02 locks `Condition`; rejected |
| New `finding_id` column on `CryptoEndpoint` | Encode in `service_detail` | Schema migration is out of scope; encoding in existing column matches established convention |

**Installation:** None. Phase adds zero new pip dependencies.

## Architecture Patterns

### System Architecture Diagram

```
                     ┌────────────────────────────────────────────┐
                     │            run_scan.py (CLI entry)         │
                     └──┬───────────────┬──────────────┬──────────┘
                        │               │              │
              ┌─────────▼────┐  ┌───────▼──────┐  ┌────▼──────────────┐
              │ TokenBucket  │  │ load_cache /  │  │ scan_*_targets()  │
              │ (BLOCK-06)   │  │ save_cache    │  │ dispatchers       │
              │ engine/      │  │ (BLOCK-05)    │  │ scanner/*.py      │
              └──────────────┘  │ engine/cache  │  └────┬──────┬───────┘
                                └───────────────┘       │      │
                          ┌────────────────────────────┘      │
                          │                                    │
            ┌─────────────▼─────────┐    ┌────────────────────▼────────┐
            │ tls_scanner / fingerprint │  │ gcp_connector / k8s_connector │
            │ (BLOCK-01)                │  │ azure_connector               │
            │ - sslyze Scanner          │  │ (BLOCK-02, BLOCK-03, BLOCK-04)│
            │ - socket via _tcp_connect │  │ → CryptoEndpoint(severity,    │
            │   → must close on raise   │  │     service_detail, dat_json) │
            └───────────────────────────┘  └───────────────────────────────┘
                          │                              │
                          └──────────┬───────────────────┘
                                     ▼
                            CryptoEndpoint rows → SQLite
                            (severity column exists; finding_id column does NOT)
```

### Recommended Project Structure (no new files needed; this lists the touched + new test files)
```
quirk/
├── engine/
│   ├── rate_limiter.py        # BLOCK-06 — rewrite TokenBucket.acquire (~25 LOC)
│   └── cache.py               # BLOCK-05 — invert ttl_hours <= 0 branch (1 line)
└── scanner/
    ├── tls_scanner.py         # BLOCK-01 — try/finally around sslyze Scanner (~10 LOC)
    ├── fingerprint.py         # BLOCK-01 — explicit close around _try_read_ssh_banner (~5 LOC)
    ├── gcp_connector.py       # BLOCK-02 — move severity to severity field (~3 LOC)
    ├── k8s_connector.py       # BLOCK-03 — guard against None cred path (already partly done; verify CR-09 empty list edge) (~10 LOC)
    └── azure_connector.py     # BLOCK-04 — three-way branch on key_source + finding_id encoding (~15 LOC)

tests/
├── test_rate_limiter.py       # NEW — BLOCK-06 unit tests (capacity guard, Condition wakeup)
├── test_cache.py          # NEW — BLOCK-05 unit tests (ttl_hours=0 → None even on fresh file)
├── test_tls_scanner_resource_cleanup.py  # NEW — BLOCK-01 sslyze leak test
├── test_fingerprint_socket_cleanup.py    # NEW — BLOCK-01 socket leak test
├── test_cloud_connectors.py   # MODIFY — rewrite 3 Cloud SQL assertions for BLOCK-02
├── test_k8s_connector.py      # APPEND — BLOCK-03 None-cred + empty-list cases
└── test_azure_blob.py         # MODIFY — assert new BLOB-UNKNOWN finding_id for absent key_source
```

### Pattern 1: Existing K8S-03 inaccessible finding helper
**What:** `_emit_inaccessible_finding(provider, cluster_name, reason, session_start)` returns a `CryptoEndpoint` with `scan_error="encryption-config-inaccessible"`, `service_detail=reason`, `protocol="KUBERNETES"`.
**When to use:** BLOCK-03 None-cred / empty-cluster guard must call this helper, NOT raise.
**Example:**
```python
# Source: quirk/scanner/k8s_connector.py:327-352 (existing)
def _emit_inaccessible_finding(provider, cluster_name, reason, session_start=None):
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    return CryptoEndpoint(
        host=f"k8s://{cluster_name or provider or 'unknown'}",
        port=0,
        protocol="KUBERNETES",
        scan_error="encryption-config-inaccessible",
        service_detail=reason,
        scanned_at=now,
    )
```

### Pattern 2: Test fixture for Azure connector with `MagicMock` accounts
**What:** `_make_account(name, key_source, ...)` builds `MagicMock` storage accounts with controllable `encryption.key_source`.
**When to use:** BLOCK-04 tests must extend this pattern for the new `BLOB-UNKNOWN` case.
**Example:**
```python
# Source: tests/test_azure_blob.py:9-24 (existing)
def _make_account(name: str, key_source, rg: str = "myrg", containers=("default",)):
    account = MagicMock()
    account.name = name
    account.id = f"/subscriptions/sub-1/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{name}"
    if key_source is None:
        account.encryption = None
    else:
        enc = MagicMock()
        enc.key_source = key_source
        account.encryption = enc
    return account
```

### Pattern 3: TokenBucket with `threading.Condition` (per D-02)
**What:** Replace lock+sleep busy-wait with `Condition.wait(timeout)` + `notify_all()`.
**When to use:** Exact final shape for BLOCK-06.
**Example:** See CONTEXT.md D-02 code block (paste verbatim into `rate_limiter.py`).

### Anti-Patterns to Avoid
- **Adding a `finding_id` column to `CryptoEndpoint`** — schema change out of scope; encode in `service_detail` per existing convention.
- **Using `threading.Lock` AND `threading.Condition` separately** — `Condition` already wraps a lock; do not introduce both.
- **Using `time.sleep` anywhere in the new TokenBucket path** — defeats the purpose of D-02.
- **Closing the sslyze `Scanner` via context manager** — sslyze 6.x does not expose `__enter__` / `__exit__`. Use `try/finally` + `del scanner`.
- **Calling `_scan_aks_encryption(credential=None, ...)`** — D-09 forbids; emit inaccessible finding first.
- **Removing `cert_pubkey_alg` assertion** from existing Cloud SQL tests without replacing with `severity` assertion — would silently weaken coverage.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fair queueing for token bucket | Custom FIFO queue, `queue.Queue` wrapper | `threading.Condition` + `notify_all()` per D-02 | Stdlib idiom; deterministic; no new deps |
| sslyze Scanner cleanup | Wrapper class around `Scanner` | `try/finally: del scanner` | sslyze owns its internal pool; `del` triggers `__del__` |
| K8s inaccessible finding | Build new dict | Reuse `_emit_inaccessible_finding()` | Already conformant to K8S-03 invariant |
| Mock storage accounts | Hand-write classes | Reuse `_make_account` from `tests/test_azure_blob.py` | Established test pattern |

**Key insight:** All six BLOCKERs are surgical fixes — there is no general-purpose abstraction to introduce. The risk is **changing too much**, not too little.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 69 makes no schema change. Existing `CryptoEndpoint` rows in user databases that have severity in `cert_pubkey_alg` (CLOUD_SQL protocol) will remain in historical scan tables, but new scans will write to `severity` correctly. **No data migration needed**: historical CBOM rows are immutable per scan-session model. | Code edit only |
| Live service config | None — no external services hold state for these subsystems. | None |
| OS-registered state | None | None |
| Secrets/env vars | None — no env var names are renamed; `args.cache_ttl_hours` and `args.rate_limit` CLI flag names are unchanged. | None |
| Build artifacts | None — pure code edit, no package metadata change. `python -m compileall` verifies. | None |

## Common Pitfalls

### Pitfall 1: Existing `test_gcp_cloud_sql_*` tests assert the bug
**What goes wrong:** BLOCK-02 source fix breaks 3 existing tests in `tests/test_cloud_connectors.py` (lines 224, 247, 292) that assert `"HIGH" in (ep.cert_pubkey_alg or "")`.
**Why it happens:** Original tests were written against the buggy code path.
**How to avoid:** Same plan/wave that edits `gcp_connector.py:_scan_cloud_sql` MUST rewrite these three tests to assert `ep.severity == "HIGH"` / `"MEDIUM"` and `ep.cert_pubkey_alg in (None, "")`. Add a 4th test asserting CBOM/classifier consumers don't see severity strings as algorithm names.
**Warning signs:** `pytest tests/test_cloud_connectors.py -k cloud_sql` fails after edit.

### Pitfall 2: sslyze `Scanner` has no `close()` / context manager
**What goes wrong:** D-05 says "use `try/finally` to clean up sslyze Scanner". sslyze 6.x does NOT expose `Scanner.__enter__` / `__exit__` / `close()`. Naive `with SslyzeScanner(...) as s:` raises `AttributeError`.
**Why it happens:** sslyze owns an internal `nassl` thread/process pool that is released when the `Scanner` object is garbage-collected (`__del__`).
**How to avoid:** Use `try/finally: del scanner` to force ref-drop:
```python
scanner = SslyzeScanner(per_server_concurrent_connections_limit=2)
try:
    scanner.queue_scans([scan_request])
    results = list(scanner.get_results())
    # ... process results ...
finally:
    try:
        del scanner
    except Exception:
        pass
```
Verify with a test that mocks `SslyzeScanner` to raise inside `get_results()` and asserts the mock's `__del__` (or a tracking attribute) was hit.
**Warning signs:** AttributeError when running `_scan_one_sslyze` against any target.

### Pitfall 3: `_scan_aks_encryption` already partially handles None credential at line 456
**What goes wrong:** k8s_connector.py:456 already has a `credential = None` branch that emits inaccessible findings. BLOCK-03 risk is duplicating or misaligning that logic.
**Why it happens:** CR-02 (Phase 29 gap closure, line 460 comment) added partial handling but only for `aks_clusters` not empty.
**How to avoid:** Read lines 452-499 carefully. The CR-09 case (empty `aks_clusters` with valid credential silently produces `[]`) is the new path to fix. The CR-03 case (None cred) already has a path — verify it covers `aks_clusters=None` AND `aks_clusters=[]` AND `cluster_name=None`. The K8S-03 final safety net at line 527 catches the absolute-empty case but not the per-cluster-list-empty case.
**Warning signs:** `test_k8s_connector.py::test_aks_credential_failure_*` already passes; new test should target the `credential is not None AND aks_clusters == []` path.

### Pitfall 4: `fingerprint.py` `_tcp_connect` leak window is narrow
**What goes wrong:** D-06 says "verify line 154 `with s:` covers all paths". Line 146-152 is the `_tcp_connect` call wrapped in try/except for socket.timeout/ConnectionRefusedError/OSError. Between line 146 (`s = _tcp_connect(...)`) returning and line 154 (`with s:`) being entered, no code runs except the implicit pass-through. The leak surface is `KeyboardInterrupt` / `SystemExit` between the two statements, plus any future code that gets inserted between them.
**Why it happens:** Python guarantees nothing about asynchronous interruption between bytecode opcodes.
**How to avoid:** Wrap the entire span in `try/finally`:
```python
try:
    s = _tcp_connect(host, port, timeout)
except socket.timeout:
    return Fingerprint(False, "CLOSED", "TIMEOUT")
except ConnectionRefusedError:
    return Fingerprint(False, "CLOSED", "REFUSED")
except OSError:
    return Fingerprint(False, "CLOSED", "UNREACHABLE")

try:
    with s:
        banner = _try_read_ssh_banner(s)
        if banner:
            return Fingerprint(True, "SSH", banner)
except BaseException:
    try:
        s.close()
    except Exception:
        pass
    raise
```
The added `try/except BaseException` ensures `KeyboardInterrupt` between line 153 and `with s:` still closes the socket.
**Warning signs:** Test injecting `KeyboardInterrupt` via mocked `_try_read_ssh_banner` shows socket leaked.

### Pitfall 5: `cache.py:load_cache` API contract change (no current callers)
**What goes wrong:** D-10 inverts the `ttl_hours <= 0` branch. **CORRECTION (2026-05-14):** initial research speculated `run_scan.py:749, 800` callers existed. Verified: `grep -rn 'load_cache\|cache_ttl' quirk/` returns ONLY `cache.py` itself — there are zero production callers and no `--cache-ttl-hours` CLI flag. The fix is an internal-API contract change preempting future-caller misuse.
**Why it happens:** D-10 explicitly inverts semantics. The prior behavior (`return obj` on `ttl_hours <= 0`) was a bug.
**How to avoid:** Document in `docs/UAT-SERIES.md` (post-phase step 2) that `load_cache(ttl_hours=0)` now returns `None` (was: returned cached object). Frame as an API contract note for future callers, not a CLI behavior change.
**Warning signs:** Future caller wires `load_cache` with `ttl_hours=0` expecting "cache forever" — they will get cache miss every call. UAT-SERIES note pre-flags this.

### Pitfall 6: `BLOB-CMK` / `BLOB-PLATFORM` / `BLOB-UNKNOWN` are NOT column values
**What goes wrong:** CONTEXT.md D-04 says "finding_id `BLOB-PLATFORM`". `CryptoEndpoint` has no `finding_id` column. Naive `CryptoEndpoint(finding_id=...)` raises TypeError or silently drops the kwarg.
**Why it happens:** Schema mismatch between CONTEXT.md vocabulary and SQLAlchemy model.
**How to avoid:** Encode finding ID in TWO places:
1. `service_detail` — keeps existing convention (`BLOB/cmk` already in production). Map: `BLOB-CMK` → `service_detail="BLOB/cmk"`, `BLOB-PLATFORM` → `service_detail="BLOB/platform-managed"` (unchanged), `BLOB-UNKNOWN` → `service_detail="BLOB/unknown"` (NEW).
2. `dat_scan_json["finding_id"]` — for programmatic consumers (CBOM intelligence layer).
Verify `quirk/intelligence/evidence.py:204` substring match (`"BLOB/platform-managed" in sd`) does NOT trigger on `"BLOB/unknown"` — confirmed by inspection (no overlap).
**Warning signs:** `test_dar_storage_scoring.py` failures (the only test asserting `BLOB/platform-managed` in scoring) — should NOT be affected by this change since the platform-managed value string is unchanged.

### Pitfall 7: `del scanner` does not deterministically free in CPython if there are unreachable refs
**What goes wrong:** sslyze internally captures `self` in its `concurrent.futures` callbacks. `del scanner` only drops the outer reference; if internal threads still hold a back-reference, GC delay until generation collection.
**Why it happens:** CPython's reference-counting GC handles cycles only via the cyclic GC pass.
**How to avoid:** Force a GC pass after `del`: `import gc; gc.collect()` inside the `finally` block. This is heavy-handed but deterministic. Acceptable here because `_scan_one_sslyze` is per-target (not per-thread tight loop).
**Warning signs:** Long-running scans show socket-handle climb in `lsof` despite `try/finally`.

## Code Examples

### TokenBucket with Condition (final shape per D-02)
```python
# Source: CONTEXT.md D-02 (verbatim)
def acquire(self, tokens: float = 1.0):
    if self.rate <= 0:
        return  # unlimited — skip Condition entirely
    if tokens > self.capacity:
        raise ValueError(f"tokens {tokens} > capacity {self.capacity}")
    with self._cond:
        while True:
            now = time.perf_counter()
            elapsed = now - self.updated
            self.updated = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            if self.tokens >= tokens:
                self.tokens -= tokens
                self._cond.notify_all()
                return
            wait_secs = (tokens - self.tokens) / self.rate
            self._cond.wait(timeout=wait_secs)
```
Constructor change: `self._cond = threading.Condition()` replaces `self.lock = threading.Lock()`.

### GCP Cloud SQL severity fix (BLOCK-02)
```python
# Source: derived from quirk/scanner/gcp_connector.py:262-274 (current buggy)
# AFTER fix:
ep = CryptoEndpoint(
    host=f"gcp://{project_id}/sql/{instance_name}",
    port=0,
    protocol="CLOUD_SQL",
    severity=severity,                        # NEW: severity goes to severity column
    service_detail=f"CLOUD_SQL/{description.replace(' ', '-')}",  # description in service_detail
    cloud_scan_json=json.dumps(
        {"sslMode": ssl_mode, "finding": description},
        default=str,
    ),
)
# Note: cert_pubkey_alg is NOT set — Cloud SQL TLS enforcement is not a public-key algorithm finding.
```

### Azure Blob three-way branch (BLOCK-04)
```python
# Source: derived from quirk/scanner/azure_connector.py:171-179 (current two-way)
# AFTER fix:
if key_source == "microsoft.keyvault":
    service_detail = "BLOB/cmk"
    finding_id = "BLOB-CMK"
    description = "Customer-managed key (Azure Key Vault)"
    severity = None
elif key_source == "microsoft.storage":
    service_detail = "BLOB/platform-managed"
    finding_id = "BLOB-PLATFORM"
    description = "Platform-managed AES-256 (Microsoft.Storage) — not customer-managed"
    severity = "MEDIUM"
else:
    # absent / null / empty / unrecognized → distinct unknown state
    service_detail = "BLOB/unknown"
    finding_id = "BLOB-UNKNOWN"
    description = "Encryption key source unavailable — could not determine key management type"
    severity = "MEDIUM"

# dat_scan_json carries finding_id + description for programmatic consumers
ep = CryptoEndpoint(
    host=container_id,
    port=0,
    protocol="AZURE_BLOB",
    service_detail=service_detail,
    dat_scan_json=json.dumps({
        "account": account_name,
        "container": container_name,
        "key_source": key_source_raw or "absent",
        "finding_id": finding_id,
        "description": description,
    }, default=str),
    scanned_at=ts,
)
if severity:
    ep.severity = severity
```

### K8s None-credential guard (BLOCK-03)
The fix is largely already present (k8s_connector.py:454-491). Verify the **CR-09 empty-list case** is closed:
```python
# AFTER credential succeeds (line 492 onwards), add guard:
if credential is not None:
    if not (aks_clusters or []):
        # CR-09: empty cluster list with valid credential — emit K8S-03 finding
        results.append(_emit_inaccessible_finding(
            provider="aks",
            cluster_name=cluster_name or "aks",
            reason="aks_clusters list is empty — no clusters configured for AKS scan",
            session_start=session_start,
        ))
    else:
        results.extend(_scan_aks_encryption(
            credential=credential,
            subscription_id=azure_subscription_id or "",
            cluster_configs=aks_clusters,
            logger=logger,
            session_start=session_start,
        ))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `threading.Lock` + `time.sleep(0.01)` busy-wait | `threading.Condition.wait(timeout)` + `notify_all` | Phase 69 (this) | No more thundering herd, no starvation, deterministic latency |
| Severity stuffed in `cert_pubkey_alg` | `severity` column + `service_detail` description | Phase 69 (this) | CBOM classifier no longer treats "HIGH" as an algorithm name |
| `service_detail` only conveys finding type | `service_detail` + `dat_scan_json["finding_id"]` for programmatic consumers | Phase 69 (this) | Adds programmatic distinguishability without schema change |

**Deprecated/outdated:** None — fixes preserve all existing extension points.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | sslyze 6.x `Scanner` exposes no `close()` or context manager | Pitfall 2 | If sslyze added one in a recent release, `del scanner` is unnecessary but harmless. **[ASSUMED]** based on training data; verify via `python -c "from sslyze import Scanner; print(dir(Scanner))"` before implementation. |
| A2 | `_scan_aks_encryption(cluster_configs=[])` returns `[]` silently (root cause of CR-09) | Pitfall 3 | Re-read k8s_connector.py:212 — if existing code raises on empty list, the fix shape changes. **[VERIFIED: source read]** — `for cfg in cluster_configs or []:` does iterate-zero-times silently. |
| A3 | `evidence.py:204` substring match `"BLOB/platform-managed" in sd` is the only consumer keying on the literal string | Pitfall 6 | If another module checks the exact value, BLOCK-04 might break it. **[VERIFIED: grep]** — only hit is `evidence.py:204` plus tests. |
| A4 | `gc.collect()` in `_scan_one_sslyze` finally block has acceptable performance | Pitfall 7 | If TLS scans are tight-looped (high target count), gc.collect() per target could measurably slow scans. **[ASSUMED]** — for typical 10-1000 target scans with timeout=10s, gc cost is negligible. |
| A5 | ~~`args.cache_ttl_hours` CLI default~~ — N/A | Pitfall 5 | **[VERIFIED 2026-05-14]** No `--cache-ttl-hours` CLI flag exists; `load_cache` has zero callers. D-10 has zero current end-user impact; the fix is an internal-API contract change. |

## Open Questions (RESOLVED 2026-05-14)

1. **Should we add `severity` to GCP Cloud SQL findings as `"HIGH"` for ALLOW_UNENCRYPTED_AND_ENCRYPTED but use `description` for the finding text?**
   - **RESOLVED:** Plan 02 encodes severity in the `severity` column and finding text in `service_detail` (`CLOUD_SQL/<description>` convention) + `cloud_scan_json["finding"]`. `CryptoEndpoint` has no `description` column.

2. **`--cache-ttl-hours` argparse default value** — needed for UAT-SERIES.md wording.
   - **RESOLVED:** No `--cache-ttl-hours` CLI flag exists. `grep -rn 'cache_ttl\|ttl_hours' quirk/` (2026-05-14) returned only `quirk/engine/cache.py` itself — `load_cache` has zero callers in the production code path. The fix is an internal-API behavior change only; no end-user CLI default to migrate. Plan 05 UAT-SERIES note can describe `load_cache(ttl_hours=0)` semantics ("0 means cache disabled — never returns a hit") without referencing a user-facing flag.

3. **Should existing `test_gcp_cloud_sql_*` tests be deleted-and-replaced or modified in place?**
   - **RESOLVED:** Plan 02 modifies in place (preserves test name + git blame); assertion lines only.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already configured per `tests/conftest.py`) |
| Config file | `pyproject.toml` (project standard) |
| Quick run command | `pytest tests/test_rate_limiter.py tests/test_cache.py tests/test_azure_blob.py tests/test_cloud_connectors.py::test_gcp_cloud_sql_plaintext_allowed -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BLOCK-01 | sslyze Scanner cleanup on mid-scan exception | unit | `pytest tests/test_tls_scanner_resource_cleanup.py -x` | ❌ Wave 0 |
| BLOCK-01 | fingerprint socket closes on `_try_read_ssh_banner` raise | unit | `pytest tests/test_fingerprint_socket_cleanup.py -x` | ❌ Wave 0 |
| BLOCK-02 | Cloud SQL severity in `severity` column, not `cert_pubkey_alg` | unit | `pytest tests/test_cloud_connectors.py -k cloud_sql -x` | ✅ (modify) |
| BLOCK-03 | K8s scan_k8s_targets with `azure_cred=None` emits inaccessible finding | unit | `pytest tests/test_k8s_connector.py::test_aks_credential_failure_emits_inaccessible_per_cluster -x` | ✅ (append empty-list case) |
| BLOCK-03 | K8s scan_k8s_targets with empty `aks_clusters` + valid cred emits K8S-03 finding | unit | `pytest tests/test_k8s_connector.py::test_aks_empty_cluster_list_emits_inaccessible -x` | ❌ Wave 0 |
| BLOCK-04 | Azure Blob `service_detail="BLOB/unknown"` for absent key_source | unit | `pytest tests/test_azure_blob.py::test_azure_blob_absent_key_source_unknown -x` | ❌ Wave 0 (rename of existing _absent_key_source_medium) |
| BLOCK-04 | Azure Blob `dat_scan_json["finding_id"]` carries BLOB-PLATFORM/UNKNOWN/CMK | unit | `pytest tests/test_azure_blob.py::test_azure_blob_finding_id_in_dat_scan_json -x` | ❌ Wave 0 |
| BLOCK-05 | `load_cache(dir, key, ttl_hours=0)` returns None even on fresh file | unit | `pytest tests/test_cache.py::test_ttl_zero_returns_none_on_fresh_file -x` | ❌ Wave 0 |
| BLOCK-06 | `TokenBucket.acquire(tokens > capacity)` raises ValueError | unit | `pytest tests/test_rate_limiter.py::test_acquire_raises_when_tokens_exceed_capacity -x` | ❌ Wave 0 |
| BLOCK-06 | `TokenBucket.acquire` uses Condition (no busy-wait) under contention | unit | `pytest tests/test_rate_limiter.py::test_acquire_blocks_via_condition_no_busy_wait -x` | ❌ Wave 0 |
| BLOCK-06 | `TokenBucket(rate=0).acquire()` returns immediately | unit | `pytest tests/test_rate_limiter.py::test_unlimited_rate_fast_path -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Per-BLOCKER quick run command above.
- **Per wave merge:** `pytest tests/test_rate_limiter.py tests/test_cache.py tests/test_tls_scanner_resource_cleanup.py tests/test_fingerprint_socket_cleanup.py tests/test_cloud_connectors.py tests/test_k8s_connector.py tests/test_azure_blob.py -x` plus `python -m compileall quirk/`.
- **Phase gate:** Full suite green before `/gsd-verify-work`: `pytest tests/ -x`.

### Wave 0 Gaps
- [ ] `tests/test_rate_limiter.py` — covers BLOCK-06 (3 tests: capacity guard, Condition wakeup, rate=0 fast path)
- [ ] `tests/test_cache.py` — covers BLOCK-05 (ttl=0 → None on fresh file; ttl>0 honored)
- [ ] `tests/test_tls_scanner_resource_cleanup.py` — covers BLOCK-01 sslyze leak (mock `Scanner` to raise inside `get_results()`, assert cleanup)
- [ ] `tests/test_fingerprint_socket_cleanup.py` — covers BLOCK-01 socket leak (mock `_try_read_ssh_banner` to raise; assert socket `.close()` called)
- [ ] No new conftest fixtures needed — reuse `MagicMock`, `monkeypatch` patterns already established
- [ ] Framework install: none — pytest already installed

## Project Constraints (from CLAUDE.md)

The following CLAUDE.md directives are **mandatory** for every plan in this phase and must be reflected in plan acceptance criteria:

1. **PEP 8 compliance** — every code change must pass project lint conventions.
2. **Minimal diffs** — avoid unnecessary refactors. Each BLOCKER fix should be the smallest viable change to make the test pass.
3. **`python -m compileall`** must pass post-edit.
4. **Run relevant tests** — quick run commands listed in Validation Architecture.
5. **Mandatory phase completion steps:**
   - Create Obsidian phase note at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-69-Deferred-BLOCKERs-Scanner-Cloud.md`
   - Update `docs/UAT-SERIES.md` (esp. cache TTL=0 behavior change for BLOCK-05; Cloud SQL severity rendering for BLOCK-02)
   - Sync UAT-SERIES.md to Obsidian
   - Commit `docs/UAT-SERIES.md`
6. **AUDIT-TASKS.md ledger update** — flip rows for `scanners-protocol/CR-07, CR-08` and `scanners-cloud/CR-02, CR-03, CR-06, CR-07, CR-08, CR-09, CR-10` from `[ ] deferred-v4.9` to `[x] closed — closed by Phase 69 (BLOCK-XX)`.

## Sources

### Primary (HIGH confidence)
- `quirk/engine/rate_limiter.py` — Read in full; verified TokenBucket has 1 caller (`run_scan.py:716`)
- `quirk/engine/cache.py` — Read in full. **CORRECTION (2026-05-14):** initial pass speculated 2 call sites in `run_scan.py:749, 800`; verified false — `grep -rn 'load_cache\|cache_ttl' quirk/` returns only `cache.py` itself. Zero production callers; no `--cache-ttl-hours` CLI flag.
- `quirk/scanner/tls_scanner.py` — Read in full; `_scan_one_sslyze` outer try/except already exists; sslyze `Scanner` lifecycle confirmed
- `quirk/scanner/fingerprint.py` — Read in full; `_tcp_connect` → `with s:` window verified
- `quirk/scanner/gcp_connector.py` — Read in full; `_scan_cloud_sql` line 267 confirmed buggy
- `quirk/scanner/k8s_connector.py` — Read in full; `_emit_inaccessible_finding` helper confirmed; CR-02 partial fix at line 460 verified
- `quirk/scanner/azure_connector.py` — Read in full; `_scan_blob_encryption` two-way branch at line 173 confirmed
- `quirk/models.py` — Read; confirmed `severity` column exists, `finding_id` column does NOT
- `tests/test_cloud_connectors.py:224-313` — Confirmed existing tests assert buggy behavior (will need rewrite)
- `tests/test_azure_blob.py` — Read in full; `_make_account` fixture pattern confirmed
- `tests/test_k8s_connector.py` — Test list verified; `test_aks_credential_failure_*` exist
- `.planning/audit-2026-05-08/scanners-cloud/REVIEW.md` — All 6 cloud BLOCKER details read
- `.planning/audit-2026-05-08/scanners-protocol/REVIEW.md` — CR-07, CR-08 protocol BLOCKER details read
- `.planning/REQUIREMENTS.md` — BLOCK-01..BLOCK-06 acceptance criteria confirmed

### Secondary (MEDIUM confidence)
- `quirk/intelligence/evidence.py:204` — Substring match on `BLOB/platform-managed` (only downstream consumer found via grep)
- `tests/test_dar_storage_scoring.py` — Uses `BLOB/platform-managed` literal in scoring tests (unaffected by BLOCK-04 since string unchanged)

### Tertiary (LOW confidence / [ASSUMED])
- sslyze 6.x lacks `Scanner.__exit__` / `close()` — based on training data; verify with `dir(SslyzeScanner)` before implementation (Assumption A1).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pure stdlib (`threading.Condition`), no new deps
- Architecture: HIGH — every targeted module + helper read in source
- Pitfalls: HIGH — Pitfalls 1, 2, 6 backed by grep + source read; Pitfalls 4, 7 reasoned from CPython semantics

**Research date:** 2026-05-14
**Valid until:** 2026-06-13 (30 days; stable subsystem, no fast-moving deps)

## RESEARCH COMPLETE

**Phase:** 69 — Deferred BLOCKERs — Scanner + Cloud
**Confidence:** HIGH

### Key Findings
- All six BLOCKERs are surgical, locally-scoped fixes (≤25 LOC each); zero new dependencies needed.
- `CryptoEndpoint` has NO `finding_id` column — D-04 IDs encode in `service_detail` (existing convention) + `dat_scan_json["finding_id"]`.
- BLOCK-02 fix breaks 3 existing `test_gcp_cloud_sql_*` tests that assert the bug; same plan must rewrite assertions to use `ep.severity`.
- TokenBucket has one caller (`run_scan.py:716`) which never passes `tokens > capacity` — D-01 ValueError is safe.
- sslyze 6.x `Scanner` likely lacks `__exit__`/`close()`; D-05 mitigation must use `try/finally: del scanner` + optional `gc.collect()` (Assumption A1 — verify).
- `fingerprint.py` line 154 leak window is narrow; explicit `try/finally` around line 154 closes the gap deterministically.

### File Created
`.planning/phases/69-deferred-blockers-scanner-cloud/69-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | All stdlib; no version risk |
| Architecture | HIGH | Every targeted source file read end-to-end |
| Pitfalls | HIGH | All 7 pitfalls grounded in source inspection or grep evidence (Pitfall 7 reasoned from CPython GC semantics) |

### Open Questions
- Verify sslyze `Scanner` API surface (Assumption A1) before BLOCK-01 plan execution — `python -c "from sslyze import Scanner; print([m for m in dir(Scanner) if not m.startswith('_')])"`.
- ~~Confirm `--cache-ttl-hours` default in `run_scan.py` argparse~~ — RESOLVED 2026-05-14: no such CLI flag exists; `load_cache` has zero callers (see Q2 RESOLVED above and Pitfall 5 CORRECTION).
- Decide whether existing `test_gcp_cloud_sql_*` tests are modified in place (recommended) or replaced.

### Ready for Planning
Research complete. Recommended planning shape: 6 plans, 2 waves (Wave A: BLOCK-02/04/05/06 parallel; Wave B: BLOCK-01/03 parallel after Wave A green). Each plan ≤ ~25 LOC production + dedicated pytest cases.
