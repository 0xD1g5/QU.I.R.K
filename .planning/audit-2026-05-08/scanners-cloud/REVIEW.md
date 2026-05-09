---
status: issues_found
files_reviewed: 11
depth: deep
reviewed: 2026-05-08
findings:
  critical: 10
  warning: 24
  info: 0
  total: 34
---

# Code Review — Cloud Connectors + Engine Subsystem

**Reviewed:** 2026-05-08
**Depth:** deep
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Cross-file deep review of cloud connectors (AWS/Azure/GCP/DB/K8s/Vault) and engine modules (cache/migration_planner/profiles/rate_limiter/risk_engine). Several BLOCKER-class defects identified — most notably, `migration_planner.py` is a near-empty stub that does not match the subsystem's stated purpose, and `risk_engine.py` is actually a findings evaluator (not a scorer) — the actual scoring/risk-engine arithmetic was therefore not reviewable from this file set; flagged as scoping defect.

Additional defects span credential-bearing exception messages, anti-patterns swallowing AKS scan errors, GCP Cloud SQL severity-misuse (placed in `cert_pubkey_alg`), cache TTL boundary inversion, rate limiter starvation under contention, and several control-flow bugs in `k8s_connector.scan_k8s_targets`.

---

## BLOCKER Findings

### CR-01: `migration_planner.py` is a stub — does not implement scoring/wave logic safely
**File:** `quirk/engine/migration_planner.py:1-16`
**Issue:** This entire module is 16 lines. Crashes with `KeyError`/`TypeError` on any non-dict input. Does not validate input is a list; does not handle `None`/missing severity; does not normalize case (`"high"` vs `"HIGH"`); does not handle finding objects (only dicts); silently buckets unknown severities into `"LATER"` with no distinction.
**Fix:** Add input validation + case normalization + explicit unknown-severity bucket.

### CR-02: GCP Cloud SQL stuffs severity into `cert_pubkey_alg` field
**File:** `quirk/scanner/gcp_connector.py:262-272`
**Issue:** The severity string ("HIGH"/"MEDIUM") is being assigned to `cert_pubkey_alg`. Schema misuse — downstream CBOM/classifier reads `cert_pubkey_alg` as a cryptographic algorithm name. CryptoEndpoint also has no `severity=...` set, so actual severity is lost.
**Fix:** Set `severity=severity` on CryptoEndpoint, remove the `cert_pubkey_alg=severity` line.

### CR-03: K8s `scan_k8s_targets` calls `_scan_aks_encryption` even when credential is None
**File:** `quirk/scanner/k8s_connector.py:492-499`
**Issue:** Subtle control flow — when `aks_clusters` is empty and credential succeeds, `_scan_aks_encryption` is invoked on `[]` and silently returns `[]`, violating the K8S-03 invariant (no inaccessible finding emitted).
**Fix:** Add explicit empty-cluster guard before invoking `_scan_aks_encryption`, or have `_scan_aks_encryption` itself emit an inaccessible finding when its `cluster_configs` list is empty.

### CR-04: Vault scan_error returns leak full exception text including potential token fragments
**File:** `quirk/scanner/vault_connector.py:421-430, 443-452`
**Issue:** `scan_error=f"vault-client-init-failed: {exc}"` interpolates raw exception. `hvac` exceptions on auth failures sometimes include the request URL with token query parameters or wrapped HTTP payloads. Persisted to SQLite and rendered in the report — credential-exposure risk.
**Fix:** `scan_error=f"vault-client-init-failed: {type(exc).__name__}"`.

### CR-05: GCP `scan_gcp_targets` exception message includes raw credentials error text
**File:** `quirk/scanner/gcp_connector.py:381`
**Issue:** `scan_error_msg = f"gcp-credentials-unavailable: {exc}"` — `DefaultCredentialsError` may contain file paths to ADC files and credential metadata. Persisted to DB.
**Fix:** Stringify only the exception class.

### CR-06: Cache TTL boundary inverted on `ttl_hours <= 0`
**File:** `quirk/engine/cache.py:59-62`
**Issue:** `if ttl_hours <= 0: return obj` — callers passing `ttl_hours=0` get the cached entry FOREVER. Opposite of the typical convention where 0 means "no caching".
**Fix:** Document explicitly OR invert: `if ttl_hours <= 0: return None`.

### CR-07: TokenBucket starvation when `tokens > capacity` requested
**File:** `quirk/engine/rate_limiter.py:20-32`
**Issue:** If `acquire(tokens=N)` is called with `N > self.capacity`, the loop spins forever — `self.tokens` is bounded by `self.capacity`, can never reach `N`.
**Fix:** Add guard at top: `if tokens > self.capacity: raise ValueError(...)`.

### CR-08: TokenBucket sleep + busy-wait can starve under heavy contention
**File:** `quirk/engine/rate_limiter.py:23-32`
**Issue:** Fixed `time.sleep(0.01)` causes thundering-herd; under fairness loss, individual callers can wait indefinitely. No timeout parameter.
**Fix:** Add `timeout: Optional[float]` parameter, return `bool`, compute precise sleep needed.

### CR-09: K8s `scan_k8s_targets` empty-list edge case violates K8S-03
**File:** `quirk/scanner/k8s_connector.py:368, 366, 527`
**Issue:** Caller passing `[]` (vs None) for `gke_clusters` causes silent skip without emitting the K8S-03 inaccessible finding.
**Fix:** After dispatching GKE/AKS branches, emit explicit inaccessible finding for empty configured cluster lists.

### CR-10: Azure Blob `key_source == "microsoft.storage"` conflated with absent encryption
**File:** `quirk/scanner/azure_connector.py:173-179`
**Issue:** Code treats `microsoft.storage`, empty string, and `None` all as `MEDIUM/BLOB/platform-managed`. Absence of encryption config means SDK call failed/returned unexpected shape — labeling that as "platform-managed" emits a misleading finding.
**Fix:** Distinguish three states: CMK / platform-managed / unreadable (emit `scan_error`).

---

## WARNING Findings

- **WR-01:** AWS `_scan_acm` may pass empty ARN to `describe_certificate` (`aws_connector.py:53-66`).
- **WR-02:** AWS `_scan_kms` does not skip disabled or pending-deletion keys (`aws_connector.py:315-346`).
- **WR-03:** Azure `_scan_keyvault_keys` swallows `key_size` from properties incorrectly — always None (`azure_connector.py:50-56`).
- **WR-04:** GCP `_scan_kms` triple-nested `while` with no pagination iteration cap (`gcp_connector.py:131-224`).
- **WR-05:** GCP `_scan_kms` skips `CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED` AND `UNKNOWN`-mapped keys inconsistently (`gcp_connector.py:174-180`).
- **WR-06:** K8s connector `_emit_inaccessible_finding` does not strip `:` from cluster_name (`k8s_connector.py:344-352`).
- **WR-07:** DB connector `psycopg2.connect` password defaults to empty string (different from None) (`db_connector.py:88-95, 213-220`).
- **WR-08:** DB connector exception message does not strip target host (`db_connector.py:158-167`).
- **WR-09:** `vault_connector` reads `VAULT_TOKEN` from env after explicit token=None (covered by CR-04).
- **WR-10:** `risk_engine.py` is misnamed / missing — actual risk engine code not in this review. Scoping error to flag to parent.
- **WR-11:** `profiles.py` mutates `cfg.connectors.enable_email`/`enable_broker` without checking explicit user override (`profiles.py:110-117, 134-141`).
- **WR-12:** `profiles.py` standard profile re-applies defaults that are equal to baseline, no-op'ing (`profiles.py:121-122`).
- **WR-13:** AWS `_scan_s3_encryption` `executor.map` exceptions silently dropped on `_classify` failure (`aws_connector.py:303-306`).
- **WR-14:** AWS `_scan_eks_encryption` reads `enc_cfg[0].get("provider")` on potentially multi-entry list (`aws_connector.py:165-169`).
- **WR-15:** Cache `_read_json` does not handle malformed JSON (`cache.py:27-29, 56-63`).
- **WR-16:** `cache.scope_hash` does not include connector enable flags — toggling does NOT invalidate cache (`cache.py:32-47`).
- **WR-17:** K8s `_enumerate_secret_types` `Counter` may include `None` as type (`k8s_connector.py:286-288`).
- **WR-18:** Vault `_scan_pki_mounts` PEM split heuristic fragile (`vault_connector.py:277-282`).
- **WR-19:** AWS module-level `from concurrent.futures import ThreadPoolExecutor` inside function (`aws_connector.py:226-227`).
- **WR-20:** K8s `try/except` nests `getattr(db_enc, "key_name")` twice — `key_name` from unencrypted path included in `dat_scan_json` misleadingly (`k8s_connector.py:136-156`).
- **WR-21:** `profiles.py` tail truncated mid-function — verify EOF marker (`profiles.py:153`).
- **WR-22:** GCP `_scan_cloud_sql` description placed in `cloud_scan_json` only — should surface via `service_detail` (`gcp_connector.py:262-272`).
- **WR-23:** `evaluate_endpoints` `_postprocess_findings` mutates findings during iteration (`risk_engine.py:335-371`).
- **WR-24:** `_dedupe_findings` orders by 4-tuple including recommendation — unstable golden-file outputs (`risk_engine.py:312-319`).

---

## Cross-File / Cross-Cutting Concerns

- **Credential-leak risk pattern (CR-04, CR-05, WR-08):** Multiple connectors stringify exceptions into `scan_error`/log messages without redaction. Recommend a shared `quirk/util/safe_exc.py::safe_str(exc)` helper.

- **Missing-extra graceful degradation:** All connectors use `try: import ...; FOO_AVAILABLE = True` correctly. However, the `enable_*` config flag is checked NOWHERE in connector modules — modules trust that `run_scan.py` gated the call. Importing `quirk.scanner.aws_connector` triggers `import boto3` even when `enable_aws=False`. Cold-import time of boto3 is hundreds of ms. **Fix:** Lazy-import inside entry points.

- **Risk engine arithmetic NOT in this review:** Per WR-10, the directive's score-engine concerns (subscore weights, division-by-zero, multiplier clamping) cannot be verified from `quirk/engine/risk_engine.py` because that file is a findings evaluator, not a scorer. The actual scoring code is elsewhere (likely `quirk/intelligence/scoring.py`).

---

_Reviewed: 2026-05-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
