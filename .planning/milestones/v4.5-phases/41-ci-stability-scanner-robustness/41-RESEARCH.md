# Phase 41: CI Stability & Scanner Robustness — Research

**Researched:** 2026-04-29
**Domain:** pytest infrastructure, Python exception handling, TOML config patterns
**Confidence:** HIGH (all findings verified directly from codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Pragmatic skip policy. Stale skips deleted; optional-extra and live-infra skips kept.
- **D-02:** Single `tests/skip_registry.py` (or equivalent in `conftest.py`) registering every acceptable skip with `{file:line, category ∈ {optional_extra, live_infra}, reason}`.
- **D-03:** CI gate meta-test that fails when an unregistered `pytest.skip` / `importorskip` / `@skipif` is encountered.
- **D-04:** Initial deletion targets (must re-verify during planning): `tests/conftest.py:111`, 6× `@skipif(not _HAS_GCP_MODULE)` in `tests/test_cloud_connectors.py`, `tests/test_broker_db_schema.py:70`.
- **D-05:** `pytest.importorskip("quirk.scanner.broker_scanner")` in broker tests stays — broker_scanner is in `[motion]`.
- **D-06:** Canonical timeout policy lives in `quirk/config.py` as a `[scan.timeouts]` TOML sub-table. Per-scanner overrides: `[scan.timeouts.tls]`, `[scan.timeouts.ssh]`, `[scan.timeouts.fingerprint]`, etc.
- **D-07:** Four divergent fields migrate into the sub-table; old names become deprecation aliases (warn-on-read). Not removed in this phase.
- **D-08:** Scanners read timeout slots read-only. `run_scan.py` MUST NOT mutate `cfg.scan.*` around scanner phases. Dissolves BACK-45.
- **D-09:** Retry/backoff defaults live in `[scan.retry]`: `retry_count`, `backoff_base_seconds`, `backoff_max_seconds`. ROBUST-04 audit doc is a markdown table.
- **D-10:** Overall scan upper-bound formula documented in `docs/configuration.md`.
- **D-11:** `scan_errors[]` entries use minimal schema: `{scanner, target, reason, category}` where `category ∈ {missing_extra, timeout, exception, config}`.
- **D-12:** Missing extras emit a `scan_errors[]` entry AND a stderr advisory: `[advisory] scanner=<name> extra=<group> not installed — run \`pip install quirk[<group>]\` to enable`.
- **D-13:** CLI exit code `0` for any combination of `missing_extra`/`timeout`/handled `exception` entries; non-zero only for unhandled crashes.
- **D-14:** Every scanner entrypoint runs inside `try/except BaseException`; re-raise only `KeyboardInterrupt`/`SystemExit`; all others → `scan_errors[]` entry + `category="exception"` + scan continues.
- **D-15:** `scan_errors[]` category field must be respected so trends.py delta reports don't conflate "regression crash" with "missing extra".
- **D-16:** Any test consistently >1s gets `@pytest.mark.slow`. Default `pytest` invocation excludes `slow` and must finish in <60s.
- **D-17:** Phase 41 scope is **local pytest only**. `.github/workflows/*` NOT modified.
- **D-18:** `lab.sh` down arm: `compose down` → `compose --profile "*" down --remove-orphans`.

### Claude's Discretion

- Exact filename/location of skip registry (`tests/skip_registry.py` vs entry in `conftest.py`).
- Exact mechanism of unregistered-skip CI gate (pytest plugin vs collection hook vs sentinel meta-test).
- Per-scanner default timeout values inside the new sub-table (use more conservative value when divergent).
- Whether `try/except BaseException` wrapper lives in `run_scan.py` or as a decorator on each scanner.

### Deferred Ideas (OUT OF SCOPE)

- Dashboard "Scan Issues" widget — Phase 43.
- GitHub Actions CI YAML tuning — future phase.
- Single-bundled wheel removing `[motion]` optionality.
- Deprecation removal of legacy `*_timeout_seconds` fields.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CI-01 | Zero skip/xfail markers on tests deferred for code reasons | Skip-marker triage table identifies all 3 deletion targets; 13 live-infra/optional-extra skips confirmed as legitimate keeps |
| CI-02 | Deterministic test suite — no order-dependent or global-state tests | No time.sleep in unit tests found; subprocess tests are candidates for slow-marking |
| CI-03 | Long-running tests marked `@pytest.mark.slow`; default run <60s | Slow-test candidate list below; no pytest.ini `slow` marker registered yet |
| ROBUST-01 | Missing optional extra → advisory + scan completes | `broker_scanner` is the only runtime-missing-extra path today; email_scanner also optional | 
| ROBUST-02 | Per-scanner timeout respected; overall scan has documented upper bound | cfg.scan mutation map shows TLS+SSH phases actively mutate shared fields today; D-08 fixes this |
| ROBUST-03 | Unexpected exception → `scan_errors[]` entry; scan continues | No existing `try/except BaseException` wrapper in run_scan.py; must be added |
| ROBUST-04 | Timeout/retry policy consistent and documented | Four divergent timeout fields confirmed; retry not yet defined anywhere |
</phase_requirements>

---

## Skip-Marker Triage Table (D-01..D-05)

All `pytest.skip`, `pytest.importorskip`, and `@pytest.mark.skipif` occurrences in `tests/`:

| File | Line | Marker Text | Verdict | Rationale |
|------|------|-------------|---------|-----------|
| `tests/conftest.py` | 111 | `pytest.skip("quirk.dashboard not yet implemented")` | **delete_now** | `quirk/dashboard/` exists; dashboard imports succeed; this skip is stale |
| `tests/test_cloud_connectors.py` | 154 | `@pytest.mark.skipif(not _HAS_GCP_MODULE, reason="gcp_connector.py not yet created")` | **delete_now** | `quirk/scanner/gcp_connector.py` exists; `_HAS_GCP_MODULE` is always `True` in a full install |
| `tests/test_cloud_connectors.py` | 162 | same pattern | **delete_now** | same |
| `tests/test_cloud_connectors.py` | 179 | same pattern | **delete_now** | same |
| `tests/test_cloud_connectors.py` | 232 | same pattern | **delete_now** | same |
| `tests/test_cloud_connectors.py` | 256 | same pattern | **delete_now** | same |
| `tests/test_cloud_connectors.py` | 280 | same pattern | **delete_now** | same |
| `tests/test_cloud_connectors.py` | 303 | same pattern | **delete_now** | same |
| `tests/test_cloud_connectors.py` | 327 | same pattern | **delete_now** | same |
| `tests/test_cloud_connectors.py` | 360 | same pattern | **delete_now** | same (9 total `@skipif(not _HAS_GCP_MODULE)` decorators) |
| `tests/test_broker_db_schema.py` | 70 | `pytest.skip("Column already present via Base.metadata; idempotency covered by test_init_db_twice_no_error")` | **delete_now** | This is a runtime skip inside test body; the skip fires unconditionally because `Base.metadata.create_all` always includes the column. The test never exercises the migration path. Idempotency is covered by sibling test as noted. Safe to remove the entire test or convert to an assertion. |
| `tests/test_broker_scanner_rabbitmq.py` | 13 | `pytest.importorskip("quirk.scanner.broker_scanner", reason="Phase 33 Plan 04")` | **optional_extra** | D-05: broker_scanner is `[motion]`; keep |
| `tests/test_broker_scanner_kafka.py` | 12 | `pytest.importorskip("quirk.scanner.broker_scanner", reason="Phase 33 Plan 03")` | **optional_extra** | D-05: keep |
| `tests/test_broker_scanner_redis.py` | 13 | `pytest.importorskip("quirk.scanner.broker_scanner", reason="Phase 33 Plan 05")` | **optional_extra** | D-05: keep |
| `tests/test_email_scanner.py` | 81–84 | `_skip_scanner = pytest.mark.skipif(not _EMAIL_SCANNER_AVAILABLE, ...)` applied to 16 tests | **delete_now** | `quirk/scanner/email_scanner.py` exists and imports succeed; `_EMAIL_SCANNER_AVAILABLE` is always `True`; all 16 `@_skip_scanner` decorators should be removed |
| `tests/test_chaos_storage.py` | 41 | `@pytest.mark.skipif(not os.environ.get("QUIRK_RUN_DOCKER_IT"), ...)` | **live_infra** | Requires Docker + MinIO; keep, register in skip registry |
| `tests/test_chaos_storage.py` | 67 | same env-var guard | **live_infra** | keep |
| `tests/test_dnssec_scanner.py` | 475 | `@pytest.mark.skipif(not os.environ.get("QUIRK_INTEGRATION_TESTS"), ...)` | **live_infra** | Requires chaos lab BIND9; keep, register |
| `tests/test_saml_scanner.py` | 366 | `@pytest.mark.skipif(not os.environ.get("QUIRK_INTEGRATION_TESTS"), ...)` | **live_infra** | Requires SimpleSAMLphp chaos lab; keep, register |
| `tests/test_kerberos_scanner.py` | 360 | `@pytest.mark.skipif(not os.environ.get("QUIRK_KERBEROS_INTEGRATION"), ...)` | **live_infra** | Requires Samba DC chaos lab; keep, register |
| `tests/test_cbom_motion_golden.py` | 189 | `@pytest.mark.skipif(os.environ.get("REGEN_CBOM_FIXTURES") != "1", ...)` | **live_infra** | Fixture regeneration guard; keep, register |
| `tests/test_version.py` | 32 | `pytest.skip(f"CLI --version not invokable: {exc}")` | **unclear** | Fires only when subprocess fails. Probably should be `pytest.fail`. Not a code-reason skip — defensive skip on environment failure. Planner decision: convert to `pytest.fail` or keep as live-infra. |
| `tests/test_version.py` | 34 | `pytest.skip("CLI --version returned non-zero")` | **unclear** | Same: only fires when CLI is broken. Convert to assertion. |

**D-04 confirmation:**
- `tests/conftest.py:111` — DELETE (dashboard exists) [VERIFIED]
- `tests/test_cloud_connectors.py` 9× `@skipif(not _HAS_GCP_MODULE)` — DELETE (`gcp_connector.py` exists, `_HAS_GCP_MODULE = True` in full install) [VERIFIED]
- `tests/test_broker_db_schema.py:70` — DELETE (runtime skip that always fires, idempotency covered elsewhere) [VERIFIED]

**Additional deletion target not in D-04:** `tests/test_email_scanner.py` `_skip_scanner` pattern on 16 tests — `email_scanner.py` exists [VERIFIED].

**Skip registry membership (13 entries for `live_infra`/`optional_extra`):**

| Category | File | Tests Covered |
|----------|------|---------------|
| optional_extra | test_broker_scanner_rabbitmq.py | all (via module-level importorskip) |
| optional_extra | test_broker_scanner_kafka.py | all |
| optional_extra | test_broker_scanner_redis.py | all |
| live_infra | test_chaos_storage.py:41 | test_minio_unencrypted_bucket_produces_high_finding |
| live_infra | test_chaos_storage.py:67 | test_minio_encrypted_bucket_no_finding |
| live_infra | test_dnssec_scanner.py:475 | test_chaos_lab_integration |
| live_infra | test_saml_scanner.py:366 | test_chaos_lab_integration |
| live_infra | test_kerberos_scanner.py:360 | test_samba_dc_integration |
| live_infra | test_cbom_motion_golden.py:189 | test_generate_fixtures |

---

## Scanner Inventory (D-06..D-09, D-14)

Full 21-scanner table. "Entrypoint" = the public function called from `run_scan.py`. "Timeout param" = how the scanner currently receives a timeout value. "Optional extra" = which `[project.optional-dependencies]` group gates it.

| # | File | Entrypoint (public) | Timeout Source Today | Optional Extra | Notes |
|---|------|---------------------|---------------------|----------------|-------|
| 1 | `scanner/fingerprint.py` | `fingerprint_service()` | `fp_timeout` local var in run_scan.py:312 (reads `cfg.scan.fingerprint_timeout_seconds`) | — | Not exposed directly; called via `_fp_task` |
| 2 | `scanner/tls_scanner.py` | `scan_tls_targets()` | `cfg.scan.timeout_seconds` (after mutation: run_scan.py:417) | — | D-08 target: mutation at line 417 |
| 3 | `scanner/ssh_scanner.py` | `scan_ssh_targets()` | `cfg.scan.timeout_seconds` (after mutation: run_scan.py:444-445) | — | D-08 target: mutation at lines 444-445 |
| 4 | `scanner/jwt_scanner.py` | `scan_jwt_targets()` | `timeout=cfg.scan.timeout_seconds` (run_scan.py:469) | — | Passes timeout as positional arg |
| 5 | `scanner/container_scanner.py` | `scan_container_targets()` | `timeout=cfg.scan.timeout_seconds` (run_scan.py:481) | — | Default timeout=120 in function sig |
| 6 | `scanner/source_scanner.py` | `scan_source_targets()` | `timeout=cfg.scan.timeout_seconds` (run_scan.py:493) | — | Default timeout=300 in function sig |
| 7 | `scanner/aws_connector.py` | `scan_aws_targets()` | no timeout param (uses boto3 default) | `[cloud]` (boto3 is a core dep) | No timeout slot needed |
| 8 | `scanner/azure_connector.py` | `scan_azure_targets()` | no timeout param | `[cloud]` | No timeout slot needed |
| 9 | `scanner/gcp_connector.py` | `scan_gcp_targets()` | no timeout param | `[cloud]` | No timeout slot needed |
| 10 | `scanner/db_connector.py` | `scan_pg_targets()`, `scan_mysql_targets()` | hardcoded `connect_timeout=5` (lines 87, 206) | `[db]` | Two entrypoints; hardcoded timeout not from cfg |
| 11 | `scanner/k8s_connector.py` | `scan_k8s_targets()` | no timeout param | `[cloud]` | No timeout slot needed |
| 12 | `scanner/vault_connector.py` | `scan_vault_targets()` | hardcoded `timeout=10` at line 413 | `[cloud]` (hvac) | Not from cfg |
| 13 | `scanner/dnssec_scanner.py` | `scan_dnssec_targets()` | `timeout=getattr(cfg.connectors, "dnssec_timeout", 10)` (run_scan.py:658) | — | Uses connectors cfg not scan cfg |
| 14 | `scanner/saml_scanner.py` | `scan_saml_targets()` | `timeout=getattr(cfg.connectors, "saml_timeout", 10)` (run_scan.py:672) | — | Uses connectors cfg not scan cfg |
| 15 | `scanner/kerberos_scanner.py` | `scan_kerberos_targets()` | `timeout=getattr(cfg.connectors, "kerberos_timeout", 10)` (run_scan.py:686) | — | Uses connectors cfg not scan cfg |
| 16 | `scanner/email_scanner.py` | `scan_email_targets()` | `timeout=cfg.scan.timeout_seconds` (run_scan.py:727) | `[email]` (sub-dep of `[motion]`) | email_scanner exists — importorskip in tests is stale |
| 17 | `scanner/broker_scanner.py` (kafka) | `scan_kafka_targets()` | `timeout=cfg.scan.timeout_seconds` (run_scan.py:743) | `[motion]`/`[broker]`/`[kafka]` | **Also bug at run_scan.py:743: passes `profile=cfg.scan.profile` but `ScanCfg` has NO `profile` attribute** |
| 18 | `scanner/broker_scanner.py` (rabbitmq) | `scan_rabbitmq_targets()` | `timeout=cfg.scan.timeout_seconds` (run_scan.py:752) | `[motion]`/`[broker]` | |
| 19 | `scanner/broker_scanner.py` (redis) | `scan_redis_targets()` | `timeout=cfg.scan.timeout_seconds` (run_scan.py:757) | `[motion]`/`[broker]`/`[redis]` | |
| 20 | `scanner/target_expander.py` | `expand_targets()` | no timeout | — | Discovery helper, not a scanner |
| 21 | `discovery/tls_scanner.py` | (internal; not called from run_scan.py main path) | `cfg.scan.timeout_seconds` | — | Legacy discovery scanner; still reads cfg.scan |

**Bug found at run_scan.py:743:** `profile=cfg.scan.profile` — `ScanCfg` dataclass has no `profile` attribute. This will raise `AttributeError` at runtime when `enable_broker=True`. Planner must address this in the same wave as D-08 cleanup.

**D-14 wrapper surface:** All 19 callable scanner entrypoints in `run_scan.py` are already inside `with _phase_timer(...)` blocks. The `try/except BaseException` wrapper can be added either:
- (a) Around each `_phase_timer` block in `run_scan.py` (centralised, single file change), or  
- (b) As a decorator in each scanner module.

Option (a) is lower-friction per the established pattern.

---

## cfg.scan Mutation Map (D-08)

Every assignment to a `cfg.scan.*` attribute in the codebase (excluding `apply_profile` which is intentional pre-scan setup):

| File | Lines | Attribute(s) Mutated | Context |
|------|-------|---------------------|---------|
| `run_scan.py` | 414–417 | `cfg.scan.timeout_seconds`, `cfg.scan.concurrency` | TLS phase setup (BEFORE `scan_tls_targets` call) |
| `run_scan.py` | 433–434 | `cfg.scan.timeout_seconds`, `cfg.scan.concurrency` | TLS phase teardown in `finally:` block (restores base values) |
| `run_scan.py` | 444–445 | `cfg.scan.timeout_seconds`, `cfg.scan.concurrency` | SSH phase setup (BEFORE `scan_ssh_targets` call) |
| `run_scan.py` | 458–459 | `cfg.scan.timeout_seconds`, `cfg.scan.concurrency` | SSH phase teardown in `finally:` block (restores base values) |
| `quirk/engine/profiles.py` | multiple | `fingerprint_timeout_seconds`, `fingerprint_concurrency`, `tls_timeout_seconds`, `tls_concurrency`, `ssh_timeout_seconds`, `ssh_concurrency`, `tls_enum_mode` | Called once pre-scan via `apply_profile()` — this is **intentional config initialisation**, NOT the BACK-45 problem |

**BACK-45 pattern (the problem):** `run_scan.py:414-434` and `run_scan.py:444-459` are the BACK-45 mutation sites. The `try/finally` exists precisely because the mutation is unsafe — this is the guard that D-08 eliminates.

**D-08 fix:** Pass timeout/concurrency as explicit kwargs to `scan_tls_targets()` and `scan_ssh_targets()`, reading from `cfg.scan.tls_timeout_seconds` / `cfg.scan.ssh_timeout_seconds` directly. Remove the 4 assignment lines and both `finally:` blocks. The `base_timeout` / `base_conc` variables also become unused.

**Also note:** `quirk/engine/profiles.py` calls `setattr(scan, ...)` broadly — this is pre-scan initialisation and is NOT the BACK-45 pattern. Do not modify profiles.py under D-08.

---

## scan_errors[] Producer/Consumer Map (D-11, D-15)

### Current data model

`scan_errors[]` does NOT exist as a standalone list today. The equivalent is `CryptoEndpoint.scan_error` — a nullable `Text` column on the `crypto_endpoints` table (defined at `quirk/models.py:35`).

`trends.py` counts scan errors by counting endpoints where `ep.scan_error is not None` (lines 232–257).

**D-11 adds a new concept:** a structured `scan_errors[]` list (separate from the per-endpoint `.scan_error` field). The planner must decide the data container:
- Option A: New `ScanError` dataclass / namedtuple accumulated in `run_scan.py`, passed to `write_reports` and persisted to a new `scan_errors` table.
- Option B: Augment existing `CryptoEndpoint.scan_error` field with structured JSON matching `{scanner, target, reason, category}`.

Given D-15 says `trends.py` consumes it and D-11 says "category field", the cleanest path is to **add a `scan_error_category` column to `CryptoEndpoint`** and populate it alongside `scan_error`. This avoids a new table and preserves the existing trends.py counting logic.

### Producers (where `.scan_error` is currently written)

| File | Line(s) | Context |
|------|---------|---------|
| `run_scan.py` | 367–368 | Fingerprint CLOSED ports: `ep.scan_error = f"{proto}: {detail}"` |
| (each scanner) | varies | Scanners set `ep.scan_error = ...` internally when connection fails |

### Consumers

| File | Lines | What It Does |
|------|-------|--------------|
| `quirk/intelligence/trends.py` | 232–259 | Counts `ep.scan_error is not None` for `cur_err` / `prev_err`; computes `scan_errors_new_count` / `scan_errors_resolved_count` |
| `quirk/dashboard/api/schemas.py` | 222–223 | `scan_errors_new_count: int = 0`, `scan_errors_resolved_count: int = 0` in Pydantic schema |
| `quirk/dashboard/api/routes/trends.py` | 97–98 | Passes counts through to API response |

### D-15 impact

The new `category` field must NOT cause trends.py to conflate `missing_extra` (expected, no alarm) with `exception` (regression). The current logic counts all `scan_error is not None` uniformly.

**Minimal fix:** Add an exclusion filter in `trends.py` to exclude `category="missing_extra"` from error counts. This way `scan_errors_new_count` only fires for `timeout`/`exception`/`config`.

### `category` field existence

**Does not exist today.** `CryptoEndpoint` has only `scan_error TEXT` (nullable). The `category` field is genuinely additive. [VERIFIED from `quirk/models.py`]

---

## Slow-Test Candidates (D-16)

Heuristic: tests using `subprocess.run` (live process spawn), real network sockets, or identified as live-infra tests.

| File | Test(s) | Why Slow | Action |
|------|---------|----------|--------|
| `tests/test_version.py` | `test_cli_version_subprocess` | Spawns `python -m run_scan --version` subprocess | `@pytest.mark.slow` |
| `tests/test_cli_init.py` | all (3 tests) | Spawns `quirk init` subprocess 2–3 times | `@pytest.mark.slow` |
| `tests/test_cli_version.py` | `test_cli_version` | Spawns subprocess | `@pytest.mark.slow` |
| `tests/test_chaos_storage.py` | `test_minio_*` (2 tests) | Live Docker+network (already skipif'd behind env var) | Already gated; also add `@pytest.mark.slow` |
| `tests/test_dnssec_scanner.py` | `test_chaos_lab_integration` | Live chaos lab | Already gated; also add `@pytest.mark.slow` |
| `tests/test_saml_scanner.py` | `test_chaos_lab_integration` | Live chaos lab | Already gated; also add `@pytest.mark.slow` |
| `tests/test_kerberos_scanner.py` | `test_samba_dc_integration` | Live chaos lab | Already gated; also add `@pytest.mark.slow` |
| `tests/test_cbom_motion_golden.py` | `test_generate_fixtures` | Fixture regeneration; env-gated | Already gated; also add `@pytest.mark.slow` |

**No `[tool.pytest.ini_options]` section in `pyproject.toml` today.** The `slow` marker is unregistered. Wave 0 must add:

```toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow (deselect with '-m not slow')",
    "integration: marks tests requiring live infrastructure",
]
addopts = "-m 'not slow'"
```

The `addopts = "-m 'not slow'"` line makes the exclusion automatic on bare `pytest` invocations (D-16 requirement).

---

## lab.sh Down-Arm Diff (D-18)

**Current code (`quantum-chaos-enterprise-lab/lab.sh:97-101`):**

```bash
  down)
    echo "🧯 Stopping lab: project=${PROJECT_NAME}"
    compose down
    echo "✅ Lab stopped."
    ;;
```

**Proposed replacement:**

```bash
  down)
    echo "🧯 Stopping lab: project=${PROJECT_NAME}"
    compose --profile "*" down --remove-orphans
    echo "✅ Lab stopped."
    ;;
```

**Why:** `compose down` without `--profile "*"` leaves containers from named profiles running (profile-tagged services are only managed when the matching profile flag is present). The `--remove-orphans` flag cleans up any containers not defined in the current compose file.

**Other call sites:** `reset` arm at line 104 also calls `compose down -v` without profile flag:

```bash
  reset)
    echo "♻️ Resetting lab (down -v + up -d): project=${PROJECT_NAME}"
    compose down -v
    compose up -d
```

This has the same profile-sweep gap. Planner should fix both: `compose --profile "*" down -v --remove-orphans` for reset. [VERIFIED from `lab.sh:97-108`]

---

## Proposed [scan.timeouts] / [scan.retry] Shape (D-06..D-10)

### Current divergent fields in `ScanCfg` (all four confirmed)

| Field | Default in ScanCfg | Default in profiles.py (standard) | Purpose |
|-------|-------------------|----------------------------------|---------|
| `timeout_seconds` | `int` (required) | 5 | Global / fallback |
| `fingerprint_timeout_seconds` | `int = 2` | 4 (overrides ScanCfg default) | Fingerprint phase |
| `tls_timeout_seconds` | `int = 5` | 6 (overrides ScanCfg default) | TLS scan phase |
| `ssh_timeout_seconds` | `int = 5` | 6 (overrides ScanCfg default) | SSH scan phase |

Note: `profiles.py` _overrides_ ScanCfg defaults silently via `_set_if_default`. The effective defaults after profile application differ from ScanCfg field defaults.

### Proposed TOML shape

```toml
[scan.timeouts]
default_seconds = 5          # was: timeout_seconds (global fallback)
fingerprint_seconds = 4      # was: fingerprint_timeout_seconds
tls_seconds = 6              # was: tls_timeout_seconds (effective post-profile)
ssh_seconds = 6              # was: ssh_timeout_seconds (effective post-profile)
jwt_seconds = 10             # new explicit slot (currently uses default)
container_seconds = 120      # new explicit slot (scanner default)
source_seconds = 300         # new explicit slot (scanner default)
dnssec_seconds = 10          # new (currently in connectors via getattr)
saml_seconds = 10            # new (currently in connectors via getattr)
kerberos_seconds = 10        # new (currently in connectors via getattr)
vault_seconds = 10           # new (currently hardcoded in vault_connector.py:413)
db_connect_seconds = 5       # new (currently hardcoded in db_connector.py:87,206)
broker_seconds = 10          # new explicit slot (broker_scanner default)
email_seconds = 10           # new explicit slot (email_scanner default)

[scan.retry]
retry_count = 0              # default: no retry
backoff_base_seconds = 1.0
backoff_max_seconds = 5.0
```

### Deprecation-alias pattern (D-07)

In `config.py`, after loading `[scan.timeouts]` sub-table, expose the old field names as properties with a deprecation warning:

```python
@property
def timeout_seconds(self):
    import warnings
    warnings.warn(
        "cfg.scan.timeout_seconds is deprecated; use cfg.scan.timeouts.default_seconds",
        DeprecationWarning, stacklevel=2,
    )
    return self.timeouts.default_seconds
```

Repeat for `fingerprint_timeout_seconds`, `tls_timeout_seconds`, `ssh_timeout_seconds`.

### Config loading pattern (existing pattern in `config.py`)

`config.py` currently uses `ScanCfg(**raw["scan"])` — a direct dataclass unpack from YAML dict. For sub-tables, the planner needs to add a `TimeoutsCfg` and `RetryCfg` dataclass, then parse `raw["scan"].get("timeouts", {})` and `raw["scan"].get("retry", {})` separately, injecting them as nested dataclass instances.

This is a **breaking change to `config.yaml` schema** for any user who relies on the flat `scan:` block. Backward compatibility requires the loader to check for both the new sub-table and the old flat keys.

### Upper-bound formula (D-10)

To document in `docs/configuration.md`:

```
scan_upper_bound = (
  fingerprint_timeout * N_targets
  + tls_timeout * N_tls_candidates
  + ssh_timeout * N_ssh_candidates
  + max(jwt_timeout, container_timeout, source_timeout, ...) * N_connector_targets
) + 10s safety_margin
```

Where N values depend on target scope. Conservative single-host estimate: `4 + 6 + 6 + 10 + 10 = 36s` plus safety = ~46s. Well under the 60s CI budget for unit/integration tests.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (version in `pyproject.toml` dev deps, not listed — standard install) |
| Config file | None today — Wave 0 creates `[tool.pytest.ini_options]` in `pyproject.toml` |
| Quick run command | `pytest -m "not slow" tests/` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CI-01 | Zero stale skip markers in default run | meta-test (collection hook or sentinel) | `pytest tests/test_skip_registry.py -x` or hook runs on every `pytest` | Wave 0 — create `tests/test_skip_registry.py` |
| CI-01 | Unregistered skip triggers CI gate failure | meta-test | same | Wave 0 |
| CI-02 | No order-dependent tests | audit (manual + pytest-randomly) | `pytest --randomly-seed=random -m "not slow" tests/` | existing tests |
| CI-03 | Default run <60s | benchmark check | `time pytest -m "not slow" tests/` | existing tests + Wave 0 `pyproject.toml` edit |
| ROBUST-01 | Missing extra → advisory to stderr | unit test | `pytest tests/test_scan_robustness.py::test_missing_extra_advisory -x` | Wave 0 |
| ROBUST-01 | Missing extra → scan completes, exit 0 | unit test | `pytest tests/test_scan_robustness.py::test_missing_extra_exit_code -x` | Wave 0 |
| ROBUST-02 | Per-scanner timeout respected | unit test (mock socket timeout) | `pytest tests/test_scan_robustness.py::test_timeout_respected_* -x` | Wave 0 |
| ROBUST-02 | Overall scan upper-bound documented | documentation check (manual UAT) | UAT line in UAT-SERIES.md | docs |
| ROBUST-03 | Unexpected exception → scan_errors[] entry | unit test | `pytest tests/test_scan_robustness.py::test_exception_captured -x` | Wave 0 |
| ROBUST-03 | Scan continues after scanner exception | unit test | `pytest tests/test_scan_robustness.py::test_scan_continues_after_exception -x` | Wave 0 |
| ROBUST-04 | Timeout policy single source of truth | audit doc (markdown table) | manual: verify `docs/configuration.md` has table | docs |
| ROBUST-04 | Deprecation warning on old field names | unit test | `pytest tests/test_config.py::test_deprecated_timeout_fields -x` | add to existing `tests/test_config.py` if it exists, else Wave 0 |

### Wave 0 Gaps

- [ ] `pyproject.toml` — add `[tool.pytest.ini_options]` with `markers` and `addopts = "-m 'not slow'"`
- [ ] `tests/test_skip_registry.py` — or equivalent section in `conftest.py` — CI gate meta-test (CI-01)
- [ ] `tests/test_scan_robustness.py` — ROBUST-01, ROBUST-02, ROBUST-03 unit tests
- [ ] `tests/conftest.py` — skip registry data structure (D-02)

### Sampling Rate

- **Per task commit:** `pytest -m "not slow" tests/ -x --tb=short`
- **Per wave merge:** `pytest -m "not slow" tests/ --tb=short`
- **Phase gate:** `pytest tests/` (full suite including slow, gated by env vars for live-infra) before `/gsd-verify-work`

---

## Open Questions (RESOLVED)

> All 5 questions were resolved during planning. Resolutions are encoded in the Phase 41 plans (see 41-01 through 41-07). Bug-fix fold-in lives in Plan 03; ScanError storage decision is a new column on `CryptoEndpoint` per Plan 01; conftest.py:111 fixture conversion uses `pytest.importorskip` per Plan 05; lab.sh reset arm extension is in Plan 06; TimeoutsCfg ships as a TOML sub-table per D-06 in Plan 02.

1. **`cfg.scan.profile` AttributeError bug (run_scan.py:743)**
   - What we know: `scan_kafka_targets()` is called with `profile=cfg.scan.profile` but `ScanCfg` has no `profile` attribute; this will raise `AttributeError` whenever `enable_broker=True`.
   - What's unclear: Did a prior phase intend to add `profile` to `ScanCfg`? Or should run_scan.py pass `scan_profile` (the local variable at line 224) instead?
   - Recommendation: Pass `profile=scan_profile` (the argparse-derived string already in scope). Fix in D-08 cleanup wave.

2. **`scan_errors[]` as new list vs augmented `CryptoEndpoint` column**
   - What we know: D-11 specifies `{scanner, target, reason, category}` — no spec on storage layer. `trends.py` reads `ep.scan_error is not None` from `CryptoEndpoint` rows.
   - What's unclear: Does D-11 expect a new standalone list (returned from `run_scan.py`, not persisted) or a new DB column on `CryptoEndpoint`?
   - Recommendation: Add `scan_error_category TEXT` column to `CryptoEndpoint` (consistent with existing `scan_error` field) and a migration helper. Trends.py filtering on category is then a DB query filter.

3. **`conftest.py:111` fixture scope**
   - What we know: Line 111 is inside the `client` fixture (lines 75–111). Removing the skip means `create_app()` / `TestClient` must succeed; if the dashboard import fails for a different reason, the fixture would raise instead of skip.
   - What's unclear: Does removing the skip risk breaking non-dashboard tests if `[dashboard]` extras are absent?
   - Recommendation: The skip should be replaced with a proper `pytest.importorskip("quirk.dashboard")` at module level in dashboard test files, not in conftest. Or: keep `try/except ImportError` but convert to `pytest.fail` with a clear message.

4. **`reset` arm in lab.sh also missing profile sweep**
   - What we know: `lab.sh:104` calls `compose down -v` without `--profile "*"`.
   - What's unclear: D-18 specifically mentions lines 97-101 (down arm only). Does the user want reset fixed too?
   - Recommendation: Fix both down and reset arms in the same single-plan change. Flag in plan as "D-18 extension, trivially safe".

5. **`TimeoutsCfg` as nested dataclass vs flat `ScanCfg` extension**
   - What we know: `config.py` uses `ScanCfg(**raw["scan"])` — direct unpack. A nested sub-table breaks this.
   - What's unclear: Should `[scan.timeouts]` be a genuine TOML sub-table (nested dict in YAML) or just new flat keys in `[scan]` with a `timeouts_` prefix?
   - Recommendation: New nested dataclass `TimeoutsCfg` + `RetryCfg` stored as fields on `ScanCfg`; the YAML flat keys remain valid through the deprecation-alias properties. TOML sub-table is the canonical new format. This matches D-06 spec.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 41 is code/config/test changes with no new external dependencies.

---

## Sources

All findings are VERIFIED directly from the codebase. No external sources consulted.

- `quirk/config.py` — ScanCfg dataclass, four timeout fields confirmed [VERIFIED]
- `run_scan.py` — all cfg.scan mutation sites confirmed lines 414-417, 433-434, 444-445, 458-459 [VERIFIED]
- `quirk/engine/profiles.py` — apply_profile mutation confirmed as intentional pre-scan init [VERIFIED]
- `quirk/intelligence/trends.py:232-259` — scan_error counting confirmed [VERIFIED]
- `quirk/models.py:35` — `scan_error TEXT` column confirmed; no `category` field exists [VERIFIED]
- `quantum-chaos-enterprise-lab/lab.sh:97-108` — down and reset arms confirmed [VERIFIED]
- `pyproject.toml` — optional extras confirmed: `[motion]`, `[broker]`, `[kafka]`, `[email]`, `[cloud]`, `[db]` [VERIFIED]
- `tests/` — all 24 skip/importorskip/skipif sites catalogued and classified [VERIFIED]

---

## RESEARCH COMPLETE
