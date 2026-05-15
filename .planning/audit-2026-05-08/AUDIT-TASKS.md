---
audit: comprehensive-codebase-2026-05-08
ledger_status: active
generated: 2026-05-09
triaged: 2026-05-10
total_findings: 169
closed: 34
open: 121
deferred: 13
wont_fix: 1
---

# Audit Findings Ledger — 2026-05-08

**Purpose:** Durable, mark-off-able tracking of every finding from the 2026-05-08 audit across the v4.8 milestone and into v4.9 triage.

**Lifecycle:**
- `[ ] open` — finding present in code, no decision yet
- `[ ] mapped` — closed-by a v4.8 phase; flips to `[x]` when that phase ships
- `[x] closed` — fix shipped, verified by phase verification
- `[ ] deferred-v4.9` — explicit decision to push to next milestone
- `[ ] wont-fix` — explicit decision not to address (with reason)

**How to use:**
1. During Wave A phase execution, executor flips matching rows to `[x]` after verification.
2. After Wave A complete, triage all remaining `open` rows — assign deferred-v4.9 / wont-fix / new-phase.
3. v4.9 milestone planning consumes this ledger as input.

---

## Summary

| Severity | Total | Mapped | Open | Closed | Deferred | Won't-fix |
|---|---:|---:|---:|---:|---:|---:|
| BLOCKER | 44 | 0 | 0 | 30 | 13 | 1 |
| WARNING | 96 | 0 | 92 | 4 | 0 | 0 |
| INFO | 29 | 0 | 29 | 0 | 0 | 0 |
| **TOTAL** | **169** | **0** | **121** | **34** | **13** | **1** |

---

## Findings by Subsystem

### Scanners — Protocol

| Finding ID | Severity | Title | Closed-By | Status |
|---|---|---|---|---|
| scanners-protocol/CR-01 | BLOCKER | JWT scanner disables TLS verification on JWKS fetch (MITM) | Phase 57 (HARDEN-SCAN-01) | [x] closed |
| scanners-protocol/CR-02 | BLOCKER | Argument injection into semgrep via repo_path | Phase 57 (HARDEN-SCAN-02) | [x] closed |
| scanners-protocol/CR-03 | BLOCKER | Argument injection into syft via image_ref | Phase 57 (HARDEN-SCAN-03) | [x] closed |
| scanners-protocol/CR-04 | BLOCKER | SSRF in SAML metadata fetcher — no scheme/host validation | Phase 57 (HARDEN-SCAN-04) | [x] closed |
| scanners-protocol/CR-05 | BLOCKER | Hardcoded guest:guest credentials sent to arbitrary hosts | Phase 57 (HARDEN-SCAN-05) | [x] closed |
| scanners-protocol/CR-06 | BLOCKER | verify=False on RabbitMQ mgmt API + ssl_cert_reqs=none Redis | Phase 57 (HARDEN-SCAN-06) | [x] closed |
| scanners-protocol/CR-07 | BLOCKER | Nested ThreadPoolExecutor + sslyze internal pool resource leak | Phase 69 (BLOCK-01 / CR-07) | [x] closed — closed by Phase 69 (BLOCK-01 / CR-07): sslyze Scanner lifecycle wrapped in try/finally with explicit del + gc.collect per locked decision D-05; outer ThreadPoolExecutor "with ex:" already shut down pool cleanly. Test: tests/test_tls_scanner_resource_cleanup.py (3 tests, structural + behavioral) |
| scanners-protocol/CR-08 | BLOCKER | fingerprint._tcp_connect socket leak on SSH banner branch | Phase 69 (BLOCK-01 / CR-08) | [x] closed — closed by Phase 69 (BLOCK-01 / CR-08): fingerprint socket closed on all exception paths via try/except BaseException at _try_read_ssh_banner span per locked decision D-06. Test: tests/test_fingerprint_socket_cleanup.py (4 tests) |
| scanners-protocol/WR-01 | WARNING | coverage.calculate_coverage can return >100% | Phase 71 | [x] closed — closed by Phase 71 (71-01 / PROTO-01): calculate_coverage return wrapped in max(0.0, min(1.0, ...)) per locked D-06; formula math unchanged per D-15. Tests: tests/test_coverage_bounds.py (clamp above/below + zero-denominator). |
| scanners-protocol/WR-02 | WARNING | quantum_readiness_score non-monotonic; severity case-sensitive | Phase 71 | [x] closed — closed by Phase 71 (71-01 / PROTO-01): severity comparison normalized via str(...).upper() before matching CRITICAL/HIGH/MEDIUM per locked D-07. Tests: tests/test_coverage_bounds.py (parametrized over mixed-case 'critical'/'high'/'medium' variants). |
| scanners-protocol/WR-03 | WARNING | Bare except Exception swallowing subprocess errors silently | Phase 71 | [x] closed — closed by Phase 71 (71-02 / PROTO-02): bare `except Exception` swallowing subprocess errors narrowed in 3 sites (quirk/scanner/ssh_scanner.py::_run_ssh_audit, quirk/scanner/container_scanner.py::scan_container_image, quirk/scanner/source_scanner.py::scan_source_repo) to explicit tuple (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError, json.JSONDecodeError) with module-level `_LOG.warning(...)` capturing failure context per locked D-08. Plan-time files_modified target (fingerprint.py) corrected post-investigation; the bare-except subprocess swallow flagged by WR-03 lives in the three scanner modules above, not fingerprint.py. Tests: tests/test_subprocess_logging.py (3 tests — timeout / FileNotFoundError / JSONDecodeError paths). |
| scanners-protocol/WR-04 | WARNING | nmap_provider default port CSV is incomplete and wrong | Phase 71 | [x] closed — closed by Phase 71 (71-03 / PROTO-03): default port CSV composed via default_nmap_ports_csv() unioning cfg.scan.ports_tls with fixed consulting set (22,25,80,88,389,465,587,636,993,995,3389,5671,8080,9092) per locked D-03. Tests: tests/test_nmap_hardening.py::test_default_port_csv_includes_consulting_set. |
| scanners-protocol/WR-05 | WARNING | nmap_provider.run_nmap_discovery accepts unvalidated extra_args | Phase 71 | [x] closed — closed by Phase 71 (71-03 / PROTO-03): _SAFE_NMAP_ARG_RE allowlist (^[A-Za-z0-9._:/=,-]+$) validates every extra_args token before subprocess; unsafe tokens raise ValueError per locked D-04 (mirrors Phase 70 _SAFE_COL_TYPE_RE). Tests: tests/test_nmap_hardening.py (allowlist accept/reject + subprocess-not-reached assertion). |
| scanners-protocol/WR-06 | WARNING | nmap_parser uses stdlib ET — XXE / billion-laughs surface | Phase 71 | [x] closed — closed by Phase 71 (71-03 / PROTO-03): nmap_parser imports defusedxml.ElementTree (defuses XXE/billion-laughs/external-DTD) per locked D-05; defusedxml already a core dep. Tests: tests/test_nmap_hardening.py::test_nmap_parser_uses_defusedxml + test_nmap_parser_blocks_xxe (EntitiesForbidden on external-entity DOCTYPE). |
| scanners-protocol/WR-07 | WARNING | dnssec _parse_dnskeys unbounded subscript on key_bytes | Phase 71 | [x] closed |
| scanners-protocol/WR-08 | WARNING | kerberos _probe_kdc_udp silently swallows all decode errors | Phase 71 | [x] closed |
| scanners-protocol/WR-09 | WARNING | kerberos _build_as_req uses non-cryptographic RNG for nonce | Phase 71 | [x] closed |
| scanners-protocol/WR-10 | WARNING | saml _classify_target parses JSON of arbitrary bytes; no size cap | Phase 71 | [x] closed |
| scanners-protocol/WR-11 | WARNING | Inconsistent extras messaging across optional-dep scanners | Phase 71 | [x] closed |
| scanners-protocol/WR-12 | WARNING | email/broker ThreadPool workers hardcoded to 50 | Phase 71 | [x] closed |
| scanners-protocol/WR-13 | WARNING | discovery/tls_scanner.py is dead-code duplicate | Phase 71 | [x] closed |
| scanners-protocol/WR-14 | WARNING | target_expander dedup; no CIDR bound; type confusion | Phase 71 | [x] closed |
| scanners-protocol/IN-01 | INFO | tls_capabilities downgrade SSLContext warrants comment | — | [ ] open |
| scanners-protocol/IN-02 | INFO | DNSSEC_ALG_MAP missing reserved algorithms 9, 11 | — | [ ] open |
| scanners-protocol/IN-03 | INFO | SHA1_INDICATORS substring match too loose | — | [ ] open |
| scanners-protocol/IN-04 | INFO | fingerprint _http_probe_plain sends Host: localhost | — | [ ] open |
| scanners-protocol/IN-05 | INFO | _is_pfs / _is_weak duplicated across email/broker/tls | — | [ ] open |
| scanners-protocol/IN-06 | INFO | kerberos _derive_realm IPv4 detection is fragile | — | [ ] open |

### Scanners — Cloud + Engine

| Finding ID | Severity | Title | Closed-By | Status |
|---|---|---|---|---|
| scanners-cloud/CR-01 | BLOCKER | migration_planner.py is a stub — does not implement scoring | — | [ ] wont-fix |
| scanners-cloud/CR-02 | BLOCKER | GCP Cloud SQL stuffs severity into cert_pubkey_alg field | Phase 69 (BLOCK-02) | [x] closed — closed by Phase 69 (BLOCK-02): Cloud SQL severity moved from cert_pubkey_alg column to severity column; description routed to service_detail per locked decision D-08; cert_pubkey_alg now absent from Cloud SQL findings. Tests: tests/test_cloud_connectors.py (3 assertions rewritten, 15 tests green) |
| scanners-cloud/CR-03 | BLOCKER | K8s scan_k8s_targets calls _scan_aks_encryption with None cred | — | [ ] deferred-v4.9 |
| scanners-cloud/CR-04 | BLOCKER | Vault scan_error leaks raw exception text incl token fragments | Phase 59 (LEAK-01) | [x] closed — closed by Phase 59 (safe_str helper in quirk/util/safe_exc.py applied to vault_connector scan_error path; AST gate test in tests/test_safe_exc_gate.py) |
| scanners-cloud/CR-05 | BLOCKER | GCP scan_gcp_targets exception message includes raw cred text | Phase 59 (LEAK-02) | [x] closed — closed by Phase 59 (safe_str helper in quirk/util/safe_exc.py applied to scan_gcp_targets exception path; AST gate test in tests/test_safe_exc_gate.py) |
| scanners-cloud/CR-06 | BLOCKER | Cache TTL boundary inverted on ttl_hours <= 0 | Phase 69 (BLOCK-05) | [x] closed — closed by Phase 69 (BLOCK-05): load_cache ttl_hours<=0 branch inverted per locked decision D-10 — ttl_hours=0 now means "cache disabled, never return". docs/UAT-SERIES.md documents the API contract change. Test: tests/test_cache.py (4 tests) |
| scanners-cloud/CR-07 | BLOCKER | TokenBucket starvation when tokens > capacity requested | Phase 69 (BLOCK-06 / CR-07) | [x] closed — closed by Phase 69 (BLOCK-06 / CR-07): TokenBucket capacity guard raises ValueError immediately when tokens > capacity per locked decision D-01; eliminates infinite loop hazard. Test: tests/test_rate_limiter.py::test_acquire_raises_when_tokens_exceed_capacity |
| scanners-cloud/CR-08 | BLOCKER | TokenBucket sleep + busy-wait can starve under contention | Phase 69 (BLOCK-06 / CR-08) | [x] closed — closed by Phase 69 (BLOCK-06 / CR-08): TokenBucket lock+sleep replaced with threading.Condition per locked decision D-02; threads block via _cond.wait(timeout=wait_secs) instead of busy-waiting; rate<=0 fast path added per D-03. Test: tests/test_rate_limiter.py::test_acquire_blocks_via_condition_no_busy_wait + 3 more (4 tests total) |
| scanners-cloud/CR-09 | BLOCKER | K8s scan_k8s_targets empty-list edge case violates K8S-03 | Phase 69 (BLOCK-03) | [x] closed — closed by Phase 69 (BLOCK-03 / CR-09): explicit empty-aks_clusters short-circuit added to scan_k8s_targets per locked decision D-09; returns [] without raising AttributeError and without emitting an inaccessible finding (that path reserved for credential=None / CR-03 / Phase 29). Test: tests/test_k8s_connector.py::test_aks_empty_cluster_list_returns_empty |
| scanners-cloud/CR-10 | BLOCKER | Azure Blob key_source microsoft.storage conflated with absent | Phase 69 (BLOCK-04) | [x] closed — closed by Phase 69 (BLOCK-04): Azure Blob _scan_blob_encryption now emits semantically distinct findings via service_detail + dat_scan_json[finding_id]: BLOB-PLATFORM (microsoft.storage), BLOB-UNKNOWN (absent/null), BLOB-CMK (microsoft.keyvault) per locked decision D-04 — no schema column added. evidence.py dar_storage_aws_managed_count extended to count BLOB/unknown alongside BLOB/platform-managed (preserves MEDIUM-tier scoring). Test: tests/test_azure_blob.py (10 tests, parameterized) |
| scanners-cloud/WR-01 | WARNING | AWS _scan_acm may pass empty ARN to describe_certificate | Phase 72 | [x] closed — closed by Phase 72 (72-01 / D-07): _scan_acm now guards describe_certificate with `if not arn or not arn.strip()` before the AWS API call; empty/whitespace ARNs from malformed listing responses degrade gracefully with `logger.v` warning (project Logger has no .warning method). Mirrors Phase 71 D-11 fail-soft pattern. Test: tests/test_aws_connector.py::test_scan_acm_skips_empty_arn + test_scan_acm_skips_whitespace_arn + test_scan_acm_emits_for_valid_arn |
| scanners-cloud/WR-02 | WARNING | AWS _scan_kms does not skip disabled or pending-deletion keys | Phase 72 | [x] closed — closed by Phase 72 (72-01 / D-08): _scan_kms now skips KeyMetadata.KeyState when it is in module-level frozenset `_KMS_SKIP_STATES = {"Disabled", "PendingDeletion", "PendingImport", "Unavailable"}`; INFO-level skip log via `logger.info(f"KMS key {key_id} skipped (state={state})")`. Test: tests/test_aws_connector.py::test_scan_kms_skips_non_encrypting_states (parametrized x4) + test_scan_kms_emits_for_enabled |
| scanners-cloud/WR-03 | WARNING | Azure _scan_keyvault_keys swallows key_size — always None | Phase 72 | [x] closed — closed by Phase 72 (72-02 / D-12): _scan_keyvault_keys derives key_size per-type — RSA via key.n.bit_length(), EC via _AZURE_EC_CURVE_SIZES map (P-256/384/521 + secp256k1), OCT via properties.key_size, unknown types leave None + DEBUG log via logger.v. Test: tests/test_azure_keyvault.py (9 tests covering RSA 2048/4096, EC P-256/P-384/P-521/secp256k1, OCT 256, unknown type, unknown curve) |
| scanners-cloud/WR-04 | WARNING | GCP _scan_kms triple-nested while with no pagination cap | Phase 72 | [x] closed — closed by Phase 72 (72-03 / D-01 / D-01a): MAX_KMS_PAGES = 1000 module constant added; each of the three pagination loops (locations, key-rings, crypto-keys) in _scan_kms maintains its own page_count counter and raises ValueError(f"GCP KMS pagination exceeded {MAX_KMS_PAGES} pages for {resource}; aborting to prevent runaway scan") on overflow. Mirrors PROTO-05 / WR-14 fail-loud pattern. Commit cce4e7b. Test: tests/test_gcp_connector.py::test_kms_pagination_cap_raises_after_1000_pages (parametrized at MAX_KMS_PAGES+1) + test_kms_pagination_under_cap_completes |
| scanners-cloud/WR-05 | WARNING | GCP _scan_kms skips UNSPECIFIED/UNKNOWN keys inconsistently | Phase 72 | [x] closed — closed by Phase 72 (72-03 / D-16): _GCP_KMS_SKIP_ALGORITHMS = frozenset({"CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED", "UNKNOWN"}) added at module scope; _scan_kms now checks the raw `algorithm` string against this set BEFORE the GCP_KMS_ALGORITHM_MAP lookup and emits an INFO log naming the original GCP enum value via `logger.info("GCP key %s skipped (algorithm=%s)", key_name, algorithm)`. Post-map `alg_name == "UNKNOWN"` branch retained per D-25. Commit cce4e7b. Test: tests/test_gcp_connector.py::test_kms_skips_unspecified_and_unknown_algorithms (parametrized over both skip values) + test_kms_emits_for_real_algorithm (negative-of-skip) |
| scanners-cloud/WR-06 | WARNING | K8s _emit_inaccessible_finding does not strip : from cluster_name | Phase 72 | [x] closed — closed by Phase 72 (72-02 / D-13): _emit_inaccessible_finding now applies cluster_name = (cluster_name or "").replace(":", "") at function entry before embedding in the finding's host identity tuple. Colons in cluster names no longer corrupt CSV/CBOM ordering or dedup. Test: tests/test_k8s_connector.py::test_emit_inaccessible_finding_strips_colon_from_cluster_name + test_emit_inaccessible_finding_empty_cluster_name_safe |
| scanners-cloud/WR-07 | WARNING | DB connector psycopg2.connect password defaults to empty string | Phase 72 | [x] closed — closed by Phase 72 (72-05 / D-20): scan_pg_targets and scan_mysql_targets now build the connect-kwargs dict conditionally — `password is None` omits the kwarg entirely (libpq reads .pgpass/PGPASSWORD; pymysql reads defaults file/env); `password == ""` is treated as an explicit empty-password attempt and passed through with an INFO log; non-empty passwords pass through normally. Removes the silent `password=password or ""` default that masked None as ""; tests: tests/test_db_connector.py::test_pg_connect_password_none_omits_kwarg, test_pg_connect_password_empty_string_passes_through, test_pg_connect_password_nonempty_passes_through, test_mysql_connect_password_none_omits_kwarg |
| scanners-cloud/WR-08 | WARNING | DB connector exception message does not strip target host | Phase 72 | [x] closed — closed by Phase 72 (72-05 / D-21, narrowed per RESEARCH C-2): postgres scan_error path was already routed through `quirk.util.safe_exc.safe_str(exc)` in Phase 59 LEAK-01. PLAN 05 extends safe_str coverage to the previously-missed `logger.v(...)` exception logging in both postgres and mysql branches (was emitting raw `{exc}` text) so credential-bearing exception messages cannot leak via verbose logs. Test: tests/test_db_connector.py::test_mysql_exception_uses_safe_str — RuntimeError carrying a long base64-shaped token is sanitized to just the exception class name in scan_error. |
| scanners-cloud/WR-09 | WARNING | vault_connector reads VAULT_TOKEN from env after token=None | Phase 72 | [x] closed — closed by Phase 72 (72-05 / D-22): scan_vault_targets now raises `ValueError("vault_connector requires explicit token; …")` when `token is None` — no implicit `os.environ['VAULT_TOKEN']` fallback inside the connector. Caller boundary (run_scan.py:1411) reads the env var explicitly: `_vault_token = cfg.connectors.vault_token or os.environ.get("VAULT_TOKEN", "")` and passes the resolved value through. Explicit empty-string token preserves the existing `vault-no-token` scan_error endpoint path. Test: tests/test_vault_connector.py::test_scan_vault_targets_raises_on_none_token + test_scan_vault_targets_accepts_explicit_token. Existing test_no_token_produces_scan_error migrated to test_empty_token_produces_scan_error to match new contract. |
| scanners-cloud/WR-10 | WARNING | risk_engine.py is misnamed / actual scorer not in this review | Phase 72 | [x] closed — closed by Phase 72 (72-05 / D-05 / D-05a): `git mv quirk/engine/risk_engine.py → quirk/engine/findings_evaluator.py` (added module docstring clarifying "NOT the score engine"); recreated risk_engine.py as a 2-line deprecation shim `"""Deprecated alias for quirk.engine.findings_evaluator. Removed in v5.0.""" + from quirk.engine.findings_evaluator import * + explicit re-exports of _-prefixed privates` (no DeprecationWarning at import per D-05). All 6 internal callers migrated atomically in the same commit (run_scan.py + 5 test modules, per D-05a default yes). Also repointed tests/fixtures/chaos_lab_findings.py AST aggregator to the new canonical file. Test: tests/test_findings_evaluator_dedupe.py::test_dedupe_via_risk_engine_shim_works (asserts shim and canonical reference the same function object). |
| scanners-cloud/WR-11 | WARNING | profiles.py mutates enable_email/enable_broker w/o user override | Phase 72 | [x] closed — closed by Phase 72 (72-05 / D-02 / D-02a): ConnectorsCfg gained `_user_set_fields: frozenset = field(default_factory=frozenset, repr=False, compare=False)` sidecar; quirk/config.py populates it post-construction via `connectors_cfg._user_set_fields = frozenset(conn_raw.keys())`. quirk/engine/profiles.py guards both `enable_email` and `enable_broker` mutations in both the deep and standard branches via `if "<field>" not in cfg.connectors._user_set_fields:`. A user who wrote `enable_email: false` in YAML is now respected — the profile no longer flips it back to True. Test: tests/test_profiles.py::test_profiles_respects_user_explicit_enable_email_false, test_profiles_flips_enable_email_when_not_user_set, test_profiles_respects_user_explicit_enable_broker_false, test_profiles_flips_enable_broker_when_not_user_set. |
| scanners-cloud/WR-12 | WARNING | profiles.py standard profile re-applies defaults equal to baseline | Phase 72 | [x] closed — closed by Phase 72 (72-05 / D-03): standard branch inventory of `_set_if_default` calls — removed 5 no-op calls whose value equalled the dataclass default: `fingerprint_timeout_seconds=4` (TimeoutsCfg.fingerprint_seconds default 4), `fingerprint_concurrency=200` (ScanCfg default 200), `tls_timeout_seconds=6` (TimeoutsCfg.tls_seconds default 6), `tls_concurrency=150` (ScanCfg default 150), `ssh_timeout_seconds=6` (TimeoutsCfg.ssh_seconds default 6). Retained `ssh_concurrency=150` — differs from ScanCfg default of 100. Per D-03 not a blanket strip; each removal documented via inline `# Phase 72 D-03 / WR-12: removed no-op …` breadcrumb. Test: tests/test_profiles.py::test_profiles_standard_branch_no_op_calls_removed (asserts exactly 1 uncommented _set_if_default call remains in the standard branch). |
| scanners-cloud/WR-13 | WARNING | AWS _scan_s3_encryption executor.map drops _classify exceptions | Phase 72 | [x] closed — closed by Phase 72 (72-01 / D-09): _scan_s3_encryption replaced `for ep in executor.map(_build_endpoint, buckets)` with `futures = {executor.submit(_build_endpoint, b): b for b in buckets}` + `for f in as_completed(futures)` + per-future try/except around `f.result()`; failures now logged at WARNING via logger.v instead of being silently swallowed. Mirrors the Phase 64 idiom from quirk/scanner/email_scanner.py:536-552. Audit cite said `_classify` but current code calls `_build_endpoint` (RESEARCH C-1) — locked behavior change applied to actual call site. Test: tests/test_aws_connector.py::test_scan_s3_propagates_build_endpoint_exception + test_scan_s3_uses_as_completed_pattern |
| scanners-cloud/WR-14 | WARNING | AWS _scan_eks_encryption reads enc_cfg[0] on multi-entry list | Phase 72 | [x] closed — closed by Phase 72 (72-01 / D-10): _scan_eks_encryption now iterates the entire `enc_cfg` list via `for cfg in enc_cfg:` and emits one CryptoEndpoint per provider entry (was `enc_cfg[0].get("provider", {}).get("keyArn", "")` reading only first entry). Each finding tags the keyArn in `service_detail = f"EKS/encrypted:{kms_key}"` so D-04 dedup keeps multi-provider entries distinct. Test: tests/test_aws_connector.py::test_scan_eks_emits_per_provider_entry + test_scan_eks_single_provider_still_one_finding |
| scanners-cloud/WR-15 | WARNING | Cache _read_json does not handle malformed JSON | Phase 72 | [x] closed — closed by Phase 72 (72-04 / D-18): _read_json wraps json.load in `try/except (json.JSONDecodeError, UnicodeDecodeError)`, logs WARNING via `logger = logging.getLogger(__name__)`, returns None. Corrupt cache file is intentionally left on disk for forensics (no os.remove). load_cache guards against None and treats it as a cache miss. Tests: tests/test_cache.py::test_read_json_returns_none_on_malformed_json + test_read_json_returns_none_on_unicode_error + test_load_cache_skips_corrupt_file |
| scanners-cloud/WR-16 | WARNING | cache.scope_hash does not include connector enable flags | Phase 72 | [x] closed — closed by Phase 72 (72-04 / D-19): scope_hash now includes `connectors` parts key built from `dataclasses.asdict(cfg.connectors)`. Toggling cfg.connectors.enable_email or enable_broker flips the resulting hash (cache invalidation). The `_user_set_fields` sidecar (added by PLAN 05 / D-02) is defensively `.pop("_user_set_fields", None)`-ed before json.dumps so the non-JSON-serializable frozenset doesn't raise; no-op if D-02 hasn't landed. Tests: test_scope_hash_changes_when_enable_email_flips, test_scope_hash_changes_when_enable_broker_flips, test_scope_hash_stable_for_identical_cfg, test_scope_hash_handles_user_set_fields_sidecar, test_scope_hash_sidecar_does_not_affect_hash |
| scanners-cloud/WR-17 | WARNING | K8s _enumerate_secret_types Counter may include None | Phase 72 | [x] closed — closed by Phase 72 (72-02 / D-14): _enumerate_secret_types now filters None-typed secrets explicitly via `Counter(t for t in secret_types if t is not None)` rather than coercing them to "Opaque" via `s.type or "Opaque"` (RESEARCH Pitfall 4). Skipped-None count logged at DEBUG via logger.v. None and Opaque are now semantically distinct in the count signal. Test: tests/test_k8s_connector.py::test_enumerate_secret_types_excludes_none |
| scanners-cloud/WR-18 | WARNING | Vault _scan_pki_mounts PEM split heuristic fragile | Phase 72 | [x] closed — closed by Phase 72 (72-05 / D-23): _scan_pki_mounts intermediate-chain path replaced the naive `chain_pem.split("-----BEGIN CERTIFICATE-----")` heuristic with `cryptography.x509.load_pem_x509_certificates(chain_bytes)` (plural form; available since cryptography>=36, pyproject pins >=44.0). Each parsed certificate is re-serialized via `cert.public_bytes(serialization.Encoding.PEM)` before classification — handles mixed line endings, embedded comments, and trailing whitespace correctly. Defensive `AttributeError` (lib too old) and `ValueError` (PEM parse error) branches log via safe_str and degrade gracefully. Test: tests/test_vault_connector.py::test_scan_pki_mounts_parses_multi_cert_chain + test_scan_pki_mounts_uses_load_pem_x509_certificates (static-source assertion). |
| scanners-cloud/WR-19 | WARNING | AWS module-level ThreadPoolExecutor import inside function | Phase 72 | [x] closed — closed by Phase 72 (72-01 / D-11): `from concurrent.futures import ThreadPoolExecutor, as_completed` moved from `_scan_s3_encryption` function body (was line 226-227) to module-scope imports block (now at top of file alongside other module imports). Combined with as_completed in the same line (consumed by D-09). Test: tests/test_aws_connector.py::test_threadpool_executor_imported_at_module_scope |
| scanners-cloud/WR-20 | WARNING | K8s key_name from unencrypted path included in dat_scan_json | Phase 72 | [x] closed — closed by Phase 72 (72-02 / D-15): _scan_gke_encryption now builds a fresh dat_scan_json dict per branch — the encrypted branch includes `key_name` and `encrypted: True`; the unencrypted branch explicitly omits `key_name` and sets `encrypted: False`. Inline comment marks the contract (`Phase 72 D-15`). Eliminates cross-branch dict pollution. Test: tests/test_k8s_connector.py::test_dat_scan_json_unencrypted_omits_key_name + test_dat_scan_json_encrypted_includes_key_name |
| scanners-cloud/WR-21 | WARNING | profiles.py tail truncated mid-function — verify EOF | Phase 72 | [x] closed — closed by Phase 72 (72-04 / D-06): file integrity verified via Pitfall-5 path. `python -m py_compile quirk/engine/profiles.py` exits 0; `git log -- profiles.py` shows last touch was 67b1537 (Phase 33-02 enable_broker gating) with no truncation; `wc -l` returned 153 pre-marker. No reconstruction needed — file IS intact. Action: appended a single `# eof` marker line as the final line (file now 155 lines including a one-line comment explaining the marker). Tests: tests/test_cache.py::test_profiles_py_has_eof_marker + test_profiles_py_compiles |
| scanners-cloud/WR-22 | WARNING | GCP _scan_cloud_sql description not surfaced via service_detail | Phase 72 | [x] closed — closed by Phase 72 (72-03 / D-17 / C-3 adjudication): _scan_cloud_sql now surfaces the Cloud SQL instance description in service_detail via slash-suffix encoding `CLOUD_SQL/<finding-desc>/<instance-desc-slug>` (falls back to 'no-description' when absent). Audit row's strict reading — instance['description'] field carried only in cloud_scan_json — was confirmed against HEAD: only the *finding* description (from SSL_FINDING_MAP) was previously in service_detail; the *instance* description was stranded. Corrective path applied per Task 2 step 3 (not the C-3 verify-only path). No schema change — uses existing single service_detail field per D-25. Commit 2f6921e (verifying commit cce4e7b for WR-04/05 sibling fixes). Test: tests/test_gcp_connector.py::test_cloud_sql_service_detail_contains_description |
| scanners-cloud/WR-23 | WARNING | evaluate_endpoints _postprocess_findings mutates during iteration | Phase 72 | [x] closed — closed by Phase 72 (72-05 / D-24): _postprocess_findings now iterates `for f in tuple(findings):` — defensive snapshot pattern. Per RESEARCH C-2 the current body only mutates fields of existing finding dicts in-place (no list extend/remove), so the risk is hypothetical today; the snapshot protects against future maintainers adding append/remove without re-checking iteration safety. Body unchanged except for the `tuple(...)` wrapping. Comment breadcrumb marks the contract (`Phase 72 D-24 / WR-23`). Indirectly covered by the suite of existing _postprocess_findings tests in tests/test_risk_engine.py — all 123 affected tests continue to pass post-edit. |
| scanners-cloud/WR-24 | WARNING | _dedupe_findings 4-tuple ordering causes unstable golden outputs | Phase 72 | [x] closed — closed by Phase 72 (72-05 / D-04 / D-04a / C-4 adjudication): inverted `_SEVERITY_RANK` to `{CRITICAL:0, HIGH:1, MEDIUM:2, LOW:3, INFO:4}` (lower rank = higher severity); dedup tie-break comparison flipped from `>` to `<` to preserve "higher-severity wins" semantics. `_dedupe_findings` sort key replaced with `(severity_rank, title, host, port)` — recommendation dropped entirely from the key so remediation-text edits no longer reshuffle golden output. RESEARCH C-4 / Pitfall 6 adjudicated: D-04's "finding_id" field has no analog in the current dedup tuple `(host, port, title, recommendation)`; maps to `title` (the existing identity-defining column). `_SEVERITY_RANK` kept module-private per D-04a default. No project goldens reference dedup ordering — verified via grep — so no snapshot regen required; the chaos_lab_findings AST aggregator was repointed in a separate `chore(72-05-snapshots)` commit per CONTEXT test_strategy. Test: tests/test_findings_evaluator_dedupe.py::test_dedupe_sort_stable_under_recommendation_diff, test_dedupe_sort_severity_priority, test_severity_rank_module_private. |

### QRAMM + Compliance

| Finding ID | Severity | Title | Closed-By | Status |
|---|---|---|---|---|
| qramm-compliance/BL-01 | BLOCKER | Profile multiplier not clamped server-side | Phase 60 (SCORE-01) | [x] closed |
| qramm-compliance/BL-02 | BLOCKER | Maturity threshold gap mis-classifies scores in [1.4,1.5) etc. | Phase 60 (SCORE-02) | [x] closed |
| qramm-compliance/BL-03 | BLOCKER | last_verified lexicographic string comparison is fragile | Phase 64.1 (BL-03) | [x] closed — closed by Phase 64.1 (tests/test_compliance_status_staleness.py) |
| qramm-compliance/BL-04 | BLOCKER | int(years_raw) accepts negative/zero years | Phase 64.1 (BL-04) | [x] closed — closed by Phase 64.1 (tests/test_operator_context_years_clamp.py) |
| qramm-compliance/WR-01 | WARNING | Evidence bridge date-string equality vulnerable to TZ drift | — | [ ] open |
| qramm-compliance/WR-02 | WARNING | compute_practice_score accepts out-of-range answers | Phase 74 | [x] closed |
| qramm-compliance/WR-03 | WARNING | evidence_bridge synchronize_session=fetch suboptimal; no idempotency | — | [ ] open |
| qramm-compliance/WR-04 | WARNING | Practice 1.1 Discovery score ignores endpoint count entirely | Phase 74 | [x] closed |
| qramm-compliance/WR-05 | WARNING | vuln_pct unbounded division — zero algos scores 4 (Advanced) | Phase 74 | [x] closed |
| qramm-compliance/WR-06 | WARNING | Maturity label >=4.0 unreachable at multiplier=1.0 (FP noise) | Phase 74 | [x] closed |
| qramm-compliance/WR-07 | WARNING | evidence_bridge does not handle db.commit failure | — | [ ] open |
| qramm-compliance/WR-08 | WARNING | attach_context swallows AttributeError; user context dropped | — | [ ] open |
| qramm-compliance/WR-09 | WARNING | migration_advisor substring matching produces false positives | — | [ ] open |
| qramm-compliance/WR-10 | WARNING | _walk_json_for_alg_strings skips non-_ALG_KEYS strings | — | [ ] open |
| qramm-compliance/WR-11 | WARNING | compliance_map.py weight 0.0 ambiguous vs not-yet-covered | — | [ ] open |
| qramm-compliance/WR-12 | WARNING | model_meta.py lacks is_qramm_model_stale helper | — | [ ] open |
| qramm-compliance/WR-13 | WARNING | TODO Phase 50 comment left in production module header | — | [ ] open |

### CBOM + Intelligence + Reports

| Finding ID | Severity | Title | Closed-By | Status |
|---|---|---|---|---|
| cbom-intel-reports/CR-01 | BLOCKER | CBOM Pass-1 emits zero algo components for 12 protocol families | Phase 61 (CBOM-COVER-01) | [x] closed — closed by Phase 61 (CBOM-COVER-01, see tests/test_cbom_coverage.py per-family parametrize) |
| cbom-intel-reports/CR-02 | BLOCKER | VAULT protocol falls through to TLS branch in Pass-1/2/3 | Phase 61 (CBOM-COVER-02) | [x] closed — closed by Phase 61 (CBOM-COVER-02, dedicated VAULT Pass-1 branch + tests/test_cbom_vault_consistency.py golden snapshot) |
| cbom-intel-reports/CR-03 | BLOCKER | SOURCE algo hint maps DES->3DES and collapses AES variants | Phase 64.1 (CR-03) | [x] closed — closed by Phase 64.1 (tests/test_cbom_builder_algo_hints.py) |
| cbom-intel-reports/CR-04 | BLOCKER | Confidence returns 100% TLS-enum coverage when no TLS scanned | Phase 60 (SCORE-03) | [x] closed |
| cbom-intel-reports/CR-05 | BLOCKER | Trend 1-second session window cannot disambiguate two scans | Phase 64.1 (CR-05) | [x] closed — closed by Phase 64.1 (tests/test_trends_subsecond_sessions.py) |
| cbom-intel-reports/CR-06 | BLOCKER | Score subscores can sum >100; agility_score added unbounded | Phase 60 (SCORE-04) | [x] closed |
| cbom-intel-reports/CR-07 | BLOCKER | Markdown injection / table-break in technical.py finding rows | Phase 61 (REPORT-SAN-01) | [x] closed — closed by Phase 61 (REPORT-SAN-01/02, quirk/reports/_md_escape.py md_cell + tests/test_report_sanitization.py adversarial corpus) |
| cbom-intel-reports/WR-01 | WARNING | PDF render uses blanket except Exception — masks programmer errors | Phase 73 | [x] closed — closed by Phase 73 (73-01 / INTEL-01 / D-01): render_pdf_report's inner blanket `except Exception` replaced with narrowed tuple `(PlaywrightError, PlaywrightTimeoutError, OSError, RuntimeError)` per RESEARCH C-2 sync-API translation. Programmer bugs (e.g., KeyError) now propagate. Test: tests/test_pdf_render_hardening.py::test_render_pdf_propagates_unexpected_exception |
| cbom-intel-reports/WR-02 | WARNING | PDF render does not clean up Playwright resources on exception | Phase 73 | [x] closed — closed by Phase 73 (73-01 / INTEL-01 / D-01): Playwright lifecycle wrapped in try/finally; `browser` initialized to None pre-try, finally calls `if browser is not None: try: browser.close() except Exception: pass` (close-time errors never mask original failure). Sync API has no explicit context (RESEARCH C-2). Tests: tests/test_pdf_render_hardening.py::test_render_pdf_closes_browser_in_finally + test_render_pdf_close_failure_does_not_mask |
| cbom-intel-reports/WR-03 | WARNING | motion_broker_weak_tls_count predicate uses inconsistent uppercase | Phase 73 | [x] closed — closed by Phase 73 (73-02 / INTEL-02 / D-10): evidence.py motion_broker block routes through new `quirk.util.weak_crypto.is_legacy_tls_version` (legacy-TLS set) and `is_weak_cipher` (weak-token set). Structural TLS_RSA_WITH_ + ECDHE-less-AES-SHA clauses preserved inline per D-10 boundary. Test: tests/test_intelligence_evidence.py::test_motion_broker_legacy_tls |
| cbom-intel-reports/WR-04 | WARNING | ECDSA detection in evidence.py mismatches cert_pubkey_alg conventions | Phase 73 | [x] closed — closed by Phase 73 (73-02 / INTEL-02 / D-03): ECDSA branch at evidence.py:132 changed from `startswith("ECDSA")` to `startswith(("EC", "ECDSA"))`. Consumer now accepts both TLS-scanner ("EC") and cloud-KMS-normalizer ("ECDSA") emitter conventions without touching emitters (D-14). Tests: tests/test_intelligence_evidence.py::test_ecdsa_alias_ec + test_ecdsa_alias_ecdsa + test_ecdsa_negative_ed25519 |
| cbom-intel-reports/WR-05 | WARNING | _apply_weighted_impacts uses fixed score_cap=25.0 | Phase 60 (SCORE-04) | [x] closed |
| cbom-intel-reports/WR-06 | WARNING | SCORE_WEIGHTS sum is 261, not normalized | Phase 73 | [x] closed — closed by Phase 73 (73-03 / INTEL-03 / D-04): module-level comment block above SCORE_WEIGHTS naming the invariant (sum=261.0 BY DESIGN, NOT probabilities, NOT normalized) and citing Phase 60 SCORE-04/CR-06 cap-sharing rationale. CI gate added at tests/test_score_weights_invariant.py asserting abs(sum - 261.0) < 1e-9 and len == 29. No weight values changed (D-14). |
| cbom-intel-reports/WR-07 | WARNING | Roadmap _why string-format produces double-period artifacts | Phase 73 | [x] closed — closed by Phase 73 (73-03 / INTEL-03 / D-05): `_why` returns `f"{base} Driver: {hint.rstrip('.')}."` so a hint already ending in `.` no longer produces `..`. Tests: tests/test_intelligence_roadmap.py::test_why_no_double_period_when_hint_ends_with_period + test_why_preserves_no_period_hint + test_why_empty_hint_unchanged. |
| cbom-intel-reports/WR-08 | WARNING | Roadmap mutation-after-yield merge rule undocumented | Phase 73 | [x] closed — closed by Phase 73 (73-03 / INTEL-03 / D-06): multi-line docstring added to `_add_candidate` describing the lower-(_PHASE_ORDER[phase], int(_priority), title)-tuple-wins merge rule. RESEARCH C-6: module is not a generator; "mutation-after-yield" phrasing was figurative. Tests: tests/test_intelligence_roadmap.py::test_add_candidate_merge_lower_key_wins + test_add_candidate_merge_higher_key_loses + test_add_candidate_merge_equal_key_preserves_original. |
| cbom-intel-reports/WR-09 | WARNING | executive _build_interpretation accesses score['score'] w/o guard | Phase 73 | [x] closed — closed by Phase 73 (73-03 / INTEL-03 / D-07): module-level `_INTERPRETATION_UNAVAILABLE` constant + `_build_interpretation` guards via `score.get('score') if isinstance(score, dict) else None`; on missing/non-dict returns `{"bullets": [_INTERPRETATION_UNAVAILABLE]}`. `score['rating']` replaced with `score.get('rating', 'Unknown')`. Tests: tests/test_executive_score_guard.py (5 cases — full dict, None, empty, non-dict, missing rating). |
| cbom-intel-reports/WR-10 | WARNING | evidence.py SAML weak detection equality on uppercased SHA1 fragile | Phase 73 | [x] closed — closed by Phase 73 (73-02 / INTEL-02 / D-02): SAML branch at evidence.py:159 replaced `_saml_alg == "SHA1"` with `is_weak_cipher(_saml_alg)`. Now catches "SHA-1", "sha1", "#rsa-sha1" and the full D-02 weak-token set. Test: tests/test_intelligence_evidence.py::test_saml_sha1_mixed_case |
| cbom-intel-reports/WR-11 | WARNING | evidence.py motion email weak-cipher predicate diverges from broker | Phase 73 | [x] closed — closed by Phase 73 (73-02 / INTEL-02 / D-02): motion_email predicate now uses `is_weak_cipher(cipher)`, matching the broker token set (DES, DES-CBC, IDEA, CBC3, ANON, NULL, EXPORT, MD5, SHA1, SHA-1, 3DES, RC4). Single source of truth via `quirk.util.weak_crypto`. Tests: tests/test_intelligence_evidence.py::test_motion_email_des_cbc_now_detected + test_email_broker_parity_token_set |
| cbom-intel-reports/WR-12 | WARNING | _decompose_cipher_suite returns wrong KEX for RSA non-PFS in TLS1.2 | Phase 73 | [x] closed — closed by Phase 73 (73-03 / INTEL-03 / D-08): `_KEX_MAP["RSA"] = "RSA-kex"` at quirk/cbom/builder.py:142 (NOT evidence.py — RESEARCH C-1). Single-token relabel chosen over dual-emit path (RESEARCH C-4 path (a)) — no Pass-1/2/3 logic change. Tests: tests/test_tls_kex_label.py parametrizes 8 non-PFS RSA TLS 1.2 suites (assert 'RSA-kex' present, bare 'RSA' absent) + ECDHE-RSA negative test + TLS 1.3 path-unaffected test. |
| cbom-intel-reports/WR-13 | WARNING | confidence.py weight overrides bypass clamp and validation | Phase 73 | [x] closed — closed by Phase 73 (73-03 / INTEL-03 / D-09): inline at compute_confidence override block (confidence.py:46-49 at HEAD — RESEARCH C-5: no `apply_weight_overrides` function exists). `float()` coercion with `(TypeError, ValueError)` re-raised as ValueError(f"...must be numeric in [0.0, 1.0]..."); clamp via `max(0.0, min(1.0, num))`; `_LOGGER.warning(...)` for unknown override keys (forward-compat per CONTEXT). Tests: tests/test_intelligence_confidence.py adds 7 cases (below-zero / above-one / in-range / non-numeric / None / list / unknown-key WARNING). |
| cbom-intel-reports/WR-14 | WARNING | writer.py PDF graceful degradation prints no warning to user | Phase 73 | [x] closed — closed by Phase 73 (73-01 / INTEL-01 / D-01): user-visible advisory `f"PDF generation failed: {safe_str(e)}; scan complete, HTML report at {html_path}"` printed to sys.stderr from the callee (html_renderer.py) on the narrowed-except path. Exception text routed through `quirk.util.safe_exc.safe_str` (AST-gated). RESEARCH C-3: callee-emit chosen because both `e` and `html_path` are in scope. Tests: tests/test_pdf_render_hardening.py (3 advisory assertions) + tests/test_reports_writer.py::test_pdf_failure_advisory_propagates_via_writer |
| cbom-intel-reports/IN-01 | INFO | Hardcoded PLATFORM_VERSION = 4.4.0 duplicated across modules | — | [ ] open |
| cbom-intel-reports/IN-02 | INFO | _extract_ssh_algorithms swallows JSONDecodeError silently | — | [ ] open |
| cbom-intel-reports/IN-03 | INFO | Trend analysis fetches all endpoints into memory per session | — | [ ] open |
| cbom-intel-reports/IN-04 | INFO | evidence.py _PROTOCOL_KEYS missing CONTAINER/SOURCE/AWS/etc. | — | [ ] open |
| cbom-intel-reports/IN-05 | INFO | Roadmap baseline governance item only when len < min_items | — | [ ] open |
| cbom-intel-reports/IN-06 | INFO | executive truncates Migration Paths at 10 with no indicator | — | [ ] open |
| cbom-intel-reports/IN-07 | INFO | html_renderer roadmap_section timeframe comparison dead branch | — | [ ] open |
| cbom-intel-reports/IN-08 | INFO | writer hosts_count set falsy hosts collapse to single "" | — | [ ] open |
| cbom-intel-reports/IN-09 | INFO | Schema dataclass IntelligenceReport defined but unused | — | [ ] open |

### Dashboard API + CLI + Core

| Finding ID | Severity | Title | Closed-By | Status |
|---|---|---|---|---|
| api-cli-core/CR-01 | BLOCKER | Path traversal in quirk init --output | Phase 58 (HARDEN-API-02) | [x] closed |
| api-cli-core/CR-02 | BLOCKER | SSRF / port binding in routes/pdf.py via QUIRK_SERVE_PORT | Phase 58 (HARDEN-API-03) | [x] closed |
| api-cli-core/CR-03 | BLOCKER | Missing authentication on every dashboard route | Phase 58 (HARDEN-API-01) | [x] closed |
| api-cli-core/CR-04 | BLOCKER | QRAMMProfile.session_id is nullable and has no DB-level FK | Phase 70 | [x] closed — closed by Phase 70 (BLOCK-07): ForeignKey(qramm_sessions.id, ondelete=SET NULL) on QRAMMProfile.session_id + _ensure_qramm_profiles_fk 12-step rebuild + per-connection PRAGMA foreign_keys=ON via connect event. Tests: tests/test_qramm_models.py::test_qramm_profiles_has_db_level_fk, ::test_connect_event_enables_fk_pragma |
| api-cli-core/CR-05 | BLOCKER | delete_session does not clear qramm_sessions.profile_id link | Phase 70 | [x] closed — closed by Phase 70 (BLOCK-07): delete_session re-ordered to null session.profile_id + flush before profile/answer deletes (D-04). Tests: tests/test_qramm_delete_session_fk.py::test_delete_session_with_profile_clears_fk, ::test_delete_session_with_profile_and_answers |
| api-cli-core/CR-06 | BLOCKER | Bare except: pass in classifier call drops findings silently | Phase 70 | [x] closed — closed by Phase 70 (BLOCK-08): _qs_for_alg narrowed to except (KeyError, TypeError, AttributeError) with logger.warning; unrelated exceptions propagate. Tests: tests/test_cbom_scan_route.py (full file — 6 tests covering swallow + propagation) |
| api-cli-core/CR-07 | BLOCKER | SQL injection guard on column names lacks col_type DDL fragment | Phase 70 | [x] closed — closed by Phase 70 (BLOCK-08): _SAFE_COL_TYPE_RE allowlist + ValueError guard in _ensure_v43/_phase41/_phase46/_phase54_qramm_columns. Tests: tests/test_db_migrations.py (full file — regex matrix + 4 poisoned-dict tests) |
| api-cli-core/CR-08 | BLOCKER | init_db ALTER TABLE migrations are not transactional | Phase 64.1 (CR-08) | [x] closed — closed by Phase 64.1 (tests/test_init_db_idempotent.py) |
| api-cli-core/CR-09 | BLOCKER | parse_target_tokens reflective DoS via deep @file recursion | Phase 58 (HARDEN-API-04) | [x] closed |
| api-cli-core/WR-01 | WARNING | _check_dashboard / _check_network always return True | — | [ ] open |
| api-cli-core/WR-02 | WARNING | _check_db opens DB at default path regardless of QUIRK_DB_PATH | — | [ ] open |
| api-cli-core/WR-03 | WARNING | _default_db_path mtime-newest-wins is non-deterministic | — | [ ] open |
| api-cli-core/WR-04 | WARNING | get_latest_scan ?scan_id= time-window slice off-by-microsecond | — | [ ] open |
| api-cli-core/WR-05 | WARNING | list_scans groups by string-formatted timestamp — TZ-fragile | — | [ ] open |
| api-cli-core/WR-06 | WARNING | compute_overall_score multiplier validated client-side only | — | [ ] open |
| api-cli-core/WR-07 | WARNING | routes/qramm read_session returns score=None on JSON corruption | — | [ ] open |
| api-cli-core/WR-08 | WARNING | _derive_dar_findings swallows json.loads errors with bare except | — | [ ] open |
| api-cli-core/WR-09 | WARNING | _compute_multiplier rounds before clamp — boundary fragile | — | [ ] open |
| api-cli-core/WR-10 | WARNING | interactive _prompt_int infinite loop on EOF | — | [ ] open |
| api-cli-core/WR-11 | WARNING | interactive exposure default silently used when input not 1/2/3 | — | [ ] open |
| api-cli-core/WR-12 | WARNING | setattr enable_nmap injects undeclared dataclass attribute | — | [ ] open |
| api-cli-core/WR-13 | WARNING | validate.py artifact list missing intelligence-{stamp}.json | — | [ ] open |
| api-cli-core/WR-14 | WARNING | qramm_cmd env override has no try/except on malformed input | — | [ ] open |
| api-cli-core/WR-15 | WARNING | routes/scan reads QUIRK_OUTPUT_DIR from env into Path read | — | [ ] open |
| api-cli-core/WR-16 | WARNING | parse_target_tokens does not validate hostnames | — | [ ] open |
| api-cli-core/WR-17 | WARNING | routes/qramm list_questions fragile on QRAMM_QUESTIONS schema drift | — | [ ] open |
| api-cli-core/IN-01 | INFO | Dict[str, Any] type erasure on QRAMM endpoints | — | [ ] open |
| api-cli-core/IN-02 | INFO | _FACES banner has \- ambiguous escape (comment misleading) | — | [ ] open |
| api-cli-core/IN-03 | INFO | interactive timezone fallback to UTC string vs IANA name | — | [ ] open |
| api-cli-core/IN-04 | INFO | Magic numbers for QRAMM clamp 0.8 / 1.5 / 0.10 / 0.20 | — | [ ] open |
| api-cli-core/IN-05 | INFO | app.py closure captures via default argument missing | — | [ ] open |
| api-cli-core/IN-06 | INFO | db.py _ensure_*_columns helpers collapse to one helper | — | [ ] open |
| api-cli-core/IN-07 | INFO | targets.py projected_probe_count materializes /8 host list | — | [ ] open |

### React Frontend

| Finding ID | Severity | Title | Closed-By | Status |
|---|---|---|---|---|
| react-frontend/BR-01 | BLOCKER | Debounced draft persister drops fields on rapid multi-field edits | Phase 62 (HOOK-01) | [x] closed |
| react-frontend/BR-02 | BLOCKER | Confirm-auto-fill flow never persists confirmed_at to server | Phase 62 (HOOK-02) | [x] closed |
| react-frontend/BR-03 | BLOCKER | useScanData error setters lack cancellation guard | Phase 62 (HOOK-03) | [x] closed |
| react-frontend/BR-04 | BLOCKER | useScanData does not clear stale data when scan switches | Phase 62 (HOOK-03) | [x] closed |
| react-frontend/BR-05 | BLOCKER | /print data-ready sentinel never reset — stale on re-fetch | Phase 62 (HOOK-04) | [x] closed |
| react-frontend/BR-06 | BLOCKER | System theme not reactive — prefers-color-scheme read once | Phase 62 (HOOK-04) | [x] closed |
| react-frontend/WR-01 | WARNING | useQRAMMSession setError/setSession run without cancellation guard | Phase 62 (HOOK-01) | [x] closed |
| react-frontend/WR-02 | WARNING | useScanList silently swallows non-OK responses | — | [ ] open |
| react-frontend/WR-03 | WARNING | Pending QRAMM debounce timers leak on provider unmount | Phase 62 (HOOK-03) | [x] closed |
| react-frontend/WR-04 | WARNING | theme-provider casts localStorage value to Theme without validation | — | [ ] open |
| react-frontend/WR-05 | WARNING | executive PDF download setTimeout revoke leaks across unmount | — | [ ] open |
| react-frontend/WR-06 | WARNING | executive reads body.detail without coercion check | — | [ ] open |
| react-frontend/WR-07 | WARNING | print data-ready set even when QRAMM has errored | — | [ ] open |
| react-frontend/WR-08 | WARNING | qramm-profile submitError swallows actual error message | — | [ ] open |
| react-frontend/WR-09 | WARNING | certificates Subject CN regex breaks on RFC2253-escaped commas | — | [ ] open |
| react-frontend/WR-10 | WARNING | cbom Cytoscape registration uses cast without proper typing | — | [ ] open |
| react-frontend/WR-11 | WARNING | ScorecardTab Maturity Distribution width math hardcodes /4 | — | [ ] open |
| react-frontend/WR-12 | WARNING | ScorecardTab maturity bar applies badge text/border classes | — | [ ] open |
| react-frontend/WR-13 | WARNING | ComplianceMapTab re-fetches on every ctx.scoreResult change | — | [ ] open |
| react-frontend/WR-14 | WARNING | qramm-assessment handleNewAssessment does not abort debounced persists | Phase 62 (HOOK-03) | [x] closed |
| react-frontend/IN-01 | INFO | qramm-assessment comment says 5-tab but renders 6 tabs | — | [ ] open |
| react-frontend/IN-02 | INFO | cbom/roadmap try/catch swallows extension registration error | — | [ ] open |
| react-frontend/IN-03 | INFO | findings/identity recreate columns array on every render | — | [ ] open |
| react-frontend/IN-04 | INFO | useQRAMMSession seededRef not reset on New Assessment flow | — | [ ] open |
| react-frontend/IN-05 | INFO | cbom compByAlg lookups use [0] for representative — drops variance | — | [ ] open |
| react-frontend/IN-06 | INFO | print createElement style injection works but non-standard React | — | [ ] open |
| react-frontend/IN-07 | INFO | useScanData does not propagate actual fetch URL into errors | — | [ ] open |

---

## Cross-Cutting Patterns

Findings rolled up into a single phase fix.

- **Pattern A — Credential leakage via exception stringification:** scanners-cloud/CR-04, scanners-cloud/CR-05, scanners-cloud/WR-08, scanners-cloud/WR-09, api-cli-core/WR-08, api-cli-core/WR-15 → Phase 59 (LEAK-01..03). Top-15 blockers (CR-04, CR-05) are mapped above; remaining warnings flagged here for Phase 59 opportunistic close.
- **Pattern B — Untrusted input flowing to subprocess / HTTP:** scanners-protocol/CR-02, CR-03, CR-04, WR-05, WR-06, WR-10 → Phase 57 (HARDEN-SCAN-02..04). Top-15 blockers mapped above; warnings are sub-instances candidate for Phase 57 close.
- **Pattern C — Cancellation guard inconsistency in React hooks:** react-frontend/BR-01..BR-06 (mapped), plus react-frontend/WR-01, WR-03, WR-14 → Phase 62 (HOOK-01..04) opportunistic close.
- **Pattern D — Migration safety:** api-cli-core/CR-07, api-cli-core/CR-08, scanners-cloud/WR-15, scanners-cloud/CR-06 → flag as `open` (not mapped; candidate for v4.9 or Phase 67 RESUME).
- **Pattern E — Score arithmetic correctness:** cbom-intel-reports/CR-04, CR-06, WR-05, WR-06, qramm-compliance/BL-01, BL-02, WR-05, WR-06 → Phase 60 (SCORE-01..04). Top-15 + WR-05 mapped; remainder candidate for Phase 60 opportunistic close.

---

## Initial Triage Recommendations

For findings NOT mapped to a Wave A phase, suggest a default disposition based on the finding text. **These are recommendations only — no triage decisions are recorded as final dispositions in this ledger.**

- **Likely defer-v4.9 (dead/misnamed code):**
  - scanners-protocol/WR-13 — `quirk/discovery/tls_scanner.py` dead duplicate (delete)
  - cbom-intel-reports/IN-09 — `quirk/intelligence/schema.py` unused dataclasses
  - scanners-cloud/CR-01 — `migration_planner.py` 16-line stub
  - scanners-cloud/WR-10 — `risk_engine.py` rename / scoping
  - qramm-compliance/WR-09 — migration_advisor false-positives
  - AUDIT-SUMMARY explicitly suggests v5.2 chaos lab + tech debt sweep for dead-code cleanup.

- **Likely close-during-Wave-A (opportunistic in-phase fixes):**
  - All Pattern A warnings (Phase 59)
  - All Pattern B warnings (Phase 57)
  - Pattern C remaining warnings (Phase 62)
  - Pattern E remaining warnings (Phase 60)
  - Subsystem INFO findings adjacent to BLOCKER fixes already in scope

- **Likely won't-fix (audit text flagged low-value or addressed-by-design):**
  - cbom-intel-reports/IN-05 — Roadmap baseline governance item (probably intentional, undocumented)
  - cbom-intel-reports/IN-08 — writer hosts_count edge case (defensive-but-misleading)
  - api-cli-core/IN-05 — closure capture pattern (correct as-is)
  - react-frontend/IN-04 — useQRAMMSession seededRef (no action required per audit text)

These are recommendations for the human triage pass.

---

_Generated: 2026-05-09 from `.planning/audit-2026-05-08/` REVIEW.md files._

---

## Dispositions — Phase 64.1 (2026-05-10)

Structured rationale blocks for all 14 remaining open BLOCKERs not addressed by a code fix in Phase 64.1 Plan 1. Applied per CONTEXT.md D-06 format.

---

### scanners-protocol/CR-07 — Nested ThreadPoolExecutor + sslyze pool resource leak

> **deferred-v4.9** — scanners-protocol/CR-07
> - Rationale: sslyze invocation in tls_scanner uses a context-manager pool nested inside the scanner's own ThreadPoolExecutor; on exception inside sslyze's pool, the inner pool can leak threads.
> - Safe to defer: Triggers only on sslyze internal exception during TLS enumeration. Resource leak is bounded by scan lifetime (single-shot CLI invocation; FastAPI dashboard scans are also bounded). No long-running daemon mode exists.
> - Fix phase: v4.9 scanner reliability sweep — would naturally pair with WR-12 thread pool sizing work.
> - Risk: low — daemon mode does not exist; per-scan leak is reclaimed at process exit.

---

### scanners-protocol/CR-08 — fingerprint._tcp_connect socket leak on SSH banner branch

> **deferred-v4.9** — scanners-protocol/CR-08
> - Rationale: SSH banner branch in fingerprint._tcp_connect opens a socket but on early-return error path does not always close it.
> - Safe to defer: Sockets are reclaimed at scan-process exit; SSH fingerprinting is a niche code path; no production deployments report file descriptor exhaustion.
> - Fix phase: v4.9 scanner reliability sweep — pair with CR-07 thread/resource leak cleanup.
> - Risk: low — bounded by single scan run; no daemon mode.

---

### scanners-cloud/CR-01 — migration_planner.py is a 16-line stub

> **wont-fix** — scanners-cloud/CR-01
> - Rationale: migration_planner.py is dead code — the real migration recommendation logic lives in quirk/intelligence/migration_advisor.py (audited separately as qramm-compliance/WR-09). The stub will be removed in v5.2 chaos-lab + tech-debt sweep per AUDIT-SUMMARY recommendation. No code path imports the stub today.
> - Acceptable because: The file is entirely unused — zero imports, zero callers. It does not score, classify, or process anything. Leaving it in place creates confusion (misleading filename) but no correctness or security risk. Removal is a cleanup task, not a bug fix.
> - Fix phase: v5.2 dead-code removal (delete file entirely).
> - Risk: low — unused module; misleading filename only.

---

### scanners-cloud/CR-02 — GCP Cloud SQL stuffs severity into cert_pubkey_alg field

> **deferred-v4.9** — scanners-cloud/CR-02
> - Rationale: gcp_connector._scan_cloud_sql writes the severity string ("WARN", "CRITICAL") into the cert_pubkey_alg column, conflating algorithm and severity.
> - Safe to defer: Output is consumed only by GCP-specific reporting; users see the conflation in raw JSON but the dashboard's severity badge is derived independently from the severity column. No incorrect finding classification occurs; the issue is data-field misuse only.
> - Fix phase: v4.9 GCP connector polish — pair with scanners-cloud/WR-22 (Cloud SQL description not surfaced).
> - Risk: low — cosmetic field misuse; severity is still computed correctly elsewhere.

---

### scanners-cloud/CR-03 — K8s scan_k8s_targets calls _scan_aks_encryption with None cred

> **deferred-v4.9** — scanners-cloud/CR-03
> - Rationale: When azure_cred is unavailable but AKS targets are present, _scan_aks_encryption is invoked with None and fails with AttributeError caught by a bare except.
> - Safe to defer: K8s is opt-in via the cloud profile + extras install; most users hit the documented "azure-identity not installed" path long before this branch. Failure is silent (caught) — no incorrect findings, just missing data for that AKS target.
> - Fix phase: v4.9 K8s reliability sweep — pair with CR-09 empty-list edge case (same function, same phase scope).
> - Risk: medium — silent data loss for AKS users who have credentials misconfigured; operator sees incomplete results without error indication.

---

### scanners-cloud/CR-06 — Cache TTL boundary inverted on ttl_hours <= 0

> **deferred-v4.9** — scanners-cloud/CR-06
> - Rationale: Cache._is_fresh treats ttl_hours <= 0 as "always fresh" instead of "never fresh"; documentation says ttl=0 disables caching.
> - Safe to defer: Default ttl_hours is 24; no production config sets ttl <= 0. Operators who want to disable cache use --no-cache or set ttl very low (e.g., 0.001h) which still produces correct behavior.
> - Fix phase: v4.9 cache subsystem cleanup — Pattern D migration-safety group.
> - Risk: low — only manifests when operator deliberately sets ttl <= 0 via config or CLI; no default path affected.

---

### scanners-cloud/CR-07 — TokenBucket starvation when tokens > capacity requested

> **deferred-v4.9** — scanners-cloud/CR-07
> - Rationale: TokenBucket.acquire(n) where n > capacity loops forever because the bucket can never accumulate that many tokens.
> - Safe to defer: All current callers request n=1 (single API call per acquire). No code path requests n > capacity. A defensive precondition check would protect future contributors but provides zero operational benefit today.
> - Fix phase: v4.9 rate-limiting sweep — pair with CR-08 contention starvation fix.
> - Risk: low — no current caller triggers this path; only manifests if future code requests n > capacity.

---

### scanners-cloud/CR-08 — TokenBucket sleep + busy-wait contention starvation

> **deferred-v4.9** — scanners-cloud/CR-08
> - Rationale: Under high concurrent acquire load, the sleep-then-retry loop without a fair queue can starve some callers indefinitely.
> - Safe to defer: Cloud scanners run with ThreadPoolExecutor max_workers=8 typically; bucket sizing is per-cloud-provider rate limits. Real-world contention is bounded and no production starvation has been reported.
> - Fix phase: v4.9 rate-limiting sweep — pair with CR-07 capacity starvation fix.
> - Risk: medium — could manifest under aggressive parallelism settings (large --max-workers or future parallel scan dispatch from Phase 65).

---

### scanners-cloud/CR-09 — K8s scan_k8s_targets empty-list edge case violates K8S-03

> **deferred-v4.9** — scanners-cloud/CR-09
> - Rationale: When target list is empty after filtering, scan_k8s_targets returns a malformed empty result that violates the K8S-03 contract (expected: empty list with metadata; actual: bare empty list).
> - Safe to defer: Empty-target path is exercised only when all K8s clusters are explicitly excluded from the scan. Dashboard handles bare empty list gracefully (no crash, just empty table).
> - Fix phase: v4.9 K8s reliability sweep — pair with CR-03 None-credential AKS bug (same function scope).
> - Risk: low — schema cosmetic; no user-visible incorrect data or crash; contract violation only affects downstream API consumers.

---

### scanners-cloud/CR-10 — Azure Blob key_source microsoft.storage conflated with absent

> **deferred-v4.9** — scanners-cloud/CR-10
> - Rationale: azure_blob._classify treats key_source="Microsoft.Storage" and key_source=None as the same case, masking the distinction between platform-managed-keys (known state) and unknown-state.
> - Safe to defer: Both states produce the same finding severity (WARN — not customer-managed); the conflation only affects the detail/description string, not the classification or severity badge shown in the dashboard.
> - Fix phase: v4.9 Azure connector polish — pair with scanners-cloud/WR-03 Azure keyvault key_size fix.
> - Risk: low — finding severity unchanged; only diagnostic detail text is less precise.

---

### api-cli-core/CR-04 — QRAMMProfile.session_id nullable, no DB-level FK

> **deferred-v4.9** — api-cli-core/CR-04
> - Rationale: QRAMMProfile model declares session_id as nullable=True with no SQLAlchemy ForeignKey constraint; orphan profiles can exist after session deletion if the application-level cascade fails.
> - Safe to defer: delete_session does cascade in application code (Phase 51 D-09 decision); the missing DB-level FK is a defense-in-depth gap, not a current exploitable bug. No orphan profiles have been observed in practice.
> - Fix phase: v4.9 QRAMM data model hardening — pair with CR-05 stale FK pointer fix (same model, same migration).
> - Risk: low — application-level cascade works correctly; DB-level constraint is belt-and-suspenders hardening only.

> **closed by Phase 70** — 70-01
> - Resolution: ForeignKey(qramm_sessions.id, ondelete=SET NULL) added to QRAMMProfile.session_id (D-03); _ensure_qramm_profiles_fk 12-step rebuild for existing DBs (D-01); per-connection PRAGMA foreign_keys=ON via SQLAlchemy connect event (D-02).
> - Evidence: tests/test_qramm_models.py::test_qramm_profiles_has_db_level_fk, ::test_connect_event_enables_fk_pragma
> - Commit: (pending)

---

### api-cli-core/CR-05 — delete_session does not clear qramm_sessions.profile_id link

> **deferred-v4.9** — api-cli-core/CR-05
> - Rationale: delete_session removes QRAMMSession but does not null out the reverse profile_id pointer on QRAMMProfile, leaving the profile with a stale FK string referencing a deleted session.
> - Safe to defer: No code path reads profile.session_id without re-validating against the live sessions table; the stale pointer is inert and causes no incorrect data to be displayed or returned.
> - Fix phase: v4.9 QRAMM data model hardening — pair with CR-04 nullable FK constraint fix.
> - Risk: low — dangling pointer is read-only stale data; no incorrect behavior triggered.

> **closed by Phase 70** — 70-01
> - Resolution: delete_session re-ordered per D-04 — null session.profile_id, db.flush(), then delete linked QRAMMProfile rows, then QRAMMAnswer rows, then the session itself. FK-safe under PRAGMA foreign_keys=ON.
> - Evidence: tests/test_qramm_delete_session_fk.py::test_delete_session_with_profile_clears_fk, ::test_delete_session_with_profile_and_answers
> - Commit: (pending)

---

### api-cli-core/CR-06 — Bare except: pass in classifier call drops findings silently

> **deferred-v4.9** — api-cli-core/CR-06
> - Rationale: One classifier invocation path swallows all exceptions with bare `except: pass`, dropping findings without logging any indication of the failure.
> - Safe to defer: Classifier exceptions are extremely rare given that input is structured Pydantic models validated at ingestion. Failure mode is silent under-count (missing findings), not a crash or false positive.
> - Fix phase: v4.9 logging-hygiene sweep — pair with bare-except findings across WR-03, WR-08, IN-02 (common pattern across subsystems).
> - Risk: medium — silent finding loss is invisible to operators; scan result may under-report vulnerabilities without any warning.

> **closed by Phase 70** — 70-02
> - Resolution: _qs_for_alg narrowed to except (KeyError, TypeError, AttributeError) per D-05 with logger.warning("classifier failed for alg=%r: %s", ...) on the swallowed cases; unrelated exceptions (e.g., RuntimeError) propagate to surface real bugs.
> - Evidence: tests/test_cbom_scan_route.py (full file — 6 tests covering swallow + propagation)
> - Commit: (pending)

---

### api-cli-core/CR-07 — SQL injection guard on column names lacks col_type DDL fragment

> **deferred-v4.9** — api-cli-core/CR-07
> - Rationale: _SAFE_COL_RE allowlist validates column names but the col_type DDL fragment (e.g., "TEXT", "VARCHAR(16)") appended in ALTER TABLE statements is interpolated without a separate validation guard.
> - Safe to defer: All col_type values are hardcoded string constants in _V43_COLUMN_DDLS, _PHASE41_COLUMN_DDLS, and equivalent dicts — they are never user-influenced. Current attack surface is zero; the gap is a "future contributor adds a dynamic col_type" defense failure, not a present-day injection vector.
> - Fix phase: v4.9 schema-migration safety sweep — pair with init_db idempotency hardening (the test added by Phase 64.1 Plan 1 for CR-08 already exercises the migration path).
> - Risk: low — zero current attack surface; all col_type values are repo-hardcoded constants; only a future code change could introduce the vector.

> **closed by Phase 70** — 70-03
> - Resolution: _SAFE_COL_TYPE_RE = ^(TEXT|INTEGER|REAL|BOOLEAN|DATETIME|VARCHAR\(\d{1,4}\))$ added at quirk/db.py module scope adjacent to _SAFE_COL_RE per D-06; ValueError("Unsafe column type in migration: ...") guard inserted in _ensure_v43_columns, _ensure_phase41_columns, _ensure_phase46_columns, _ensure_phase54_qramm_columns. D-07 do-not-touch list (identity/gcp/email/broker) preserved.
> - Evidence: tests/test_db_migrations.py (full file — regex matrix + 4 poisoned-dict tests)
> - Commit: (pending)
