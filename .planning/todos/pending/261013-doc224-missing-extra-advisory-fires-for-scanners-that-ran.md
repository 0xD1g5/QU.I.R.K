---
type: todo
created: 2026-10-13
source: Phase 224 GC3 (REST3) wording sweep; ledger rows DCL-CONN-GCP-0021, DCL-CONN-VAULT-0026, DCL-CONN-DB-0030 (docs/connectors/gcp.md, vault.md, db.md)
priority: medium
area: quirk/util/optional_extra.py (REGISTRY cloud and db entries, probe_missing_extras)
status: pending
resolves_phase: null
owner: "999.127"
---

# The `cloud` and `db` missing-extra advisories claim a scan was skipped when it ran

`probe_missing_extras` (`quirk/util/optional_extra.py:204-244`) emits one ADVISORY row per registry entry when any
of the entry's `enabled_attrs` is on and **not all** of its `modules` import. Two entries group scanners that
`run_scan.py` gates separately, so the advisory text is false for the scanner that did run:

- `cloud` (`optional_extra.py:99-107`): modules `googleapiclient`, `kubernetes`, `hvac`; enabled by
  `enable_gcp` / `enable_k8s` / `enable_vault`; text "GCP / Kubernetes / HashiCorp Vault scanning skipped".
- `db` (`optional_extra.py:89-97`): modules `psycopg2`, `pymysql`; text "Database TLS scanning (PostgreSQL/MySQL)
  skipped". `run_scan.py:3400` runs the phase when either driver imports.

Live probes (isolated HOME, env -i, real scan of 127.0.0.1:1, `--verbose`):
`work/probes/gc3-rest3-advisory-granularity-probe.sh` in the phase directory:
- `enable_vault` with `hvac` installed but `googleapiclient` absent -> stderr `[QRK-INSTALL-001]`, ADVISORY row
  "GCP / Kubernetes / HashiCorp Vault scanning skipped ...", while `vault_scanning|ran` and the Vault scan produced an
  endpoint.
- `enable_k8s` with `kubernetes` installed, `googleapiclient` absent -> same advisory, `k8s_scanning|ran`.
- `gc3-rest3-connector-skip-probe.sh` db-pg-only-missing (`psycopg2` absent, `PyMySQL` present) -> "Database TLS
  scanning (PostgreSQL/MySQL) skipped" advisory while `db_scanning|ran`.

- [ ] Split the `cloud` entry per scanner (gcp / k8s / vault, each gated on its own `enable_*` and module), or key
      the advisory on the specific missing module and enabled toggle.
- [ ] Give `db` OR semantics (advise only when neither driver imports), or name the missing driver.
- [ ] Update `tests/test_optional_extra.py` and re-check docs/connectors/gcp.md and vault.md "Graceful Degradation".

## Feasibility & Effort

- **CONFIRMED** behaviour: the gating loop is `quirk/util/optional_extra.py:228-235` (any enabled attr; all modules
  must import), and the three live probes above show the advisory beside a `ran` phase record.
- **CONFIRMED** the per-phase gates differ: `run_scan.py:3376` (GCP_AVAILABLE only), `run_scan.py:3800`
  (HVAC_AVAILABLE only), k8s has no pre-gate (`run_scan.py:3561` comment), db is OR (`run_scan.py:3400`).
- Effort **S**: registry data change plus test updates. Unknown: whether the dashboard reads these advisory rows by
  `scanner_label` (`grep -rn cloud_connectors src/dashboard` before renaming).
