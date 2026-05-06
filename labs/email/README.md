# Email Chaos Lab (Phase 32)

Postfix + Dovecot lab with intentionally weak TLS for QU.I.R.K. scanner validation.

## Quick start

```bash
make -C labs/email certs
docker compose --profile email --file quantum-chaos-enterprise-lab/docker-compose.yml up -d
quirk scan --target localhost --ports 30025,30465,30587,30143,30993,30110,30995
docker compose --profile email --file quantum-chaos-enterprise-lab/docker-compose.yml down
```

## Ports

| External | Service | Notes |
|----------|---------|-------|
| 30025 | SMTP (STARTTLS) | starttls-downgrade-risk MEDIUM expected |
| 30465 | SMTPS | implicit TLS |
| 30587 | SMTP submission (STARTTLS) | |
| 30143 | IMAP (STARTTLS) | |
| 30993 | IMAPS | |
| 30110 | POP3 (STLS) | |
| 30995 | POP3S | |

## TLS posture (intentionally weak)

- TLS 1.2 minimum (OpenSSL 3.x on scanner won't negotiate TLS 1.0/1.1 anyway)
- Non-PFS RSA key exchange — ECDHE/EDH/DHE excluded
- Cipher allowlist: AES128-SHA, AES256-SHA
- RSA-2048 self-signed certs (regenerate via `make certs`)

## Expected findings

See `expected_results.md` (added in Plan 32-06).
