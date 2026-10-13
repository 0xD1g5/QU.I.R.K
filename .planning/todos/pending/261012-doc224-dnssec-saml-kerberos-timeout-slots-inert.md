---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-CONFIG-A-* (configuration.md Timeout & Retry Policy)
priority: medium
area: run_scan.py (DNSSEC, SAML, Kerberos phases), quirk/config.py (TimeoutsCfg)
status: pending
resolves_phase: null
---

# scan.timeouts.dnssec_seconds / saml_seconds / kerberos_seconds are never read

`TimeoutsCfg` declares `dnssec_seconds`, `saml_seconds` and `kerberos_seconds` (default 10 each), and the dashboard job
overlay can set them, but the three scanner phases in `run_scan.py` call
`getattr(cfg.connectors, "dnssec_timeout", 10)`, `getattr(cfg.connectors, "saml_timeout", 10)` and
`getattr(cfg.connectors, "kerberos_timeout", 10)`. `ConnectorsCfg` defines none of those three fields (confirmed with
`dataclasses.fields(ConnectorsCfg)`), and `config_from_dict` drops unknown connector keys with a warning, so the
timeout is always the literal 10. `docs/timeout-retry-audit.md` and the old `docs/configuration.md` both claimed the
scanners read the `scan.timeouts` slots. `docs/configuration.md` now says the three slots have no effect.

- [ ] Read `cfg.scan.timeouts.dnssec_seconds` / `saml_seconds` / `kerberos_seconds` in the three phases (like the
      jwt/container/source phases do at `run_scan.py` `timeout=cfg.scan.timeouts.jwt_seconds`).
- [ ] Add a test that sets a non-default slot and asserts the scanner received it.
- [ ] Then remove the "not read" notes from `docs/configuration.md` and correct `docs/timeout-retry-audit.md`.

## Feasibility & Effort

**CONFIRMED** (`grep -rn "dnssec_seconds\|saml_seconds\|kerberos_seconds" run_scan.py quirk` returns only the dataclass
and dashboard-overlay hits; the three `getattr(cfg.connectors, ...)` lines are at `run_scan.py` DNSSEC/SAML/Kerberos
phases). Effort **S**: three one-line changes plus a test. No unknowns; no spike needed.
