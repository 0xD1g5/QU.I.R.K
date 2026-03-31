# Quantum Chaos Enterprise Lab (Chaos Lab)

A local simulated enterprise environment to generate realistic crypto + certificate findings for **Quantum Readiness** scanning and reporting.

## Quick Start

```bash
docker compose -p chaoslab -f docker-compose.yml \
  --profile phaseA --profile cloud --profile identity --profile pki up -d
```

## Documentation

The complete operator guide is at **[docs/chaos-lab.md](../docs/chaos-lab.md)** — covers all profiles including Phase 4 additions (jwt, registry, source, storage, ssh-weak, ldaps).

> **Historical artifact:** `CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md` in this directory is retained for reference but is no longer updated. The `docs/chaos-lab.md` guide is the authoritative reference.


## Phase C (mTLS + step-ca)

Generate and rotate short-lived certs, and restart the Phase C gateway automatically:

```bash
chmod +x scripts/phaseC_stepca_issue.sh
./scripts/phaseC_stepca_issue.sh
# loop:
./scripts/phaseC_stepca_issue.sh --loop --every-min 5
```
