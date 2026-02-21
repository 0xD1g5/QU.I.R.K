# Quantum Chaos Enterprise Lab (Chaos Lab)

A local simulated enterprise environment to generate realistic crypto + certificate findings for **Quantum Readiness** scanning and reporting.

## Quick Start

```bash
docker compose -p chaoslab -f docker-compose.yml \
  --profile phaseA --profile cloud --profile identity --profile pki up -d
```

## Documentation

- See **CHAOS_LAB_BUILD_AND_OPERATIONS.md** for the full build guide + operator manual.


## Phase C (mTLS + step-ca)

Generate and rotate short-lived certs, and restart the Phase C gateway automatically:

```bash
chmod +x scripts/phaseC_stepca_issue.sh
./scripts/phaseC_stepca_issue.sh
# loop:
./scripts/phaseC_stepca_issue.sh --loop --every-min 5
```
