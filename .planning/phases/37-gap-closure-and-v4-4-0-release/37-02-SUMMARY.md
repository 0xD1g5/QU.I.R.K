---
phase: 37
plan: 02
status: complete
requirements: [INFRA-02, STRUCT-02, STRUCT-03]
created: 2026-04-29
---

# Plan 37-02 Summary — [motion] Meta-Extra Topology

## Outcome
INFRA-02 satisfied: `pip install quirk[motion]` is the single happy path. `[motion]`
is now a meta-extra referencing flat sub-extras `[email]`, `[broker]`, `[kafka]`.

## Import Inventory (Task 1)

### `quirk/scanner/email_scanner.py`
- stdlib: `json`, `ssl`, `socket`, `smtplib`, `imaplib`, `poplib`, `concurrent.futures`, `datetime`, `typing`
- core deps: `cryptography` (already in `[project.dependencies]`)
- conditional: `sslyze` (optional, also used by `tls_scanner` — covered by core)
- internal: `quirk.models`, `quirk.logging_util`, `quirk.scanner.tls_scanner`

→ `[email]` has zero non-core dependencies. Declared as `email = []` (placeholder so the
  meta-extra resolves cleanly per D-02).

### `quirk/scanner/broker_scanner.py`
- stdlib: `base64`, `json`, `socket`, `ssl`, `urllib.error`, `urllib.request`, `concurrent.futures`, `datetime`, `typing`
- core deps: `cryptography`
- conditional optional: `kafka.admin` → `kafka-python` (already pinned in `[kafka]`)
- conditional optional: `redis` → `redis>=5.0` (REDIS-03 enrichment)
- RabbitMQ probing uses raw socket + AMQP header bytes — **no `pika`** required (CONTEXT.md note was a research-time guess; D-02 inventory is authoritative)

→ `[broker]` declared as `broker = ["redis>=5.0"]`. `kafka.admin` continues to live in `[kafka]`.

### Forbidden imports audit
`grep -c 'pika\|confluent_kafka\|aiokafka' email_scanner.py broker_scanner.py` → `0` matches.

## Files Modified
- `pyproject.toml` — `[project.optional-dependencies]` block:

```toml
motion = ["quirk[email]", "quirk[broker]", "quirk[kafka]"]
email = []
broker = ["redis>=5.0"]
kafka = ["kafka-python>=2.0"]
redis = ["redis>=5.0"]
```

## Verification
- `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` → exit 0
- TOML structural assertions (motion list, email empty, broker contains redis>=5.0, kafka unchanged) → all pass
- `pytest --collect-only -q` → `652 tests collected in 0.60s`

## Commits
- `feat(37-02): make [motion] a meta-extra over [email]+[broker]+[kafka] (INFRA-02)`
