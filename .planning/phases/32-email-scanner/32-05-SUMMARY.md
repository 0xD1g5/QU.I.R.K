---
phase: 32-email-scanner
plan: 05
status: complete
wave: 1
requirements: [EMAIL-11]
commits: [5677ae4, c6bfb88, 8bedb2b]
---

# Plan 32-05 — Email Chaos Lab Summary

## What was built

A Postfix + Dovecot Docker chaos lab under `labs/email/` exposed via
`quantum-chaos-enterprise-lab/docker-compose.yml` profile `email`. Designed to
serve weak TLS endpoints for QUIRK's Phase 32 email scanner (Plan 32-03) to
detect.

## Files

- `labs/email/Dockerfile` — single ubuntu:22.04 image with postfix +
  dovecot-imapd + dovecot-pop3d + openssl + ca-certificates installed.
  Default `CMD` runs Postfix in foreground; `dovecot-email` service in compose
  overrides `command:` to run Dovecot instead. **No supervisor / single-daemon
  per container** (deviation from plan — see below).
- `labs/email/Makefile` — `make certs` target generates RSA-2048 self-signed
  certs reproducibly (postfix.crt/.key, dovecot.crt/.key under `certs/`).
- `labs/email/postfix/main.cf` — Postfix TLS config with TLS 1.2 protocol cap
  (`smtpd_tls_protocols = TLSv1.2`, `smtpd_tls_mandatory_protocols = TLSv1.2`),
  cipher excludes for ECDHE/EDH/DHE (forces non-PFS RSA key exchange), and
  `smtpd_relay_restrictions = reject_unauth_destination` (Postfix 3.6
  requirement; not in original plan).
- `labs/email/postfix/master.cf` — services for SMTP (25), SMTPS (465 with
  `smtpd_tls_wrappermode=yes`), submission (587), plus the `postlog` service
  required by Postfix 3.4+ (not in original plan).
- `labs/email/dovecot/dovecot.conf` — IMAP + POP3 protocols, multi-line
  `inet_listener` blocks (Dovecot rejects inline `{ port = 143 }`), static
  passdb/userdb stubs.
- `labs/email/dovecot/10-ssl.conf` — `ssl_min_protocol = TLSv1.2` plus weak
  cipher list (AES128-SHA, AES256-SHA, !ECDHE/!DHE/!EDH).
- `labs/email/dovecot/openssl-tls12-only.cnf` — system OpenSSL config attempted
  to cap MaxProtocol at TLSv1.2 for the Dovecot process via `OPENSSL_CONF` env.
  **Found inert in Dovecot 2.3.16** (see Known Limitation).
- `labs/email/.gitignore` — excludes generated certs.
- `labs/email/README.md` — operator-facing runbook (quick start, port table,
  TLS posture description).
- `quantum-chaos-enterprise-lab/docker-compose.yml` — appended `postfix-email`
  and `dovecot-email` services under `profiles: ["email"]`. Each service uses
  the same image but a different `command:` so cert mounts and OPENSSL_CONF
  apply only to the relevant daemon.

## Verification

- `make -C labs/email certs` exits 0 and produces 4 cert files; postfix.crt /
  dovecot.crt are RSA Public-Key (2048 bit). OpenSSL used at cert generation:
  `OpenSSL 3.6.2 7 Apr 2026` (host).
- `python3 -c "import yaml; yaml.safe_load(...)"` validates the compose file
  (61 services total).
- `docker compose --profile email up -d --build` builds both services and they
  reach `healthy` within ~30 s.
- All 7 ports respond:
  - 30025/30465/30587 → postfix-email
  - 30143/30993/30110/30995 → dovecot-email
- TLS handshake captured during the human-verify checkpoint:
  - Postfix SMTPS 30465 default: `Protocol: TLSv1.2`, `Cipher: AES256-GCM-SHA384`
    (Kx=RSA, non-PFS) — matches the lab's intent for weak-cipher detection.
  - Postfix STARTTLS 30025: same.
  - Dovecot IMAPS 30993 default: `Protocol: TLSv1.3` (see Known Limitation),
    forced TLS 1.2: `Cipher: AES128-SHA` (RSA Kx, non-PFS).
  - Dovecot POP3S 30995: same as IMAPS.
- Both certs present `subject=CN=postfix.chaos.local` and
  `subject=CN=dovecot.chaos.local` respectively, with `Verify return code: 18
  (self-signed certificate)`.

## Deviations from PLAN.md

1. **Single-daemon-per-container (no supervisor).** PLAN.md showed a supervisor
   config running both Postfix + Dovecot in each container. That created a
   cert-mount mismatch (the postfix-email container only mounts postfix certs,
   so its dovecot daemon crashed on missing dovecot.crt) and pollutes logs.
   Replaced with `command:` overrides in compose so each container runs its
   own daemon. Same image, different entrypoint per service.

2. **Three Postfix 3.6 requirements added that the plan didn't include:**
   - `postlog unix-dgram` service in master.cf (required since Postfix 3.4)
   - `smtpd_relay_restrictions = reject_unauth_destination` (required in 3.6+)
   - Hard cap `smtpd_tls_protocols = TLSv1.2` (the plan's `!SSLv2, !SSLv3`
     allow-list left TLS 1.3 enabled, which would have bypassed the cipher
     excludes since TLS 1.3 ciphers are PFS by definition).

3. **Dovecot config syntax fixes** — the plan's
   `inet_listener imap { port = 143 }` is rejected by Dovecot 2.3.16; expanded
   to multi-line blocks. Added `passdb`/`userdb` static stubs so Dovecot
   doesn't refuse to start.

## Known Limitation — Dovecot TLS 1.3 default

Dovecot 2.3.16 (Ubuntu 22.04 stock) calls `SSL_CTX_set_min_proto_version()`
based on `ssl_min_protocol = TLSv1.2` but never calls
`set_max_proto_version()`. It also does not call `SSL_CTX_config()`, so the
`MaxProtocol = TLSv1.2` we set via `OPENSSL_CONF=/etc/dovecot/openssl-tls12-only.cnf`
is inert for the Dovecot process. Result: Dovecot defaults to TLS 1.3 when the
client offers it.

**Why this is acceptable for the lab's purpose:**
The QUIRK email scanner enumerates cipher suites at multiple TLS versions. When
the scanner pins TLS 1.2 (which any cipher-enumeration scan does), Dovecot
serves AES128-SHA with RSA key exchange — exactly the weak-cipher finding the
lab is designed to surface. The TLS 1.3 default path is orthogonal: it
represents the strongest negotiated path and doesn't hide the weak path.

**To strictly cap Dovecot at TLS 1.2** (if needed in future): add an stunnel
sidecar that terminates TLS 1.2 only and forwards plaintext to Dovecot, OR
upgrade to Dovecot 2.4+ which supports `ssl_max_protocol`.

## Checkpoint approval

User invoked the plan's "approved with caveat" path. The lab is GREEN for the
EMAIL-11 requirement (weak TLS exposed, scanner-detectable) with the
documented Dovecot 2.3.16 default-TLS-1.3 deviation.

## Next plan

Plan 32-03 (Wave 2) — implements `quirk/scanner/email_scanner.py`, which moves
the 16 currently-skipped tests from RED to GREEN.
