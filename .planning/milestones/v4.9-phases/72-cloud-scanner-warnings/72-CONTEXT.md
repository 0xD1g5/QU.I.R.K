# Phase 72: Cloud Scanner WARNINGs - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Close all 24 WARNING-severity audit findings in the cloud-scanner subsystem from the 2026-05-08 audit ledger (`scanners-cloud/WR-01..WR-24`). Internal-contract changes and bug fixes only — no new scan capabilities, no schema changes, no new pip dependencies.

**In scope (mapped to CLOUD-NN requirements):**

- **CLOUD-01** — AWS connector hardening: `_scan_acm` empty-ARN guard, `_scan_kms` skip disabled/pending-deletion keys, `_scan_s3_encryption` propagate `_classify` exceptions through `executor.map`, `_scan_eks_encryption` reads entire `enc_cfg` list not index 0 (closes WR-01, WR-02, WR-13, WR-14)
- **CLOUD-02** — Azure/K8s data correctness: KeyVault `key_size` populated for all key types, K8s `cluster_name` colon-strip before finding emission, K8s `Counter` excludes `None` values, K8s `key_name` omitted in unencrypted path of `dat_scan_json` (closes WR-03, WR-06, WR-17, WR-20)
- **CLOUD-03** — GCP connector correctness: KMS pagination loop has hard iteration cap, UNSPECIFIED/UNKNOWN key handling is consistent, Cloud SQL description surfaced via `service_detail` (closes WR-04, WR-05, WR-22)
- **CLOUD-04** — Cache + scope_hash + profiles.py integrity: `_read_json` handles malformed JSON gracefully, `scope_hash` includes connector enable flags, `profiles.py` EOF verified intact (closes WR-15, WR-16, WR-21)
- **CLOUD-05** — Miscellaneous cloud hardening: `risk_engine.py` rename + shim, `profiles.py` email/broker mutation guarded via raw-YAML key tracking, standard profile re-apply suppressed when default-equal, `vault_connector` VAULT_TOKEN env order, `db_connector` password empty-string default + exception host strip, AWS `ThreadPoolExecutor` import at module level, Vault `_scan_pki_mounts` PEM split hardened, `_postprocess_findings` safe under iteration, `_dedupe_findings` ordering stable (closes WR-07..WR-12, WR-18, WR-19, WR-23, WR-24)

**Out of scope (deferred to other phases or explicitly do-not-touch):**

- CBOM/intelligence/reports WARNINGs (Phase 73) — `cbom-intel-reports/WR-*`
- QRAMM + compliance WARNINGs (Phase 74) — `qramm-compliance/WR-*`
- API/CLI core WARNINGs (Phase 75) — `api-cli-core/WR-*`
- React frontend WARNINGs (Phase 76) — `react-frontend/WR-*`
- All BLOCKER-severity rows (already closed in Phase 69)
- `scanners-cloud/CR-01` (migration_planner.py stub) — `wont-fix`, see audit ledger
- `scanners-cloud/CR-03` (K8s scan_k8s_targets None cred) — `deferred-v4.9`, separate concern
- Any code path not explicitly named in WR-01..WR-24 (see D-15 do-not-touch list)
- The real risk-score engine in `quirk/intelligence/` (out of audit scope per WR-10)

</domain>

<decisions>
## Implementation Decisions

### GCP KMS pagination cap (CLOUD-03 / WR-04)

- **D-01 (locked):** Each `while page_token:` loop in `quirk/scanner/gcp_connector.py::_scan_kms` (lines 131-224, the project-rings → key-rings → keys triple-nested loop) maintains a `page_count` counter. If `page_count > MAX_KMS_PAGES` (constant `MAX_KMS_PAGES = 1000` at module scope), raise `ValueError(f"GCP KMS pagination exceeded {MAX_KMS_PAGES} pages for {resource}; aborting to prevent runaway scan")`. Mirrors PROTO-05 / WR-14 D-01 fail-loud pattern. 1000 pages × default ~1000 items/page = 1M items, well above any real KMS deployment ceiling.
- **D-01a (Claude's discretion):** Whether to apply the cap independently per loop level or share a single counter across all three — default to per-loop (each iteration domain bounded separately, simpler to reason about).

### profiles.py enable_email/enable_broker mutation guard (CLOUD-05 / WR-11)

- **D-02 (locked):** Track raw YAML key presence at config-load time. In `quirk/config.py` (~line 377 — `conn_raw = {k:v for k,v in (raw.get('connectors') or {}).items() ...}`), after building the `ConnectorCfg`, stash the user-provided key set: `cfg.connectors._user_set_fields = frozenset(conn_raw.keys())`. Use `dataclasses.field(default_factory=frozenset, repr=False, compare=False)` on the `ConnectorCfg` dataclass to declare the sidecar (or attach post-init if Python-version-pinned dataclass keyword behavior makes that cleaner). In `quirk/engine/profiles.py:110-117, 134-141` (both `deep` and `standard` branches), guard each mutation:
  ```python
  if 'enable_email' not in cfg.connectors._user_set_fields:
      if not cfg.connectors.enable_email:
          cfg.connectors.enable_email = True
  ```
  Same shape for `enable_broker`. A user who explicitly wrote `enable_email: false` in YAML is now respected.
- **D-02a (Claude's discretion):** Naming of the sidecar attribute — `_user_set_fields`, `_explicit_fields`, or `_yaml_set` — researcher picks whichever fits closest to any prior precedent (grep for `_user_set` / `_explicit` first).

### profiles.py standard re-apply suppression (CLOUD-05 / WR-12)

- **D-03 (locked):** In the `standard` branch of `profiles.py`, audit each `_set_if_default(...)` call where the supplied value equals the field's dataclass default. Remove those calls — they are no-ops that obscure intent. Specifically `profiles.py:121-122` per the audit row. Researcher to inventory the full set; do not blanket-strip — only suppress where `value == dataclasses.fields(ScanCfg)._field_default`.

### _dedupe_findings sort key (CLOUD-05 / WR-24)

- **D-04 (locked):** In `quirk/engine/risk_engine.py::_dedupe_findings` (lines 312-319), replace the current 4-tuple sort key (which includes `recommendation`) with `(severity_rank, finding_id, host, port)`. `severity_rank` is a module-level dict mapping severity strings to integers (`{'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4}`). `host` and `port` come from each finding's identity columns. Drop `recommendation` entirely — remediation text edits must not reshuffle golden-file output ordering.
- **D-04a (Claude's discretion):** Whether to expose the `severity_rank` dict as a public helper (`from quirk.engine.risk_engine import severity_rank`) for reuse in tests, or keep it module-private. Default private; promote later if a second caller appears.

### risk_engine.py rename + shim (CLOUD-05 / WR-10)

- **D-05 (locked):** `git mv quirk/engine/risk_engine.py quirk/engine/findings_evaluator.py`. Recreate `quirk/engine/risk_engine.py` as a 2-line shim:
  ```python
  """Deprecated alias for quirk.engine.findings_evaluator. Removed in v5.0."""
  from quirk.engine.findings_evaluator import *  # noqa: F401, F403
  ```
  No `DeprecationWarning` at import time — pure structural rename; users get a runtime warning only when the v5.0 removal lands. Add module docstring to `findings_evaluator.py` clarifying: "Post-scan findings evaluator — NOT the score engine. Quantum-readiness scoring lives in `quirk/intelligence/`."
- **D-05a (Claude's discretion):** Whether to also update internal imports across the codebase in the same commit. Default yes — single commit, atomic. Researcher to grep for `from quirk.engine.risk_engine` / `import quirk.engine.risk_engine` and migrate all to `findings_evaluator`. The shim then exists only for any external/user code that may import the old name.

### profiles.py EOF verification (CLOUD-04 / WR-21)

- **D-06 (locked):** Researcher runs in sequence:
  1. `python -m py_compile quirk/engine/profiles.py` — must pass
  2. `git log --oneline -5 -- quirk/engine/profiles.py` — inspect last 5 commits
  3. `wc -l quirk/engine/profiles.py` — current line count
  4. Visual diff of last 30 lines vs. last green known-good commit (e.g., Phase 71 tag)
  
  **If file compiles AND tail matches git history:** Add explicit `# eof` marker comment at the final line. Flip WR-21 to closed with evidence `file intact, py_compile passed, no truncation detected, # eof marker added`.
  
  **If file is actually truncated:** Reconstruct missing tail from `git show HEAD~N:quirk/engine/profiles.py` at the last green commit (find via `git bisect` or successive `git log` if needed). Flip WR-21 to closed with evidence `tail reconstructed from <commit_sha>`.

### AWS _scan_acm empty-ARN guard (CLOUD-01 / WR-01)

- **D-07 (locked):** `quirk/scanner/aws_connector.py::_scan_acm` (lines 53-66) — before calling `describe_certificate(CertificateArn=arn)`, guard with `if not arn or not arn.strip(): logger.warning("ACM cert with empty ARN — skipping"); continue`. Empty ARN comes from listing responses with malformed entries; do not raise — degrade gracefully like Phase 71 D-11.

### AWS _scan_kms disabled-key skip (CLOUD-01 / WR-02)

- **D-08 (locked):** `quirk/scanner/aws_connector.py::_scan_kms` (lines 315-346) — after `describe_key`, check `KeyMetadata.KeyState`. Skip the key (continue the loop) when `KeyState` ∈ `{"Disabled", "PendingDeletion", "PendingImport", "Unavailable"}`. These keys cannot encrypt new data and pollute the scorecard. Log at INFO level: `KMS key %s skipped (state=%s)`.

### AWS _scan_s3_encryption executor.map exception propagation (CLOUD-01 / WR-13)

- **D-09 (locked):** `quirk/scanner/aws_connector.py:303-306` — `executor.map(_classify, ...)` silently swallows exceptions until results are consumed. Replace with `as_completed` + explicit per-future `.exception()` check, logging each `_classify` failure at WARNING and continuing. Pattern matches the Phase 64 `as_completed` migration in `quirk/scanner/email_scanner.py` (researcher to verify exact site).

### AWS _scan_eks_encryption multi-entry read (CLOUD-01 / WR-14)

- **D-10 (locked):** `quirk/scanner/aws_connector.py:165-169` — `enc_cfg[0].get("provider")` reads only the first entry. EKS allows multiple encryption providers per cluster. Change to iterate: `for cfg in enc_cfg: provider = cfg.get("provider"); ...`. Emit one finding per provider entry; tag each with the provider type so the dedup in D-04 keeps them distinct.

### AWS ThreadPoolExecutor module-level import (CLOUD-05 / WR-19)

- **D-11 (locked):** `quirk/scanner/aws_connector.py:226-227` — move `from concurrent.futures import ThreadPoolExecutor` from the function body to module scope (top of file alongside other imports). Pure structural; no behavior change.

### Azure KeyVault key_size population (CLOUD-02 / WR-03)

- **D-12 (locked):** `quirk/scanner/azure_connector.py::_scan_keyvault_keys` (lines 50-56) — `key_size` is always None because the code reads `properties.key_size` instead of inspecting the key material. For RSA: read `key.n` bit-length via `(key.n.bit_length())`. For EC: map curve name to standard size (`P-256` → 256, `P-384` → 384, `P-521` → 521, `secp256k1` → 256). For OCT: read `properties.key_size` if present. For unknown key types: `key_size = None` is acceptable, log at DEBUG. Use existing helper if one exists (researcher to grep `key_size` across `quirk/scanner/`).

### K8s cluster_name colon-strip (CLOUD-02 / WR-06)

- **D-13 (locked):** `quirk/scanner/k8s_connector.py::_emit_inaccessible_finding` (lines 344-352) — `cluster_name.replace(":", "")` before embedding in the finding's identity tuple. Colons in cluster names break CSV/CBOM output ordering and dedup. Apply at the single emit site.

### K8s Counter None exclusion (CLOUD-02 / WR-17)

- **D-14 (locked):** `quirk/scanner/k8s_connector.py::_enumerate_secret_types` (lines 286-288) — `Counter(t for t in secret_types if t is not None)`. None-typed secrets are filtered out of the count and logged at DEBUG with the count of skipped Nones.

### K8s dat_scan_json key_name omission (CLOUD-02 / WR-20)

- **D-15 (locked):** `quirk/scanner/k8s_connector.py:136-156` — the nested `try/except` currently populates `dat_scan_json["key_name"]` even on the unencrypted code path (where `getattr(db_enc, "key_name")` happens to return a stale value from the encrypted branch). Restructure so the unencrypted path emits a `dat_scan_json` dict that explicitly does NOT include the `key_name` key. Use a fresh dict in each branch; never reuse the encrypted-branch dict.

### GCP UNSPECIFIED/UNKNOWN key consistency (CLOUD-03 / WR-05)

- **D-16 (locked):** `quirk/scanner/gcp_connector.py:174-180` — currently skips `CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED` but does not skip `UNKNOWN`-mapped keys. Add `UNKNOWN` to the skip set; or symmetrically include both. Locked: skip both (`{"CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED", "UNKNOWN"}`); log at INFO `GCP key %s skipped (algorithm=%s)`.

### GCP Cloud SQL service_detail surfacing (CLOUD-03 / WR-22)

- **D-17 (locked):** `quirk/scanner/gcp_connector.py::_scan_cloud_sql` (lines 262-272) — Cloud SQL `description` field currently goes only into `cloud_scan_json`. Surface it to `service_detail` (the top-level finding field consumed by reports) following the same pattern Phase 69 BLOCK-02 used for severity routing. Researcher confirms the field name `service_detail` matches the schema.

### Cache _read_json malformed JSON handling (CLOUD-04 / WR-15)

- **D-18 (locked):** `quirk/engine/cache.py::_read_json` (lines 27-29, 56-63) — wrap `json.loads(...)` in `try: ... except (json.JSONDecodeError, UnicodeDecodeError) as e: logger.warning("Cache file %s corrupt — ignoring: %s", path, e); return None`. Returning `None` means the cache miss path runs normally; the corrupt file is left on disk (do NOT delete — preserves forensics). Researcher to check whether downstream code handles `None` cleanly; if not, return `{}` instead.

### Cache scope_hash connector flags (CLOUD-04 / WR-16)

- **D-19 (locked):** `quirk/engine/cache.py::scope_hash` (lines 32-47) — currently hashes only `targets` and `scan` cfg. Add `connectors` to the hash input. Spec: `hash_input = json.dumps({"targets": ..., "scan": ..., "connectors": dataclasses.asdict(cfg.connectors)}, sort_keys=True)`. Toggling `enable_email`/`enable_broker`/etc. now invalidates the cache as expected.

### DB connector password default (CLOUD-05 / WR-07)

- **D-20 (locked):** `quirk/scanner/db_connector.py:88-95, 213-220` — `psycopg2.connect(password=password or '')` silently submits an empty string when the password is None. Change to: if `password is None`, omit the `password` kwarg entirely (let libpq read from `.pgpass` / `PGPASSWORD`). If `password == ""` and not None, that's a deliberate empty-password attempt — pass it through but log at INFO.

### DB connector exception host strip (CLOUD-05 / WR-08)

- **D-21 (locked):** `quirk/scanner/db_connector.py:158-167` — apply the `quirk/util/safe_exc.py::safe_str` helper (the Phase 59 / LEAK-01 pattern) to the exception message before logging or storing in `scan_error`. The helper strips host/port/credential fragments. Researcher confirms safe_exc exists post-Phase 59 and is the canonical sink.

### vault_connector VAULT_TOKEN env order (CLOUD-05 / WR-09)

- **D-22 (locked):** `quirk/scanner/vault_connector.py` — when caller passes `token=None`, do NOT silently fall back to `os.environ["VAULT_TOKEN"]`. Either: (a) require the caller to pass the env value explicitly (preferred — keeps the connector pure), or (b) document the env fallback as the documented contract. Locked: option (a) — caller is responsible; raise `ValueError("vault_connector requires explicit token; pass os.environ.get('VAULT_TOKEN') if env fallback intended")` when token is None.

### Vault _scan_pki_mounts PEM split hardening (CLOUD-05 / WR-18)

- **D-23 (locked):** `quirk/scanner/vault_connector.py:277-282` — replace the naive `.split("-----BEGIN CERTIFICATE-----")` heuristic with `cryptography.x509.load_pem_x509_certificates(pem_bytes)` (plural form, available in `cryptography>=36`). Project already depends on `cryptography`; researcher to confirm version pin. Falls back to single-cert `load_pem_x509_certificate` if plural form is unavailable, but log a warning recommending dependency bump.

### evaluate_endpoints _postprocess_findings safe iteration (CLOUD-05 / WR-23)

- **D-24 (locked):** `quirk/engine/risk_engine.py::_postprocess_findings` (lines 335-371; will be in `findings_evaluator.py` post-D-05) — currently mutates `findings` (extends/removes) during iteration. Refactor to: iterate over `tuple(findings)` for the read pass; accumulate adds/removes in separate lists; apply mutations after the iteration completes. Mirrors the Python idiom `for x in list(d):` for mutation-safe traversal.

### Phase-72 do-not-touch list

- **D-25 (locked):** Explicitly out of scope for Phase 72:
  - `quirk/scanner/aws_connector.py` lines beyond those named in WR-01/02/13/14/19 — no incidental cleanup
  - `quirk/engine/risk_engine.py` (now `findings_evaluator.py`) sort logic outside `_dedupe_findings` and `_postprocess_findings` — no algorithm changes
  - `quirk/engine/cache.py` cache eviction / TTL logic — only `_read_json` and `scope_hash` per WR-15/16
  - Schema changes to finding rows — D-15 fixes `dat_scan_json` content, NOT the column shape
  - Any change to `quirk/intelligence/` — out of audit scope per WR-10
  - `migration_planner.py` — explicitly `wont-fix` per audit ledger

</decisions>

<canonical_refs>
## Canonical References (downstream agents MUST read)

- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — audit ledger; rows `scanners-cloud/WR-01..WR-24` are the source of truth. Rows must be flipped to `Phase 72 | [x] closed` with per-row evidence (mirrors Phase 71 / 70 / 69 pattern).
- `.planning/audit-2026-05-08/scanners-cloud/REVIEW.md` — detailed audit review with exact file:line citations for each WR row.
- `.planning/REQUIREMENTS.md` lines 34–38 — `CLOUD-01..CLOUD-05` requirement statements; one-to-many mapping to WR rows.
- `.planning/ROADMAP.md` Phase 72 section — Goal + 5 Success Criteria — these are gating, not aspirational.
- `.planning/phases/71-protocol-scanner-warnings/71-CONTEXT.md` — Phase 71 precedent for the audit-row-flip pattern, the fail-loud bound style (D-01 mirrors PROTO-05 D-01), do-not-touch discipline (D-25 mirrors Phase 71 D-15).
- `.planning/phases/69-deferred-blockers-scanner-cloud/` — Phase 69 BLOCKER closures in the same subsystem; precedent for `service_detail` routing (D-17), severity normalization, and the safe_exc.py pattern (D-21).
- `quirk/scanner/aws_connector.py` — WR-01, WR-02, WR-13, WR-14, WR-19 sites.
- `quirk/scanner/azure_connector.py:50-56` — WR-03 site.
- `quirk/scanner/gcp_connector.py:131-224, 174-180, 262-272` — WR-04, WR-05, WR-22 sites.
- `quirk/scanner/k8s_connector.py:136-156, 286-288, 344-352` — WR-06, WR-17, WR-20 sites.
- `quirk/scanner/db_connector.py:88-95, 158-167, 213-220` — WR-07, WR-08 sites.
- `quirk/scanner/vault_connector.py:277-282` — WR-09, WR-18 sites.
- `quirk/engine/cache.py:27-63` — WR-15, WR-16 sites.
- `quirk/engine/profiles.py:110-153` — WR-11, WR-12, WR-21 sites.
- `quirk/engine/risk_engine.py:312-371` — WR-10 (rename target), WR-23, WR-24 sites.
- `quirk/util/safe_exc.py` — Phase 59 helper for D-21 application.
- `quirk/config.py:377` — `conn_raw` build site for D-02 raw-YAML key tracking.

</canonical_refs>

<code_context>
## Reusable Assets / Patterns (from codebase scout)

- **`_set_if_default(name, value, default=X)` helper** (`quirk/engine/profiles.py`) — already established for the standard/deep profile mutation guard. D-03 uses it directly; D-02 extends the same intent to user-explicit detection.
- **`safe_str(exc)` from `quirk/util/safe_exc.py`** (Phase 59 LEAK-01) — module-level helper that strips host/port/credential fragments from exception text. Single source of truth for D-21. AST-gate test in `tests/test_safe_exc_gate.py` ensures all connector exception paths route through it.
- **`as_completed` + per-future `.exception()` pattern** (Phase 64 email_scanner refactor) — canonical replacement for silent-swallow `executor.map`. D-09 (WR-13) copies this idiom.
- **`cryptography.x509.load_pem_x509_certificates` (plural)** — multi-cert PEM parser; replaces naive string splits. D-23 uses this. Researcher confirms `cryptography>=36` is pinned in `pyproject.toml`.
- **dataclass sidecar attrs via `dataclasses.field(default_factory=..., repr=False, compare=False)`** — standard Python dataclass idiom for tracking metadata without polluting equality/repr. D-02's `_user_set_fields` uses this shape.
- **Phase 69 BLOCK-02 severity routing** — established the `service_detail` field as the canonical surface for human-readable detail strings. D-17 (WR-22) follows the same precedent for Cloud SQL description.

</code_context>

<test_strategy>
## Test Approach (high-level — planner refines)

- **One test module per CLOUD-NN requirement** (5 modules) — mirrors Phase 71/70 plan-per-requirement granularity. Each module covers all WR rows under that requirement.
- **RED-then-GREEN per fix** — every guard / clamp / narrowing gets at least one test that proves the failing input is now handled. For D-01 (GCP pagination cap), include a parametrized test of `MAX_KMS_PAGES + 1` iterations triggering `ValueError`.
- **Defense-in-depth assertions** — D-04 (`_dedupe_findings` sort) requires a golden-file test where two findings differ ONLY in `recommendation` text but produce identical dedup output ordering.
- **Snapshot regeneration commit** — D-04 changes golden-file ordering across the project. Plan must include a dedicated commit `chore(72-snapshots): regen goldens for _dedupe_findings sort key change (D-04)` separate from the code-change commit, so the diff is auditable.
- **Audit ledger flip** verified by integration: a test or docs-update commit that asserts all 24 WR-NN rows show `Phase 72 | [x] closed` in `AUDIT-TASKS.md` (Phase 71/70 precedent).
- **Cache invalidation test** for D-19 (`scope_hash`) — flip `enable_email` and assert `scope_hash` value differs.
- **No new UAT-NN-NN cases needed** — these are internal contracts. Follow Phase 71 wrap pattern: prepend a "Phase 72 wrap" note to `docs/UAT-SERIES.md` `Last Updated:` preamble describing the contract changes (cache invalidation on connector flags, _dedupe order change, risk_engine→findings_evaluator rename).

</test_strategy>

<deferred>
## Deferred Ideas (noted, not in scope)

- **migration_planner.py implementation** (`scanners-cloud/CR-01`) — `wont-fix` per audit ledger; the real migration planner is in the QRAMM phase. Out of scope.
- **K8s scan_k8s_targets None credential handling** (`scanners-cloud/CR-03`) — deferred to a v4.9 follow-up phase per audit ledger.
- **DeprecationWarning at import of `quirk.engine.risk_engine`** — defer to v5.0 cycle when the shim is removed; adding the warning now would create noise across existing imports.
- **Promotion of `severity_rank` dict to a public helper** (D-04a) — defer until a second caller appears.
- **Full split of findings_evaluator vs. scorer** (WR-10 alternative) — out of scope for a WARNING-cluster phase; revisit in v5.0 if intelligence/scoring is restructured.
- **Wizard prompt for cache scope-hash debug** — operators have no current need; cache invalidation behavior is now correct (D-19).

</deferred>
