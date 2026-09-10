# Ad-Hoc Lab Scan Configs

These are ad-hoc **scan client** configs for re-running QU.I.R.K. scans against this lab's Docker
Compose profiles. They are passed via `run_scan.py --config <path>` — they are not chaos-lab
Compose profile definitions, so adding, editing, or removing one does **not** trigger CLAUDE.md's
"Chaos Lab Maintenance" rule (no `lab.sh` `ALL_PROFILES`, `expected_results_*.md`, or lab README
update is required for changes to this directory).

## Files

- `config-lab-core.yaml` — always-on `core` profile baseline scan (17-port `CONSULTING_TLS_PORTS`
  default), output to `./quirk-output`.
- `config-lab-broker190.yaml` — Phase 190 broker connector scan with `broker_targets` set
  (Kafka/RabbitMQ/Redis endpoints), `enable_broker: true`.
- `config-lab-broker190-baseline.yaml` — Phase 190 broker connector baseline, `enable_broker: true`
  with no `broker_targets`, for before/after comparison against `config-lab-broker190.yaml`.
- `config-lab-otics190.yaml` — Phase 190 OT/ICS Modbus re-verification scan.
- `config-lab-191-reuse.yaml` — Phase 191 SPKI key-reuse checkpoint, "reuse" run (ports
  8990-8992).
- `config-lab-191-noreuse.yaml` — Phase 191 SPKI key-reuse checkpoint, "no-reuse" run (same ports,
  distinct keys per target).
