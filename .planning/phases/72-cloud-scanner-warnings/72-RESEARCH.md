# Phase 72: Cloud Scanner WARNINGs - Research

**Researched:** 2026-05-15
**Domain:** Cloud connector / engine hardening (24 WARNING rows)
**Confidence:** HIGH (all line numbers and code shapes verified against HEAD at commit cf2417a)

## Summary

Phase 72 closes 24 WARNING-severity audit rows (`scanners-cloud/WR-01..WR-24`) covering
AWS/Azure/GCP/K8s/DB/Vault connectors plus three engine modules
(`profiles.py`, `cache.py`, `risk_engine.py`). CONTEXT.md locks 25 implementation
decisions (D-01..D-25). This research verifies that each cited line range still
matches current code, identifies the existing helper / pattern precedents the
planner should reuse, and surfaces three discrepancies between the audit cites
and current HEAD that the planner must adjudicate (see `<research_concerns>` at
the bottom — none of them invalidate the locked decisions).

**Primary recommendation:** Mirror the Phase 71 plan-per-CLOUD-NN granularity
(5 plans). All five fits cleanly into surgical edits — there is no architectural
rework, no new dependency, and no schema change. The single non-trivial item is
D-04 (golden-file ordering regen), which warrants its own snapshot commit per
test strategy.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

All 25 decisions D-01 through D-25 are locked in
`.planning/phases/72-cloud-scanner-warnings/72-CONTEXT.md`. Summary:

- **D-01:** GCP KMS `MAX_KMS_PAGES = 1000` cap per loop; raise `ValueError` on overflow
- **D-01a (discretion):** Per-loop counter (default) vs shared
- **D-02:** Track raw YAML key set via `cfg.connectors._user_set_fields` (frozenset sidecar)
- **D-02a (discretion):** Sidecar name — `_user_set_fields` / `_explicit_fields` / `_yaml_set`
- **D-03:** Audit each `_set_if_default(...)` in `standard` branch; suppress when value==default
- **D-04:** Dedup sort key → `(severity_rank, finding_id, host, port)`; drop `recommendation`
- **D-04a (discretion):** Keep `_SEVERITY_RANK` module-private (default)
- **D-05:** `git mv risk_engine.py findings_evaluator.py`; recreate `risk_engine.py` as 2-line shim
- **D-05a (discretion):** Update internal imports in same commit (default yes)
- **D-06:** EOF verify sequence — py_compile + git log + wc -l + visual diff; add `# eof` marker
- **D-07:** AWS `_scan_acm` empty-ARN guard with `continue`
- **D-08:** AWS `_scan_kms` skip Disabled/PendingDeletion/PendingImport/Unavailable
- **D-09:** AWS `_scan_s3_encryption` migrate `executor.map` → `as_completed` per Phase 64
- **D-10:** AWS `_scan_eks_encryption` iterate full `enc_cfg` list
- **D-11:** AWS `ThreadPoolExecutor` import to module scope
- **D-12:** Azure KeyVault `key_size` populated per-key-type
- **D-13:** K8s `cluster_name.replace(":", "")` in `_emit_inaccessible_finding`
- **D-14:** K8s `_enumerate_secret_types` Counter excludes None
- **D-15:** K8s `dat_scan_json` fresh dict per branch (no `key_name` on unencrypted path)
- **D-16:** GCP skip both `CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED` and `UNKNOWN`
- **D-17:** GCP `_scan_cloud_sql` surface `description` via `service_detail`
- **D-18:** Cache `_read_json` wraps `json.loads` in try/except → return None
- **D-19:** Cache `scope_hash` includes `connectors` via `dataclasses.asdict`
- **D-20:** DB connector — omit `password` kwarg when None (vs empty string)
- **D-21:** DB connector exception → `safe_str(exc)` (Phase 59 helper)
- **D-22:** Vault connector — raise `ValueError` instead of env fallback when token=None
- **D-23:** Vault PKI use `cryptography.x509.load_pem_x509_certificates` (plural)
- **D-24:** `_postprocess_findings` iterate `tuple(findings)` for mutation safety
- **D-25:** Phase-72 do-not-touch list (no incidental cleanup)

### Claude's Discretion

- D-01a (per-loop vs shared counter), D-02a (sidecar attr name), D-04a (private `_SEVERITY_RANK`), D-05a (atomic import migration). Recommendations made in this research where evidence supports a default.

### Deferred Ideas (OUT OF SCOPE)

- `migration_planner.py` implementation (CR-01, `wont-fix`)
- K8s `scan_k8s_targets` None-cred handling (CR-03, deferred-v4.9)
- DeprecationWarning on `risk_engine` shim (defer to v5.0)
- Promotion of `_SEVERITY_RANK` to public helper
- Full split of findings_evaluator vs scorer
- Wizard prompt for cache scope-hash debug
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLOUD-01 | AWS hardening: ACM empty ARN, KMS disabled-skip, S3 executor.map, EKS multi-entry | D-07..D-11; aws_connector.py:45-72, 150-198, 226+303, 315-346 verified |
| CLOUD-02 | Azure/K8s correctness: key_size, colon-strip, Counter None, dat_scan_json key_name | D-12..D-15; azure_connector.py:44-77, k8s_connector.py:130-159, 286-288, 327-352 verified |
| CLOUD-03 | GCP correctness: KMS pagination cap, UNSPECIFIED/UNKNOWN consistency, Cloud SQL service_detail | D-01, D-16, D-17; gcp_connector.py:122-229, 174-180, 262-272 verified |
| CLOUD-04 | Cache + EOF integrity | D-06, D-18, D-19; cache.py:27-66, profiles.py 153 lines verified intact |
| CLOUD-05 | Misc hardening (10 rows incl. rename) | D-02..D-05, D-11, D-20..D-24; safe_exc.py present, cryptography>=44.0 verified |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| AWS/Azure/GCP/K8s/DB/Vault connector hardening | scanner (connector) | — | Module-local fixes; no cross-tier impact |
| `profiles.py` mutation guard via raw-YAML key set | engine (profile application) | config (sidecar attach) | Config load surfaces the metadata; engine consumes it |
| `cache.py` `_read_json` + `scope_hash` | engine (cache) | — | Self-contained module |
| `risk_engine.py` rename + shim | engine (findings evaluator) | callers (5 prod sites, ~10 test files) | Structural rename touches every importer |
| `_dedupe_findings` / `_postprocess_findings` | engine (findings evaluator) | golden fixtures | Output ordering change requires golden regen |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cryptography` | `>=44.0` (pyproject.toml line 13) | D-23 PEM parsing via `load_pem_x509_certificates` | Already pinned; plural-form API requires `>=36` per official docs — 44.0 well above floor |
| `dataclasses` (stdlib) | Python 3.11+ | D-02 `field(default_factory=frozenset, repr=False, compare=False)` for sidecar | Project standard; `ConnectorsCfg` already a `@dataclass` |
| `concurrent.futures` (stdlib) | Python 3.11+ | D-09 `as_completed` migration | Already used in `email_scanner.py:18` |

### Supporting (already present, reused)

| Library | Version | Purpose | Use Case |
|---------|---------|---------|----------|
| `quirk.util.safe_exc.safe_str` | Phase 59 | D-21 DB exception sanitization | Already canonical sink; verified present at `quirk/util/safe_exc.py:36` |

### Alternatives Considered

None — all 25 decisions are locked; no library swaps are in scope.

**Installation:** No new dependencies. Phase boundary explicitly forbids new pip deps.

**Version verification:** `cryptography>=44.0` confirmed in `pyproject.toml:13`. Plural-form `load_pem_x509_certificates` is in `cryptography.x509` namespace per the cryptography project docs; available since v36 — well below our pin.

## Architecture Patterns

### Recommended Plan Structure

```
.planning/phases/72-cloud-scanner-warnings/
├── 72-CONTEXT.md                  # already locked
├── 72-RESEARCH.md                 # this file
├── 72-01-PLAN.md                  # CLOUD-01 (AWS) — 4 WR rows
├── 72-02-PLAN.md                  # CLOUD-02 (Azure/K8s) — 4 WR rows
├── 72-03-PLAN.md                  # CLOUD-03 (GCP) — 3 WR rows
├── 72-04-PLAN.md                  # CLOUD-04 (Cache + EOF) — 3 WR rows
└── 72-05-PLAN.md                  # CLOUD-05 (misc + rename) — 10 WR rows
```

Mirror Phase 71's 5-plan layout (`71-01-PLAN.md` through `71-05-PLAN.md`).

### Pattern 1: `as_completed` + per-future `.exception()` (D-09)

**Source:** `quirk/scanner/email_scanner.py:18, 536-552` (Phase 32+64 idiom, verified).

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=10) as ex:
    futures = {ex.submit(_build_endpoint, bucket): bucket for bucket in buckets}
    for f in as_completed(futures):
        try:
            ep = f.result()
        except Exception as e:
            if logger:
                logger.v(f"S3 endpoint task crashed: {e}")
            continue
        if ep is not None:
            results.append(ep)
```

### Pattern 2: `safe_str(exc)` sanitization (D-21)

**Source:** `quirk/util/safe_exc.py:36-53` and existing call at `quirk/scanner/db_connector.py:166`
(already in place for the postgres branch — but the audit row stays open because the mysql/scan_error
sites may not all use it).

### Pattern 3: Dataclass sidecar field (D-02)

```python
@dataclass
class ConnectorsCfg:
    # ... existing fields ...
    # Phase 72 D-02: tracks which keys appeared in the raw YAML connectors block.
    # Used by quirk.engine.profiles to suppress mutation of user-explicit values.
    _user_set_fields: frozenset = field(default_factory=frozenset, repr=False, compare=False)
```

Then in `quirk/config.py` after `ConnectorCfg` construction (~line 378):
```python
connectors._user_set_fields = frozenset(conn_raw.keys())
```

### Pattern 4: `service_detail` routing (D-17)

**Source:** Phase 69 BLOCK-02 — already extensively used in current `gcp_connector.py:268`
(`service_detail=f"CLOUD_SQL/{description.replace(' ', '-')}"`). The audit row notes
`description` lives only in `cloud_scan_json`; D-17 says surface it in `service_detail`.
The code already does this — the format is `f"CLOUD_SQL/{description.replace(' ', '-')}"`.
See `<research_concerns>` C-3 below for clarification.

### Anti-Patterns to Avoid

- **Mutating list during iteration** — D-24 explicit fix; use `tuple(findings)`
- **Per-loop `from concurrent.futures import ...`** — D-11 (function-body import)
- **Stringifying raw exceptions into `scan_error`** — D-21 + Phase 59 LEAK-01 precedent
- **Reusing the encrypted-branch dict for the unencrypted path** — D-15

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-cert PEM splitting | Naive `.split("-----BEGIN CERTIFICATE-----")` | `cryptography.x509.load_pem_x509_certificates(pem_bytes)` | Edge cases: trailing whitespace, mixed `\r\n`, certificate-with-comment headers |
| Credential-safe exception text | Custom regex per connector | `quirk.util.safe_exc.safe_str(exc)` | One sink, AST-gated test in `tests/test_safe_exc_gate.py` |
| Severity rank ordering | Inline tuple per call site | `_SEVERITY_RANK` module dict (D-04, default private) | One source of truth |
| Dataclass `asdict` for hashing | Manual dict-comprehension | `dataclasses.asdict(cfg.connectors)` | Recursive, handles nested fields safely |

## Runtime State Inventory

> Phase 72 is a code-hardening phase, not a rename/refactor. The single rename
> (D-05 `risk_engine.py → findings_evaluator.py`) is structural only.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no string is stored as a DB key/collection name | None |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | `VAULT_TOKEN` env var referenced at `vault_connector.py:396`; D-22 removes the env fallback. Env var name is unchanged — operators still set it, but must pass it explicitly. | Update callers (likely `run_scan.py`) to read env and pass through |
| Build artifacts | `quirk/engine/__pycache__/risk_engine.cpython-*.pyc` after D-05 rename — stale once `risk_engine.py` becomes a 2-line shim. Reinstall not needed; `__pycache__` regenerates on next import. | None — pycache auto-regenerates |

**Risk-engine rename downstream callers (verified via grep):**

| File | Line | Import |
|------|------|--------|
| `run_scan.py` | 36 | `from quirk.engine.risk_engine import evaluate_endpoints, evaluate_email_endpoints, evaluate_broker_endpoints` |
| `tests/test_risk_engine.py` | 13 | multi-name import |
| `tests/test_email_findings.py` | 58, 75, 89, 105, 121, 137 | 6 sites for `evaluate_email_endpoints` |
| `tests/test_risk_engine_coverage_gap.py` | 11 | `evaluate_endpoints` |
| `tests/test_risk_engine_cert_defects.py` | 18 | `_chain_verified, evaluate_endpoints` |
| `tests/test_broker_run_integration.py` | 22 | `evaluate_broker_endpoints, _dedupe_findings` |

Per D-05a (default yes), all 6 of these files get migrated to `findings_evaluator` in the same commit. The shim then exists only for downstream/user code.

## Common Pitfalls

### Pitfall 1: WR-13 cite mismatch (D-09)

CONTEXT D-09 says "executor.map(_classify, ...)" at lines 303-306. Current code has
`executor.map(_build_endpoint, buckets)` (different inner function name). Both
`_classify` and `_build_endpoint` already catch internal exceptions and return None
on failure. The real risk that `as_completed` migration addresses is exceptions
raised during the *iteration consumption* (`for ep in executor.map(...)`) which
`executor.map` does propagate but only when the result is consumed.

**Planner action:** Apply D-09 to the actual current `_build_endpoint` site (line 303). Note in the task that the inner function name differs from the audit row but the locked behavior change is correct.

### Pitfall 2: GCP UNKNOWN handling already partially present (D-16)

`gcp_connector.py:175` already does `if alg_name == "UNKNOWN": continue` because the
`GCP_KMS_ALGORITHM_MAP.get(algorithm, ("UNKNOWN", None))` default coerces unknown
algorithms to `"UNKNOWN"`. The audit row "inconsistent UNSPECIFIED/UNKNOWN handling"
means: the explicit `CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED` entry maps to
`("UNKNOWN", None)` so it currently *does* hit the skip branch, but the log message
says "unspecified" not "UNSPECIFIED/UNKNOWN".

**Planner action:** D-16 calls for `{"CRYPTO_KEY_VERSION_ALGORITHM_UNSPECIFIED", "UNKNOWN"}` skip set explicitly checking the raw `algorithm` string before the map lookup, plus an INFO log that names the algorithm. Distinct from the current alg_name check.

### Pitfall 3: WR-08 may already be partially closed (D-21)

`db_connector.py:166` already calls `safe_str(exc)` in the postgres path. The MySQL
path at line 213-220 sets `password=password or ""` (relates to D-20) but the
analogous exception handler should also be inspected for `safe_str` coverage.

**Planner action:** Apply D-21 exhaustively to all `scan_error=f"... {exc}"` sites in `db_connector.py`. Postgres already uses safe_str; mysql/rds branches may not.

### Pitfall 4: `_enumerate_secret_types` already coerces None (D-14)

`k8s_connector.py:286-288` reads `Counter((s.type or "Opaque") for s in secrets.items)`.
The `or "Opaque"` already prevents None — but D-14 says explicitly *filter out* None
via `Counter(t for t in secret_types if t is not None)`. The audit row's concern is
that the current coercion masks the gap (Opaque-typed secrets and None-typed secrets
become indistinguishable).

**Planner action:** Per D-14, replace the `or "Opaque"` coercion with a `if t is not None` filter and a DEBUG log of skipped Nones. This changes one fixture expectation; check `tests/test_k8s_connector.py`.

### Pitfall 5: `profiles.py` line count mismatch (D-06)

CONTEXT cites lines 110-153 for WR-11/12/21 sites. `wc -l` returns 153.
`python -m py_compile quirk/engine/profiles.py` exits 0 — file is intact.
Last 10 lines show the safe-mode tail block correctly closed by indentation.
**Planner action:** Per D-06, add `# eof` marker as the final line and flip WR-21.

### Pitfall 6: D-04 sort tuple "finding_id" field name

CONTEXT D-04 says the new key is `(severity_rank, finding_id, host, port)`. Current
`_dedupe_findings` uses 4-tuple `(host, port, title, recommendation)` — there is no
`finding_id` column. The closest semantic match is `title`, which is the
identity-defining field in the current dedup. The "finding_id" in D-04 likely means
"the title-or-rule-identifier" field.

**Planner action:** Map `finding_id` → `title` in the new sort key, producing `(severity_rank, title, host, port)`. Confirm in plan-checker — if planner disagrees, surface via discuss-phase.

## Code Examples

### D-01: GCP KMS pagination cap

```python
# quirk/scanner/gcp_connector.py — module scope
MAX_KMS_PAGES = 1000  # per-loop cap; ~1M items at default page size

# inside _scan_kms, per-loop counter (D-01a default)
page_count = 0
while loc_request is not None:
    page_count += 1
    if page_count > MAX_KMS_PAGES:
        raise ValueError(
            f"GCP KMS pagination exceeded {MAX_KMS_PAGES} pages for "
            f"{project_resource}; aborting to prevent runaway scan"
        )
    loc_response = loc_request.execute()
    # ... existing body ...
```

### D-02: User-explicit field tracking

```python
# quirk/config.py — ConnectorsCfg class (~line 192)
@dataclass
class ConnectorsCfg:
    # ... existing fields ...
    _user_set_fields: frozenset = field(default_factory=frozenset, repr=False, compare=False)

# quirk/config.py — after conn_raw build (~line 380, post-ConnectorCfg construction)
connectors._user_set_fields = frozenset(conn_raw.keys())

# quirk/engine/profiles.py — lines 110-117, 134-141
if 'enable_email' not in cfg.connectors._user_set_fields:
    if not cfg.connectors.enable_email:
        cfg.connectors.enable_email = True
```

### D-04: Stable dedup sort

```python
# quirk/engine/risk_engine.py (post-D-05: findings_evaluator.py) lines 312-319
_SEVERITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}

return [
    deduped[k]
    for k in sorted(
        deduped.keys(),
        key=lambda x: (
            _SEVERITY_RANK.get(str(deduped[x].get("severity", "INFO")).upper(), 4),
            x[2],  # title (per Pitfall 6 mapping for "finding_id")
            x[0],  # host
            x[1],  # port
        ),
    )
]
```

### D-09: as_completed migration (S3)

See Pattern 1 above. Source idiom: `quirk/scanner/email_scanner.py:536-552`.

### D-18: Cache `_read_json` malformed JSON handling

```python
# quirk/engine/cache.py:27-29
def _read_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        # Phase 72 D-18: corrupt cache file — return None, leave file on disk for forensics
        import logging
        logging.getLogger(__name__).warning("Cache file %s corrupt — ignoring: %s", path, e)
        return None
```

Then `load_cache` at line 56 needs `obj = _read_json(path); if obj is None: return None`.

### D-19: scope_hash with connectors

```python
import dataclasses

def scope_hash(cfg, discovery_mode, nmap_extra_args="", ports=None):
    t = cfg.targets
    scan = cfg.scan
    parts = {
        "discovery_mode": discovery_mode,
        # ... existing fqdns/cidrs/include_ips/exclude_ips/ports/include_sni/nmap_extra_args ...
        # Phase 72 D-19: connector enable flags must invalidate cache
        "connectors": dataclasses.asdict(cfg.connectors),
    }
    raw = json.dumps(parts, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]
```

Note: `dataclasses.asdict(cfg.connectors)` will include the new `_user_set_fields` from D-02 (a frozenset, not JSON-serializable). Either exclude the sidecar (`d = dataclasses.asdict(cfg.connectors); d.pop('_user_set_fields', None)`) or use a `field` with `metadata={"asdict_skip": True}` and a filter. **Recommendation:** explicit pop in `scope_hash` — minimal coupling.

### D-22: Vault token explicit raise

```python
# quirk/scanner/vault_connector.py — replace lines 396-406
if token is None:
    raise ValueError(
        "vault_connector requires explicit token; "
        "pass os.environ.get('VAULT_TOKEN') if env fallback intended"
    )
resolved_token = token
if not resolved_token:  # explicit empty-string passed — keep current scan_error path
    return [CryptoEndpoint(...)]
```

Caller side (likely `run_scan.py`): pass `os.environ.get("VAULT_TOKEN") or cfg.connectors.vault_token`.

### D-23: PEM plural parser

```python
from cryptography import x509

# quirk/scanner/vault_connector.py:277-282
try:
    certs = x509.load_pem_x509_certificates(chain_pem.encode("utf-8"))
except AttributeError:  # cryptography < 36 — should never hit at our 44.0 pin
    logger.v("cryptography lib too old for load_pem_x509_certificates; falling back")
    # fall back to existing naive split
    ...
for idx, cert in enumerate(certs, start=1):
    single_pem = cert.public_bytes(serialization.Encoding.PEM).decode("ascii")
    alg, size, sev, reason, sig_alg = _classify_pki_cert(single_pem)
    # ... existing CryptoEndpoint emission ...
```

### D-24: Mutation-safe iteration

```python
# quirk/engine/risk_engine.py (post-rename: findings_evaluator.py) :335-371
adds, removes = [], []
for f in tuple(findings):  # snapshot
    # ... existing read-only logic that decides to mutate f ...
    # if a finding should be removed, append to removes; if extra finding, append to adds
# apply mutations after iteration
for f in removes:
    findings.remove(f)
findings.extend(adds)
return _dedupe_findings(findings)
```

Caveat: current `_postprocess_findings` body actually mutates **fields of existing findings in place** (changing severity/title/recommendation), not adding/removing findings. The "mutation during iteration" risk is therefore lower than the audit row suggests — but the locked decision still says use `tuple(findings)` defensively, so apply it. See `<research_concerns>` C-2.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `executor.map(...)` silent-swallow | `as_completed` + per-future `.exception()` | Phase 64 (email_scanner) | D-09 carries forward |
| `f"scan-error: {exc}"` raw stringification | `safe_str(exc)` from `quirk/util/safe_exc.py` | Phase 59 LEAK-01 | D-21 applies pattern to db_connector |
| `risk_engine.py` (misnamed findings evaluator) | `findings_evaluator.py` + 2-line shim | Phase 72 (D-05) | Rename + import migration |
| 4-tuple dedup key including `recommendation` | `(severity_rank, title, host, port)` | Phase 72 (D-04) | Stable golden output |

**Deprecated/outdated:**
- Naive `.split("-----BEGIN CERTIFICATE-----")` PEM split — replaced by `load_pem_x509_certificates`

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `finding_id` in D-04 sort tuple semantically maps to existing `title` column | Pitfall 6 | Sort key wrong; planner discusses with user |
| A2 | `dataclasses.asdict(cfg.connectors)` choking on frozenset sidecar must be filtered | D-19 example | Cache scope_hash raises TypeError on first run |
| A3 | All 6 test files using `risk_engine` imports get atomically migrated (D-05a default yes) | Runtime State Inventory | Mixed-state imports during commit window |

## Open Questions

1. **D-04 `finding_id` field meaning**
   - What we know: current dedup tuple has `(host, port, title, recommendation)`. No `finding_id`/`id`/`cbom_finding_id` column exists in the dedup dict.
   - What's unclear: planner needs to confirm `finding_id` ≡ `title` (see Pitfall 6).
   - Recommendation: Treat as `title` unless `/gsd-discuss-phase` surfaces an alternative.

2. **D-19 sidecar serialization**
   - What we know: D-02 adds `_user_set_fields: frozenset`. `dataclasses.asdict` recursively serializes; frozenset is not JSON-serializable by default.
   - What's unclear: whether to `pop` the sidecar in `scope_hash` or annotate the field to skip.
   - Recommendation: pop in `scope_hash` (minimal coupling); document in code comment.

3. **D-22 caller migration scope**
   - What we know: `vault_connector` is called from `run_scan.py` (likely) and `tests/test_vault_connector.py`. The env-fallback removal means every caller that relied on env now needs an explicit pass-through.
   - What's unclear: how many production code paths call `scan_vault_targets(token=None)` today.
   - Recommendation: planner greps `scan_vault_targets(` to enumerate, updates each, adds a test for the explicit ValueError.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `cryptography` Python pkg | D-23 PEM plural parser | ✓ | `>=44.0` (pyproject.toml:13) | None needed |
| `python -m py_compile` | D-06 verification | ✓ (Python 3.11+) | — | — |
| `git` | D-05 `git mv`, D-06 history check | ✓ | — | — |

No missing dependencies. All decisions are implementable on the current toolchain.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | (project root) — uses pytest defaults |
| Quick run command | `pytest tests/test_cache.py tests/test_db_connector.py tests/test_vault_connector.py tests/test_k8s_connector.py tests/test_risk_engine.py -x` |
| Full suite command | `pytest -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLOUD-01 | AWS hardening (4 WR rows) | unit | `pytest tests/test_aws_connector.py -x` | ❌ Wave 0 |
| CLOUD-02 | Azure key_size + K8s correctness | unit | `pytest tests/test_azure_blob.py tests/test_k8s_connector.py -x` | ✅ partial (test_azure_blob.py covers blob; need Azure KeyVault test) |
| CLOUD-03 | GCP correctness | unit | `pytest tests/test_gcp_connector.py -x` | ❌ Wave 0 |
| CLOUD-04 | Cache + EOF | unit | `pytest tests/test_cache.py -x` | ✅ test_cache.py exists |
| CLOUD-05 | Misc + rename | unit | `pytest tests/test_risk_engine.py tests/test_db_connector.py tests/test_vault_connector.py -x` | ✅ all three exist |

### Sampling Rate

- **Per task commit:** Module-scoped pytest (one file)
- **Per wave merge:** All 5 CLOUD-NN test modules
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_aws_connector.py` — does not exist; CLOUD-01 needs new test module covering `_scan_acm` empty-ARN, `_scan_kms` disabled-skip, `_scan_s3_encryption` exception propagation, `_scan_eks_encryption` multi-entry
- [ ] `tests/test_azure_connector.py` (or extend `test_azure_blob.py`) — needs `_scan_keyvault_keys` `key_size` populated for RSA/EC/OCT key types
- [ ] `tests/test_gcp_connector.py` — does not exist; CLOUD-03 needs new test module covering pagination cap (parametrized 1001-page test), UNSPECIFIED/UNKNOWN skip, Cloud SQL `service_detail`
- [ ] `tests/test_profiles.py` — does not exist; CLOUD-05 D-02/D-03 needs tests for user-explicit override + standard re-apply suppression
- [ ] `tests/test_findings_evaluator_dedupe.py` — golden-file test for D-04 sort stability

Framework already installed; no install command needed.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (D-22 Vault token handling) | explicit pass-through, no env fallback in connector |
| V5 Input Validation | yes (D-18 cache JSON, D-23 PEM parsing) | try/except wrapper; cryptography lib |
| V6 Cryptography | yes (D-23 PEM) | `cryptography.x509.load_pem_x509_certificates` (canonical) |
| V7 Error Handling & Logging | yes (D-21 safe_str) | Phase 59 helper — never hand-roll |

### Known Threat Patterns for cloud-connector stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credential leak via exception text | Information Disclosure | `safe_str(exc)` (Phase 59 / D-21) |
| Runaway scan via unbounded pagination | DoS (self-inflicted) | `MAX_KMS_PAGES = 1000` cap (D-01) |
| Cache poisoning via malformed JSON | Tampering / DoS | try/except around `json.loads` (D-18) |
| Implicit env-var fallback for secrets | Misconfig / IDOR | Explicit ValueError (D-22) |

## Project Constraints (from CLAUDE.md)

- **PEP 8** for all Python changes.
- **Minimal diffs** — avoid unnecessary refactors. D-25 explicitly enforces this (do-not-touch list).
- After changes, run `python -m compileall` and relevant tests.
- Staleness review cadence does **not** apply to Phase 72 (no model catalog / compliance catalog edits in scope).
- Chaos lab maintenance does **not** apply (no Docker Compose profile changes).
- **Mandatory phase completion:** Create Obsidian Phase 72 note, update `docs/UAT-SERIES.md`, sync to vault, commit UAT-SERIES.md update.

## Sources

### Primary (HIGH confidence)

- `quirk/scanner/aws_connector.py:1-346` — D-07..D-11 sites all verified
- `quirk/scanner/azure_connector.py:44-77` — D-12 site verified
- `quirk/scanner/gcp_connector.py:1-285` — D-01, D-16, D-17 sites verified
- `quirk/scanner/k8s_connector.py:130-352` — D-13, D-14, D-15 sites verified
- `quirk/scanner/db_connector.py:88-167, 213-220` — D-20, D-21 sites verified (D-21 partially closed for postgres path)
- `quirk/scanner/vault_connector.py:277-282, 396-430` — D-22, D-23 sites verified
- `quirk/engine/cache.py:1-91` — full file; D-18, D-19 sites verified
- `quirk/engine/profiles.py:1-153` — full file; py_compile passes; 153 lines verified intact
- `quirk/engine/risk_engine.py:288-371` — D-04, D-05, D-24 sites verified
- `quirk/util/safe_exc.py:36-53` — D-21 helper verified
- `quirk/config.py:183-256, 331, 377-380` — D-02 sites verified
- `pyproject.toml:13` — `cryptography>=44.0` pin verified
- `quirk/scanner/email_scanner.py:18, 536-552` — D-09 pattern source verified

### Secondary (MEDIUM confidence)

- `.planning/phases/71-protocol-scanner-warnings/71-CONTEXT.md` and `71-01-PLAN.md` — Phase 71 plan structure precedent
- `.planning/audit-2026-05-08/scanners-cloud/REVIEW.md` — audit cite source
- `.planning/audit-2026-05-08/AUDIT-TASKS.md:91-114` — WR-01..WR-24 ledger rows confirmed `[ ] open`

### Tertiary (LOW confidence)

- D-04 `finding_id` semantic interpretation — relies on planner clarification (A1)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `cryptography>=44.0` and stdlib-only verified
- Architecture: HIGH — all 25 decision sites verified against HEAD
- Pitfalls: HIGH — 3 audit-vs-current-code mismatches identified, all benign
- Test gaps: MEDIUM — 4 missing test modules identified for Wave 0 creation

**Research date:** 2026-05-15
**Valid until:** 2026-06-15 (stable phase; no fast-moving dependencies)

<research_concerns>
## Research Concerns (planner adjudication needed)

These are NOT new decisions. CONTEXT.md remains authoritative. Each concern surfaces a discrepancy between the locked decision wording and current HEAD, and recommends how the planner should handle it.

### C-1 (D-09): function name in audit cite differs from current code

**CONTEXT D-09 says:** `executor.map(_classify, ...)` at `aws_connector.py:303-306`.
**Current code shows:** `executor.map(_build_endpoint, buckets)` at exactly lines 303-306.
**Adjudication:** Apply D-09 to the actual current call site. The locked behavior (migrate to `as_completed` + per-future `.exception()`) is correct regardless of inner function name.

### C-2 (D-24): "mutation during iteration" risk is lower than audit suggests

**CONTEXT D-24 says:** "currently mutates `findings` (extends/removes) during iteration".
**Current code shows:** `_postprocess_findings` (lines 335-371) iterates `for f in findings` and mutates *fields* of existing finding dicts in-place (e.g., `f["severity"] = "INFO"`), never extending/removing the outer list during the loop.
**Adjudication:** Apply D-24 anyway — `for f in tuple(findings)` is defensively correct and matches the locked decision. The risk is hypothetical today but real if anyone later adds an `append`/`remove`.

### C-3 (D-17): GCP Cloud SQL `service_detail` may already be partially routed

**CONTEXT D-17 says:** `description` field currently goes only into `cloud_scan_json`.
**Current code shows:** `gcp_connector.py:268` builds `service_detail=f"CLOUD_SQL/{description.replace(' ', '-')}"`. The description IS surfaced via `service_detail` already — encoded in a slash-separated suffix.
**Adjudication:** Two possibilities for the planner to clarify:
  (a) The audit pre-dates the current code; WR-22 may be closeable with just a verification test asserting that `service_detail` contains the description token.
  (b) D-17 wants the raw description string in a *separate* `service_detail` field rather than encoded in a slash suffix — but the `CryptoEndpoint` schema has only one `service_detail` field, so this isn't structurally possible.
Recommended: planner treats WR-22 as a verification-only row (add assertion test, no code change) and flips it closed. Surface to user via discuss-phase if disagreement.

### C-4 (Pitfall 6 / A1): D-04 `finding_id` field has no current analog

**CONTEXT D-04 says:** new sort key is `(severity_rank, finding_id, host, port)`.
**Current code shows:** no `finding_id` column anywhere in finding dicts; `title` is the identity field.
**Adjudication:** Planner maps `finding_id` → `title` in the implementation. If a strict reading is required, planner should surface to user via discuss-phase.
</research_concerns>
