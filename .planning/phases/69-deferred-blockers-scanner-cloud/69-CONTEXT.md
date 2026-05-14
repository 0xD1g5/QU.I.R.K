# Phase 69: Deferred BLOCKERs — Scanner + Cloud - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 69 closes the six deferred BLOCKER-severity audit findings in the scanner and cloud subsystems:

- **BLOCK-01** (CR-07, CR-08): Resource leaks — sslyze nested ThreadPool and fingerprint socket not closed on all exception paths
- **BLOCK-02** (CR-02): GCP Cloud SQL writes SSL severity into `cert_pubkey_alg` (wrong field)
- **BLOCK-03** (CR-03, CR-09): K8s connector calls `_scan_aks_encryption` with `azure_cred=None` (AttributeError); empty target list violates K8S-03 invariant
- **BLOCK-04** (CR-10): Azure Blob conflates `microsoft.storage` (known platform-managed) with absent/null `key_source` (unknown state) — same finding dict output for semantically different states
- **BLOCK-05** (CR-06): `cache.py` `load_cache` returns cache hit when `ttl_hours <= 0` instead of bypassing cache
- **BLOCK-06** (CR-07, CR-08): `TokenBucket.acquire(n > capacity)` loops forever; sleep+busy-wait contention replaced with proper threading.Condition

**In scope:** The six code fixes listed above, pytest tests asserting correct behavior, no schema changes, no new scan capabilities.

**Out of scope:** WARNING-tier audit findings (Phase 71/72), QRAMM/API BLOCKERs (Phase 70), chaos lab changes, dashboard UI changes.

</domain>

<decisions>
## Implementation Decisions

### BLOCK-06: TokenBucket Fix (engine/rate_limiter.py)

- **D-01: Capacity guard** — `acquire(tokens)` raises `ValueError` immediately when `tokens > self.capacity`. No infinite loop. This closes CR-07.

- **D-02: Contention fix via threading.Condition** — Replace `self.lock = threading.Lock()` and the `time.sleep(0.01)` busy-wait loop with `self._cond = threading.Condition()`. Threads block with `self._cond.wait(timeout=wait_secs)` instead of spinning. On successful token grant, call `self._cond.notify_all()`. This closes CR-08.

  Final `acquire` shape:
  ```python
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

- **D-03: rate <= 0 fast path** — When `rate <= 0` (unlimited), return immediately before entering the Condition path. Zero overhead for unlimited callers.

### BLOCK-04: Azure Blob Absent Key Source (azure_connector.py)

- **D-04: Same severity tier, distinct finding_id and description** — Both `microsoft.storage` and absent/null `key_source` remain MEDIUM severity. They are distinguished by finding_id and description:
  - `microsoft.storage` → finding_id `BLOB-PLATFORM`, description `"Platform-managed AES-256 (Microsoft.Storage) — not customer-managed"`
  - absent/null/empty → finding_id `BLOB-UNKNOWN`, description `"Encryption key source unavailable — could not determine key management type"`
  - `microsoft.keyvault` path unchanged (finding_id `BLOB-CMK` or equivalent, SAFE/None severity)

### BLOCK-01: Resource Leak Fix Strategy (tls_scanner.py, fingerprint.py)

- **D-05: try/finally in _scan_one_sslyze** — The outer `scan_tls_targets` `ThreadPoolExecutor` already uses `with ex:` (calls `shutdown(wait=True)` on exit — handles the outer pool). The fix targets `_scan_one_sslyze`: ensure sslyze's `Scanner` object is cleaned up in a `try/finally` block if sslyze raises mid-scan. Do not rely on sslyze's context manager interface.

- **D-06: fingerprint.py socket close** — Ensure the socket opened in `_tcp_connect` at line 146 is closed on all exception paths from `_try_read_ssh_banner`. The `with s:` block on line 154 handles normal and exception exit from the SSH banner check — verify this covers all paths; if not, add explicit `try/finally`.

### BLOCK-01: Resource Leak Test Fixtures

- **D-07: monkeypatch/mock injection** — Tests use `monkeypatch` / `unittest.mock.patch` to inject exceptions at specific points (e.g., patch `socket.create_connection` to return a `MagicMock` whose `close()` is trackable, then raise inside `_try_read_ssh_banner`). Assert `.close()` was called. Fast, no network, consistent with existing test patterns in `tests/`.

### BLOCK-02 / BLOCK-03 / BLOCK-05: Clear-Cut Fixes

- **D-08: GCP Cloud SQL** — Move SSL enforcement status out of `cert_pubkey_alg` into `severity` and `description` fields. Test asserts `cert_pubkey_alg` is absent from Cloud SQL finding dict (or equals `None`/empty).

- **D-09: K8s None guard** — In `scan_k8s_targets`, guard `_scan_aks_encryption` call: if `azure_cred is None`, emit a K8S-03-conformant inaccessible finding instead of calling `_scan_aks_encryption`. Empty `aks_clusters` list returns `[]` without raising (the K8S-03 "at least one finding" invariant applies at the per-provider level, not for an empty cluster list).

- **D-10: Cache TTL bypass** — In `cache.py:load_cache`, change `if ttl_hours <= 0: return obj` → `if ttl_hours <= 0: return None`. Semantics: `ttl_hours=0` means "cache disabled" (never return cached data). Test: `load_cache(dir, key, ttl_hours=0)` returns `None` even when a fresh cache file exists.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Audit Findings (authoritative source for all six BLOCKERs)
- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — Full audit ledger; rows `scanners-protocol/CR-07, CR-08` and `scanners-cloud/CR-02, CR-03, CR-06, CR-07, CR-08, CR-09, CR-10` are the six BLOCKERs in scope
- `.planning/audit-2026-05-08/scanners-protocol/` — Protocol scanner finding details (CR-07, CR-08 rationale)
- `.planning/audit-2026-05-08/scanners-cloud/` — Cloud scanner finding details (CR-02, CR-03, CR-06..CR-10 rationale)

### Requirements
- `.planning/REQUIREMENTS.md` §BLOCK-01..BLOCK-06 — Requirement text and acceptance criteria

### Source Files (all need to be read before planning)
- `quirk/engine/rate_limiter.py` — TokenBucket (BLOCK-06 target)
- `quirk/engine/cache.py` — load_cache (BLOCK-05 target)
- `quirk/scanner/tls_scanner.py` — scan_tls_targets, _scan_one_sslyze (BLOCK-01/CR-07 target)
- `quirk/scanner/fingerprint.py` — _tcp_connect, _try_read_ssh_banner, fingerprint_port (BLOCK-01/CR-08 target)
- `quirk/scanner/gcp_connector.py` — _scan_cloud_sql (BLOCK-02 target)
- `quirk/scanner/k8s_connector.py` — scan_k8s_targets, _scan_aks_encryption (BLOCK-03 target)
- `quirk/scanner/azure_connector.py` — _scan_blob_encryption (BLOCK-04 target)

### K8S-03 Invariant Reference
- `quirk/scanner/k8s_connector.py` §K8S-03 docstring — defines the "never return empty list silently" invariant that BLOCK-03 must preserve

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/util/safe_exc.py` — `safe_str` helper for scrubbing exception text (used by Phase 59 vault/GCP credential leak fixes); may be relevant if GCP Cloud SQL exception paths need scrubbing
- `threading.Condition` — replaces `threading.Lock` in TokenBucket; `__init__` change drops `self.lock`, adds `self._cond = threading.Condition()`

### Established Patterns
- **K8S-03 inaccessible finding pattern** — `_emit_inaccessible_finding()` helper in `k8s_connector.py` produces a K8S-03-conformant result; the None-cred guard should call this, not raise
- **Exception path in `scan_tls_targets`** — outer `with ThreadPoolExecutor(...) as ex:` already handles pool shutdown on normal/exception exit; the leak is inside `_scan_one_sslyze`'s sslyze call, not the outer pool
- **cache.py load pattern** — `load_cache` → `save_cache` → `scope_hash` are the three cache primitives; only `load_cache` is buggy (ttl_hours=0 branch)
- **Azure Blob finding structure** — `_scan_blob_encryption` builds a dict with `key_source`, `severity`, `description`, `finding_id` (check exact field names before patching); BLOB-CMK / BLOB-PLATFORM / BLOB-UNKNOWN are new finding_id values, verify no downstream consumers key on the old implicit finding_ids

### Integration Points
- `quirk/engine/rate_limiter.py` is imported by cloud connectors for API rate limiting — the TokenBucket `threading.Condition` change must not break the public `acquire(tokens=1.0)` API
- `quirk/engine/cache.py` is imported by `run_scan.py` for discovery-phase caching — the `ttl_hours=0` fix changes observable behavior for any caller that passes `ttl_hours=0`

</code_context>

<specifics>
## Specific Ideas

- TokenBucket `threading.Condition` implementation shape is already agreed (see D-02 code snippet above). The planner should use this exact structure.
- Azure Blob finding_ids `BLOB-PLATFORM` and `BLOB-UNKNOWN` are new names — confirm no existing test fixtures or downstream callers key on the old implicit behavior before renaming.
- Fingerprint socket leak fix: line 154 `with s:` already provides context-manager closure for the SSH banner branch in the normal path — verify the audit finding's specific exception scenario before adding redundant `try/finally`.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 69-Deferred-BLOCKERs-Scanner-Cloud*
*Context gathered: 2026-05-14*
