# Phase 41 Timeout & Retry Audit (ROBUST-04)

This document is the canonical audit trail for QU.I.R.K.'s per-scanner timeout and retry policy as
of v4.5 (Phase 41 — CI Stability & Scanner Robustness). Every scanner reads its connection timeout
and retry/backoff policy from a single source of truth: the `TimeoutsCfg` and `RetryCfg` dataclasses
on `ScanCfg` in `quirk/config.py`. Hardcoded timeout literals and ad-hoc retry loops were removed
in Phase 41 Plan 03; this table reflects the post-refactor state.

The retry policy is uniform across all scanners: `retry_count=0`, `backoff_base_seconds=1.0`,
`backoff_max_seconds=5.0` (Phase 41 Plan 02). Per-scanner retry overrides are not currently
exposed — callers needing aggressive retry behavior should set `cfg.scan.retry.retry_count` and
the backoff bounds globally.

## Per-scanner audit table

| Scanner | Timeout slot | Default (s) | Retry count | Backoff base (s) | Backoff max (s) | Canonical source |
|---------|--------------|-------------|-------------|------------------|-----------------|------------------|
| fingerprint | `fingerprint_seconds` | 4 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.fingerprint_seconds` |
| tls | `tls_seconds` | 6 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.tls_seconds` |
| ssh | `ssh_seconds` | 6 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.ssh_seconds` |
| jwt | `jwt_seconds` | 10 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.jwt_seconds` |
| container | `container_seconds` | 120 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.container_seconds` |
| source | `source_seconds` | 300 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.source_seconds` |
| dnssec | `dnssec_seconds` | 10 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.dnssec_seconds` |
| saml | `saml_seconds` | 10 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.saml_seconds` |
| kerberos | `kerberos_seconds` | 10 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.kerberos_seconds` |
| vault | `vault_seconds` | 10 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.vault_seconds` |
| db_pg | `db_connect_seconds` | 5 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.db_connect_seconds` |
| db_mysql | `db_connect_seconds` | 5 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.db_connect_seconds` |
| broker_kafka | `broker_seconds` | 10 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.broker_seconds` |
| broker_rabbitmq | `broker_seconds` | 10 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.broker_seconds` |
| broker_redis | `broker_seconds` | 10 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.broker_seconds` |
| email | `email_seconds` | 10 | 0 | 1.0 | 5.0 | `cfg.scan.timeouts.email_seconds` |

## Notes

- **Default fallback:** Any code path that needs a generic socket timeout uses
  `cfg.scan.timeouts.default_seconds` (default 5s). All scanner-specific paths above use their
  dedicated slot.
- **Database scanners (`db_pg`, `db_mysql`):** Both share the `db_connect_seconds` slot; the
  underlying drivers (`psycopg2`, `pymysql`) accept the same connect-timeout semantics.
- **Broker scanners (`broker_kafka`, `broker_rabbitmq`, `broker_redis`):** All three share
  `broker_seconds`. Per-broker tuning was considered and deferred — the 10s default works for
  every probe pattern in the chaos lab.
- **Container / source scanners:** These run against in-process images / repos and therefore
  carry significantly higher timeouts (120s and 300s respectively). They are the dominant terms
  in the upper-bound formula when those connectors are enabled.
- **Retry policy (`retry_count=0`):** Phase 41's default is no retry — scanners report a
  `ScanError` row on first-attempt failure rather than retrying. Operators with flaky network
  conditions can raise `cfg.scan.retry.retry_count` globally; exponential backoff between retries
  is bounded by `backoff_base_seconds` (initial) up to `backoff_max_seconds` (ceiling).

## Source-of-truth chain

Every scanner reads from the canonical `TimeoutsCfg` / `RetryCfg`. Legacy hardcoded literals were
removed in Phase 41 Plan 03 (`feat({phase}-03)`-tagged commits in `quirk/scanner/`,
`quirk/discovery/`, and connector modules). The four legacy flat fields on `ScanCfg`
(`timeout_seconds`, `fingerprint_timeout_seconds`, `tls_timeout_seconds`, `ssh_timeout_seconds`)
remain as `@property` aliases that emit `DeprecationWarning` on read and route to the canonical
sub-table — see `quirk/config.py` and [`docs/configuration.md`](configuration.md) §"Timeout &
Retry Policy (v4.5+)".

---

*Phase: 41-ci-stability-scanner-robustness*
*Plan: 06*
*Updated: 2026-04-29*
