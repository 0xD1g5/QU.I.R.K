# Phase 33 — Broker Scanner Expected Results

**Lab:** apache/kafka:3.6 + rabbitmq:3.12-management + redis:7-alpine (Docker Compose profile `broker`)
**Phase:** 33 — Broker TLS Scanner
**Requirements:** BROKER-LAB-01, BROKER-LAB-02
**Last updated:** 2026-04-27
**Image source:** Official images per CONTEXT.md D-15 (2026-04-27 revision) — Bitnami images cannot
configure cipher suites via env vars; only official images support the cipher-level control needed
for Success Criterion 4 (weak-cipher HIGH on ≥2 brokers).

## Lab Setup

Generate self-signed RSA-2048 certs, then start the broker profile:

```bash
cd labs/broker
make certs                      # generates certs/{kafka,rabbitmq,redis}.{crt,key}
cd ../../quantum-chaos-enterprise-lab
docker compose --profile broker up -d
```

Wait ~30s for all three healthchecks to pass:

```bash
docker compose --profile broker ps
```

Expected status:

```
kafka-broker      Up (healthy)   0.0.0.0:29092->29092/tcp, 0.0.0.0:29093->29093/tcp
rabbitmq-broker   Up (healthy)   0.0.0.0:25672->5672/tcp,  0.0.0.0:25671->5671/tcp
redis-broker      Up (healthy)   0.0.0.0:26379->6379/tcp,  0.0.0.0:26380->6380/tcp
```

Boot the QU.I.R.K. scan with broker scanning enabled (standard profile auto-enables broker):

```bash
quirk scan --target localhost --profile standard
```

## Port Map

| External | Container | Service | Protocol | Notes |
|----------|-----------|---------|----------|-------|
| 29092 | 29092 | Kafka plaintext | KAFKA-PLAIN | Intentionally listening |
| 29093 | 29093 | Kafka TLS | KAFKA-TLS | Weak non-PFS RSA ciphers |
| 25672 | 5672 | RabbitMQ AMQP | AMQP-PLAIN | Intentionally listening |
| 25671 | 5671 | RabbitMQ AMQPS | AMQPS | Weak ciphers: DES-CBC3-SHA etc. |
| 26379 | 6379 | Redis plaintext | REDIS-PLAIN | Intentionally listening |
| 26380 | 6380 | Redis TLS | REDIS-TLS | Weak ciphers: DES-CBC3-SHA etc. |

## Expected Scan Output

| port  | protocol            | tls_version | cipher_suite                           | finding                    | severity |
|-------|---------------------|-------------|----------------------------------------|----------------------------|----------|
| 29092 | KAFKA-PLAIN         | -           | -                                      | kafka-plaintext-listener   | HIGH     |
| 29093 | KAFKA-TLS           | TLSv1.2     | TLS_RSA_WITH_AES_128_CBC_SHA           | weak-cipher                | HIGH     |
| 25672 | AMQP-PLAIN          | -           | -                                      | amqp-plaintext-listener    | HIGH     |
| 25671 | AMQPS               | TLSv1.2     | DES-CBC3-SHA / AES128-SHA / AES256-SHA | weak-cipher                | HIGH     |
| 26379 | REDIS-PLAIN         | -           | -                                      | redis-plaintext-no-auth    | HIGH     |
| 26380 | REDIS-TLS           | TLSv1.2     | DES-CBC3-SHA / AES128-SHA / AES256-SHA | weak-cipher                | HIGH     |

**Success criteria for the lab (per ROADMAP Phase 33 SC4):**
- Plaintext HIGH on all three brokers (ports 29092, 25672, 26379)
- Weak-cipher HIGH on at least 2 of 3 TLS broker ports (29093, 25671, 26380)

## Expected Findings

`evaluate_broker_endpoints(endpoints)` returns the following findings against the captured
endpoint list:

| Severity | Title                                              | Port  | Source |
|----------|----------------------------------------------------|-------|--------|
| HIGH     | Kafka plaintext listener detected                  | 29092 | KAFKA-02 |
| HIGH     | Weak cipher suite on broker TLS endpoint           | 29093 | KAFKA-01 + weak-cipher |
| HIGH     | AMQP plaintext listener detected                   | 25672 | RABBIT-02 |
| HIGH     | Weak cipher suite on broker TLS endpoint           | 25671 | RABBIT-01 + weak-cipher |
| HIGH     | Redis plaintext listener (no authentication)       | 26379 | REDIS-02 |
| HIGH     | Weak cipher suite on broker TLS endpoint           | 26380 | REDIS-01 + weak-cipher |

**Severity counts:** HIGH = 6 (3 plaintext + 3 weak-cipher).
**D-11 layering verified:** each broker host can emit BOTH a plaintext-listener HIGH (from
plaintext-port detection) AND a weak-cipher HIGH (from TLS-port enumeration), because the
(host, port, title) dedup keys are distinct.

## Verification

After running a scan, query the database to confirm findings:

```bash
sqlite3 quirk.db "SELECT host, port, protocol, cipher_suite FROM crypto_endpoints WHERE port IN (29092,29093,25672,25671,26379,26380)"
```

Verify the `broker_scan_json` nested payload on the first broker endpoint:

```bash
sqlite3 quirk.db "SELECT json_extract(broker_scan_json, '$.kafka') FROM crypto_endpoints WHERE broker_scan_json IS NOT NULL LIMIT 1"
```

The `broker_scan_json` column on the first broker endpoint contains a nested dict with keys
`kafka`, `rabbitmq`, `redis`, `azure_servicebus`, `aws_sqs` (per D-12).

Direct scanner invocation for lab validation (no full pipeline required):

```python
from quirk.scanner.broker_scanner import (
    scan_kafka_targets, scan_rabbitmq_targets, scan_redis_targets,
)
from quirk.engine.risk_engine import evaluate_broker_endpoints

all_eps = (
    scan_kafka_targets(hosts=["localhost"], timeout=8)
    + scan_rabbitmq_targets(hosts=["localhost"], azure_namespaces=[], sqs_regions=[], timeout=8)
    + scan_redis_targets(hosts=["localhost"], timeout=8)
)
findings = evaluate_broker_endpoints(all_eps)
for f in findings:
    print(f["severity"], f["port"], f["title"])
```

## Caveats

### Kafka server.properties mount path

`apache/kafka:3.6` reads config from `/etc/kafka/server.properties` by default. The Compose bind
mount provides the weak-TLS `server.properties` at that path. If the Kafka container does not pick
up the config (check `docker logs kafka-broker`), the PEM keystore path
(`ssl.keystore.location=/etc/kafka/secrets/kafka.keystore.pem`) may need adjustment — the PEM
keystore format requires the cert + key in one file. See Plan 33-07 SUMMARY.md for details.

### RabbitMQ TLS 1.0 limitation

`ssl_options.versions.tlsv1` is intentionally omitted from `rabbitmq.conf`. Modern OpenSSL and
Erlang OTP 25+ (used by rabbitmq:3.12) reject TLS 1.0 as a hard error. TLS 1.1 + TLS 1.2 with
weak ciphers (DES-CBC3-SHA, AES128-SHA, AES256-SHA) is sufficient to trigger weak-cipher HIGH.

### Redis TLS cipher availability

`DES-CBC3-SHA` may not be negotiable if the scanner host's OpenSSL 3.x has disabled 3DES via the
security policy. In that case the scanner falls back to `AES128-SHA` or `AES256-SHA` — both still
fire weak-cipher HIGH. The `DES-CBC3-SHA` cipher is offered by the server and detected by sslyze's
cipher enumeration regardless of client-side policy.

### Port binding on macOS

The Kafka container listens internally on ports 29092/29093 (not 9092/9093). The scanner's default
Kafka port list targets 9092/9093. For end-to-end validation via `run_scan.py`, ensure the broker
target config uses the lab's host ports (29092/29093 etc.) or configure port forwarding.

## Tear-Down

```bash
docker compose --profile broker --file quantum-chaos-enterprise-lab/docker-compose.yml down
make -C labs/broker clean      # remove generated certs
```
