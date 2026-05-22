# Dead-Code Candidates — Reviewed Backlog (D-02b)

**Tool:** `vulture 2.16`  
**Command:** `vulture quirk/ --min-confidence 60`  
**Run date:** 2026-05-22  
**Status:** REVIEWED BACKLOG — for future per-item review only

> **IMPORTANT:** This file is a reviewed catalogue, NOT an action list. Nothing listed
> here has been deleted. Nothing should be deleted based solely on this report without
> a per-item review that accounts for:
>
> - **Dynamic dispatch** (scanner entry points called by name from `run_scan.py`)
> - **Optional-extra imports** (try/except blocks for optional dependencies)
> - **Public API contracts / CI gates** (e.g., Phase 77 D-15 locks `IntelligenceReport`)
> - **Signal-handler conventions** (`frame`, `signum` params are required by Python's
>   `signal.signal()` protocol even if the handler body ignores them)
>
> False-positive rate at 60% confidence is HIGH. Treat 60% findings as hints only.

---

## High-Signal Findings (80–100% confidence)

These are more likely to be genuinely unused but still require per-item review before deletion.

| File | Line | Finding | Confidence | Notes |
|------|------|---------|------------|-------|
| `quirk/cli/scheduler_cmd.py` | 29 | Unused variables `frame`, `signum` | 100% | Signal handler params — required by `signal.signal()` protocol; NOT dead |
| `quirk/dashboard/api/app.py` | 142 | Unused variable `full_path` | 100% | Likely route-builder artifact; check if used in middleware chain |
| `quirk/dashboard/api/schemas.py` | 346 | Unused variable `cls` | 100% | Likely a `@validator` or classmethod that receives `cls` by convention |
| `quirk/db.py` | 32 | Unused variable `connection_record` | 100% | SQLAlchemy event listener param — required by event API |
| `quirk/discovery/coverage.py` | 1 | Unused variable `reachable_hosts` | 100% | Check if used downstream |
| `quirk/reports/html_renderer.py` | 110 | Unreachable `else` expression | 100% | Structural dead branch — highest-confidence real finding; safe to review |
| `quirk/scanner/azure_connector.py` | 22 | Unused import `CertificateClient` | 90% | Optional-extra try/except import block — `CertificateClient` may be used conditionally |
| `quirk/scanner/gcp_connector.py` | 27 | Unused import `DefaultCredentialsError` | 90% | Optional-extra try/except import block — exception class may be caught elsewhere |
| `quirk/scanner/k8s_connector.py` | 37 | Unused import `ApiException` | 90% | Optional-extra try/except import block — exception class likely used in catch clauses |
| `quirk/scanner/k8s_connector.py` | 75 | Unused import `_AKSClient` | 90% | Optional-extra try/except import block — private import for optional AKS path |

### Notes on high-signal findings

- `html_renderer.py:110` — The unreachable `else` branch is the most likely genuine dead
  branch. Review the containing if/elif/else chain before removing.
- `scheduler_cmd.py:29` — `signum` and `frame` are NEVER dead in a signal handler. Python's
  `signal.signal(sig, handler)` requires the handler signature `handler(signum, frame)`.
  Removing these params would break registration. Do not delete.
- `db.py:32` — SQLAlchemy `@event.listens_for` callbacks receive positional args by the event
  framework. `connection_record` is required by the event API.
- `dashboard/api/schemas.py:346` — Pydantic `@validator` classmethods always receive `cls`
  as the first positional arg. Not dead.

---

## Low-Signal Findings (60% confidence — mostly false positives)

The bulk of 60% findings are scanner entry-point functions (`scan_*_targets`), CLI command
functions (`run_*`), and dataclass field attributes. These are called via dynamic dispatch
from `run_scan.py` or wired by the CLI framework and are NOT dead code.

### Scanner Entry Points — FALSE POSITIVES (Pitfall 5)

All `scan_*_targets` functions are called by name-based dynamic dispatch from `run_scan.py`.
Vulture's AST analysis cannot see through `getattr(module, "scan_" + name + "_targets")`
-style calls. **None of these should be deleted.**

| File | Function | Confidence |
|------|----------|------------|
| `quirk/scanner/adcs_scanner.py:270` | `scan_adcs_targets` | 60% |
| `quirk/scanner/aws_connector.py:458` | `scan_aws_targets` | 60% |
| `quirk/scanner/azure_connector.py:284` | `scan_azure_targets` | 60% |
| `quirk/scanner/broker_scanner.py:449` | `scan_kafka_targets` | 60% |
| `quirk/scanner/broker_scanner.py:525` | `scan_rabbitmq_targets` | 60% |
| `quirk/scanner/broker_scanner.py:783` | `scan_redis_targets` | 60% |
| `quirk/scanner/container_scanner.py:128` | `scan_container_targets` | 60% |
| `quirk/scanner/db_connector.py:55` | `scan_pg_targets` | 60% |
| `quirk/scanner/db_connector.py:191` | `scan_mysql_targets` | 60% |
| `quirk/scanner/dnssec_scanner.py:415` | `scan_dnssec_targets` | 60% |
| `quirk/scanner/email_scanner.py:507` | `scan_email_targets` | 60% |
| `quirk/scanner/fingerprint.py:136` | `fingerprint_service` | 60% |
| `quirk/scanner/gcp_connector.py:401` | `scan_gcp_targets` | 60% |
| `quirk/scanner/jwt_scanner.py:202` | `scan_jwt_targets` | 60% |
| `quirk/scanner/k8s_connector.py:383` | `scan_k8s_targets` | 60% |
| `quirk/scanner/kerberos_scanner.py:263` | `scan_kerberos_targets` | 60% |
| `quirk/scanner/pqc_probe.py:74` | `probe_pqc_hybrid` | 60% |
| `quirk/scanner/saml_scanner.py:429` | `scan_saml_targets` | 60% |
| `quirk/scanner/smime_scanner.py:187` | `scan_smime_targets` | 60% |
| `quirk/scanner/source_scanner.py:106` | `scan_source_targets` | 60% |
| `quirk/scanner/ssh_scanner.py:105` | `scan_ssh_targets` | 60% |
| `quirk/scanner/tls_scanner.py:518` | `scan_tls_targets` | 60% |
| `quirk/scanner/vault_connector.py:391` | `scan_vault_targets` | 60% |
| `quirk/scanner/aws_connector.py:142` | `_scan_eks_encryption` | 60% |
| `quirk/scanner/aws_connector.py:226` | `_scan_s3_encryption` | 60% |
| `quirk/scanner/azure_connector.py:154` | `_scan_blob_encryption` | 60% |

### CLI Command Functions — FALSE POSITIVES

CLI `run_*` functions are wired via `run_scan.py` argument dispatch and Typer/Click
registration. Vulture cannot see CLI framework wiring.

| File | Function | Confidence |
|------|----------|------------|
| `quirk/cli/banner.py:154` | `print_banner` | 60% |
| `quirk/cli/cmvp_cmd.py:139` | `run_cmvp` | 60% |
| `quirk/cli/doctor_cmd.py:229` | `run_doctor` | 60% |
| `quirk/cli/errors_cmd.py:95` | `run_errors` | 60% |
| `quirk/cli/init_cmd.py:7` | `run_init` | 60% |
| `quirk/cli/job_progress.py:31` | `update_job_stage` | 60% |
| `quirk/cli/job_progress.py:44` | `mark_job_completed` | 60% |
| `quirk/cli/job_progress.py:59` | `mark_job_failed` | 60% |
| `quirk/cli/job_progress.py:74` | `write_scan_checkpoint` | 60% |
| `quirk/cli/qramm_cmd.py:44` | `run_qramm_status` | 60% |
| `quirk/cli/schedule_cmd.py:141` | `run_schedule` | 60% |
| `quirk/cli/scheduler_cmd.py:195` | `run_scheduler` | 60% |

### Assessment / Utility Functions — May Warrant Review

| File | Line | Finding | Confidence | Notes |
|------|------|---------|------------|-------|
| `quirk/assessment/operator_context.py` | 32 | `prompt_for_context` | 60% | Interactive mode; may only be called in `--interactive` path |
| `quirk/assessment/operator_context.py` | 115 | `get_context` | 60% | Called from interactive mode or operator context init |
| `quirk/cbom/classifier.py` | 26 | `HYBRID` | 60% | Classifier enum member; may be unused or matched by string |
| `quirk/compliance/cmvp.py` | 101 | `is_cmvp_cache_stale` | 60% | Staleness check utility; may be called from CLI |
| `quirk/scanner/target_expander.py` | 18 | `expand_targets` | 60% | May be called from run_scan.py target expansion path |
| `quirk/util/optional_extra.py` | 151 | `is_extra_available` | 60% | Optional-extra helper; may be called from scanner setup |
| `quirk/util/optional_extra.py` | 170 | `select_nmap_port_list` | 60% | Nmap helper; may be called from scanner setup |
| `quirk/util/optional_extra.py` | 192 | `probe_missing_extras` | 60% | Doctor/health-check utility |
| `quirk/util/targets.py` | 243 | `maybe_confirm_probe_budget` | 60% | Interactive mode guard |
| `quirk/util/targets.py` | 297 | `apply_targets_file_override` | 60% | Targets file path override utility |
| `quirk/util/xml_safe.py` | 48 | `parse_safely` | 60% | XML safety helper; reachable from SAML/nmap parsers |
| `quirk/validate.py` | 50 | `_previous_intelligence` | 60% | May be used for delta scoring; check callers |

### Config Dataclass Fields — FALSE POSITIVES (attribute access via `cfg.`)

All `quirk/config.py` dataclass field "unused variables" are accessed via `cfg.<field>` in
`run_scan.py` and scanner modules. Vulture treats dataclass field defaults as variable
assignments and cannot track attribute access patterns.

| File | Lines | Finding |
|------|-------|---------|
| `quirk/config.py` | 31–48 | Timeout config fields (`jwt_seconds`, `container_seconds`, etc.) |
| `quirk/config.py` | 202–260 | Connector config fields (aws, azure, gcp, db, k8s, vault, broker, identity, smime) |

### Scanner Module Attributes — Review Before Any Action

| File | Line | Finding | Confidence | Notes |
|------|------|---------|------------|-------|
| `quirk/cli/scheduler_cmd.py` | 98, 160 | `scan_output_path` attribute | 60% | Scheduler result attribute; check if logged or returned |
| `quirk/scanner/broker_scanner.py` | 238 | `cert_sans` attribute | 60% | CryptoEndpoint field; may be read by CBOM builder |
| `quirk/scanner/email_scanner.py` | 229, 422 | `cert_sans` attribute | 60% | Same — CBOM builder reads endpoint attributes |
| `quirk/scanner/email_scanner.py` | 598 | `email_scan_json` attribute | 60% | Result attribute; may be logged |
| `quirk/scanner/tls_scanner.py` | 206, 421 | `cert_sans` attribute | 60% | CBOM builder reads endpoint attributes |
| `quirk/scanner/tls_scanner.py` | 387 | `vssock` local variable | 60% | Check if socket is closed/used after assignment |
| `quirk/scanner/kerberos_scanner.py` | 282, 288 | `tcp_error` local variable | 60% | Error variable may be used in finally/except block |
| `quirk/scanner/fingerprint.py` | 12 | `is_open` variable | 60% | Check fingerprint function logic |
| `quirk/scanner/broker_scanner.py` | 56, 60 | `ERROR`, `ERROR_NO_CONNECTIVITY` constants | 60% | Constants may be exported or compared in tests |
| `quirk/scanner/email_scanner.py` | 63, 67 | `ERROR`, `ERROR_NO_CONNECTIVITY` constants | 60% | Same |
| `quirk/scanner/adcs_scanner.py` | 39–45 | `POLICY_*` and `CT_FLAG_*` constants | 60% | ADCS protocol constants; may be used as bitmasks |
| `quirk/scanner/saml_scanner.py` | 51 | `SHA1_INDICATORS` | 60% | Set constant used in SAML weak-signing detection |

---

## Summary

| Confidence Band | Findings | Estimated True Dead | Action |
|-----------------|----------|--------------------|----|
| 100% | 6 | 1–3 (html_renderer else branch most likely) | Per-item review |
| 90% | 4 | 0–2 (optional-extra imports) | Per-item review with optional-extra audit |
| 60% | ~200+ | Low (dominated by scanner entry-point false positives) | Leave; note dynamic dispatch |

**Recommended next-action candidates (in priority order):**

1. `quirk/reports/html_renderer.py:110` — Unreachable `else` branch (100%, structural)
2. `quirk/scanner/azure_connector.py:22` / `quirk/scanner/gcp_connector.py:27` /
   `quirk/scanner/k8s_connector.py:37,75` — Optional-extra imports in try/except blocks
   (90%; confirm each is not re-exported or caught before removing)
3. `quirk/validate.py:50` `_previous_intelligence` — Worth a grep to confirm no callers

All other findings require significant reachability analysis before any deletion.
