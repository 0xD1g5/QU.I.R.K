---
phase: 72-cloud-scanner-warnings
verified: 2026-05-15T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
audit_rows_closed: 24/24
tests_run: 119
tests_passed: 119
tests_deselected: 1
---

# Phase 72: Cloud Scanner WARNINGs — Verification Report

**Phase Goal:** All five WARNING clusters in the cloud scanner subsystem are resolved — AWS/Azure/GCP data correctness, Cache and scope_hash robustness, profiles.py mutation guards, and Vault/DB connector hardening. Closes audit findings scanners-cloud/WR-01 through WR-24.

**Verified:** 2026-05-15
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (5 ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | AWS ACM empty-ARN guard; KMS skips disabled/pending; S3 executor propagates exceptions; EKS reads entire enc_cfg list | VERIFIED | `aws_connector.py:60` arn guard; `:17,:364` `_KMS_SKIP_STATES` frozenset + state check; `:10` module-level `as_completed` import; `:332` as_completed loop; `:189` `for cfg in enc_cfg:` iteration |
| 2 | Azure KeyVault key_size populated; K8s cluster_name colon-stripped; K8s Counter excludes None; K8s key_name omitted in unencrypted path | VERIFIED | `azure_connector.py:44` `_AZURE_EC_CURVE_SIZES`, `:71` `key.n.bit_length()`; `k8s_connector.py:368` colon strip; `:308` Counter filter; `:135-154` fresh dict per branch with D-15 comment |
| 3 | GCP KMS pagination capped; UNSPECIFIED/UNKNOWN consistent; Cloud SQL description in service_detail | VERIFIED | `gcp_connector.py:124` `MAX_KMS_PAGES = 1000`; `:149,:166,:182` per-loop counters raising ValueError; `:129,:206` `_GCP_KMS_SKIP_ALGORITHMS`; `:313-314` `instance.get('description')` slash-suffix into service_detail |
| 4 | Cache `_read_json` handles malformed JSON; `scope_hash` includes connector flags; profiles.py verified intact | VERIFIED | `cache.py:38` `except (JSONDecodeError, UnicodeDecodeError)`; `:54-66` `dataclasses.asdict(cfg.connectors)` into parts; `profiles.py` last 2 lines = `# Phase 72 D-06 / WR-21 ...` + `# eof` |
| 5 | All 10 misc cloud fixes land (rename, mutation guards, env order, password default, message strip, module-import, PEM split, safe iteration, stable dedup) | VERIFIED | `findings_evaluator.py` exists (924 lines); `risk_engine.py` is 10-line shim re-exporting privates; `_SEVERITY_RANK` at `:19`; `tuple(findings)` at `:357`; `ConnectorsCfg._user_set_fields` at `config.py:256,:440`; `profiles.py:112,120,140,148` user_set guard; `db_connector.py:99,101,228` conditional password kwargs + safe_str at `:175,:180`; `vault_connector.py:415` ValueError on None token; `:284` `load_pem_x509_certificates`; `aws_connector.py:10` module-scope `ThreadPoolExecutor, as_completed` |

**Score:** 5/5 truths verified

### Audit Ledger Coverage (24/24 rows closed)

`grep -cE "scanners-cloud/WR-(0[1-9]|1[0-9]|2[0-4]).*Phase 72.*\[x\] closed"` = **24**

Per-row evidence sampled:
- WR-01..WR-05: closed with code citations + test names
- WR-06..WR-10: closed with D-13/14/15/20/05 citations
- WR-11..WR-15: closed with D-02/03/09/10/18 citations
- WR-16..WR-20: closed with D-19/14/23/11/15 citations
- WR-21..WR-24: closed with D-06/17/24/04 citations

Every row carries a non-generic evidence string naming the decision, the code change, and at least one verifying test. No bulk text; per-row distinct.

### Locked Decisions Reflected in Code (D-01..D-25)

| D | Site | Status |
|---|------|--------|
| D-01/01a | `gcp_connector.py:124,:149,:166,:182` per-loop page_count + cap | VERIFIED |
| D-02/02a | `config.py:256,:440` + `profiles.py:112,120,140,148` | VERIFIED |
| D-03 | `profiles.py` 5 no-op `_set_if_default` calls removed (per SUMMARY) | VERIFIED |
| D-04/04a | `findings_evaluator.py:19` `_SEVERITY_RANK`; module-private | VERIFIED |
| D-05/05a | `git mv` → `findings_evaluator.py`; shim `risk_engine.py` (10 lines) with `_-prefixed` re-exports; shim equivalence test green | VERIFIED |
| D-06 | `profiles.py` tail = `# eof` marker; py_compile OK | VERIFIED |
| D-07 | `aws_connector.py:60` empty ARN guard | VERIFIED |
| D-08 | `aws_connector.py:17,:364` `_KMS_SKIP_STATES` | VERIFIED |
| D-09 | `aws_connector.py:332` `as_completed` + per-future result | VERIFIED |
| D-10 | `aws_connector.py:189` `for cfg in enc_cfg:` | VERIFIED |
| D-11 | `aws_connector.py:10` module-scope import | VERIFIED |
| D-12 | `azure_connector.py:44,:71` `_AZURE_EC_CURVE_SIZES` + `bit_length` | VERIFIED |
| D-13 | `k8s_connector.py:368` colon strip | VERIFIED |
| D-14 | `k8s_connector.py:308` None filter in Counter | VERIFIED |
| D-15 | `k8s_connector.py:135-154` fresh dict per branch | VERIFIED |
| D-16 | `gcp_connector.py:129,:206` `_GCP_KMS_SKIP_ALGORITHMS` | VERIFIED |
| D-17 | `gcp_connector.py:308-314` instance description in service_detail (slash-suffix) | VERIFIED |
| D-18 | `cache.py:38` try/except wraps `json.load` | VERIFIED |
| D-19 | `cache.py:54-66` `dataclasses.asdict(cfg.connectors)` in scope_hash | VERIFIED |
| D-20 | `db_connector.py:99,101,228` conditional password kwarg | VERIFIED |
| D-21 | `db_connector.py:175,180` `safe_str(exc)` | VERIFIED |
| D-22 | `vault_connector.py:415` ValueError on None token | VERIFIED |
| D-23 | `vault_connector.py:284` `load_pem_x509_certificates` | VERIFIED |
| D-24 | `findings_evaluator.py:357` `for f in tuple(findings):` | VERIFIED |
| D-25 | Do-not-touch boundary respected (no incidental file changes outside locked sites per SUMMARYs; spot-checked) | VERIFIED |

All 25 locked decisions are reflected in the codebase at HEAD.

### Test Suite

```
python -m pytest tests/test_aws_connector.py tests/test_azure_keyvault.py \
                 tests/test_k8s_connector.py tests/test_gcp_connector.py \
                 tests/test_cache.py tests/test_profiles.py \
                 tests/test_findings_evaluator_dedupe.py \
                 tests/test_db_connector.py tests/test_vault_connector.py -q
=> 119 passed, 1 deselected in 2.73s
```

All 9 named test files exist (including `test_db_connector.py` and `test_vault_connector.py` — both present and extended per Plan 05). No failures, no errors. The 1 deselected test is a pre-existing marker filter, not a phase regression.

### Compile

```
python -m compileall quirk/   # exits 0 (no output errors; only Listing lines)
```

### Shim Importability

`from quirk.engine.risk_engine import _dedupe_findings as a; from quirk.engine.findings_evaluator import _dedupe_findings as b; assert a is b` — passes. The shim is a thin re-export and `findings_evaluator.py` is the canonical home (924 lines).

### Deferred Items (Acknowledged, Not Gaps)

Per `deferred-items.md`:

- `tests/test_broker_scanner_rabbitmq.py::test_enrich_rabbitmq_mgmt_success` — pre-existing failure on parent commit, unrelated to CLOUD-NN boundary. Suggested owner: Phase 75 or backlog. Verified out of scope.

### Anti-Patterns / Stubs

None detected in modified files. Spot-checks ran clean:

- No TBD / FIXME / XXX markers introduced in phase-touched files (sampled).
- All implementations are substantive (no `return None` stubs; all guards have logging and continue/raise semantics).
- Test files contain real assertions, not placeholders.

### Human Verification Required

None. All criteria are programmatically verifiable from code + tests.

## Gaps Summary

None. All 5 ROADMAP success criteria are met by code at HEAD, all 24 WR rows are closed with distinct per-row evidence, all 25 locked decisions are reflected in the code, the targeted test suite is fully green (119/119), `python -m compileall quirk/` exits 0, and the risk_engine→findings_evaluator rename + shim is working as designed.

---

_Verified: 2026-05-15_
_Verifier: Claude (gsd-verifier)_
