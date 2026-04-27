# Phase 32: Email Scanner - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 32-email-scanner
**Areas discussed:** Target input UX, Default profile inclusion, Stdlib fallback trigger, Findings composition + chaos lab layout

---

## Target input UX

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse target list, probe email ports per host | Every host already in the TLS target list is also probed on the 7 email ports. Zero new CLI surface. Scanner skips ports gracefully on CONNECTION_REFUSED. Matches dnssec_scanner v4.2 pattern. | ✓ |
| Dedicated `--email-target` flag | User explicitly opts in: `--email-target mail.example.com`. Cleaner separation, but requires consultants to remember a separate flag. | |
| MX autodiscovery from domain | User passes `example.com`; `target_expander.py` resolves MX records and feeds resulting hostnames into the email scanner. Most ergonomic, but introduces DNS resolution into the scan path. | |
| Reuse list + opt-in MX expansion | Default = reuse target list. Add `--expand-mx` flag for consultants who want domain-level discovery. | |

**User's choice:** Reuse target list, probe email ports per host.
**Notes:** MX autodiscovery captured as deferred idea — belongs in `target_expander.py`, not the scanner, and likely future v4.5 work.

---

## Default profile inclusion

| Option | Description | Selected |
|--------|-------------|----------|
| standard + deep only | `quick` stays fast (HTTPS/TLS + SSH only); `standard` and `deep` add the 7 email ports. Matches v4.2 dnssec inclusion pattern. | ✓ |
| All three profiles | Email ports probed on every scan, including `--profile quick`. ~2-3x slower for fast triage. | |
| deep only | Email scanning is deep-profile only; standard skips it. | |
| Opt-in flag, no profile inclusion | Email never runs from a profile alone — requires `--include-email`. | |

**User's choice:** standard + deep only.
**Notes:** Wiring lives in `quirk/engine/profiles.py:apply_profile()`. `quick` keeps `cfg.scanners.email_enabled = False`.

---

## Stdlib fallback trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Sslyze exception OR error status | Fallback on uncaught exception, `ServerScanStatusEnum.ERROR_*`, or all `ScanCommandAttempt` entries reporting ERROR. Empty results without explicit error = "TLS not supported", not fallback-triggering. | ✓ |
| Any non-success outcome | Fallback whenever sslyze doesn't return a fully populated cert+cipher+TLS-version. Doubles scan time on legitimately-empty results. | |
| Only TimeoutError + ConnectionResetError | Strict transport-level only. May miss handshake-stage failures. | |
| Always run both, prefer sslyze | Run sslyze and stdlib in parallel; merge results. Maximum data, ~2x scan time, complex reconciliation. | |

**User's choice:** Sslyze exception OR error status.
**Notes:** Mirrors `tls_scanner.py:329 _scan_one_fallback` behavior. Empty cipher results without ERROR status are interpreted as "TLS not supported" and do not trigger fallback.

---

## Findings composition (port 25 + weak cipher)

| Option | Description | Selected |
|--------|-------------|----------|
| Layered: emit both | `starttls-downgrade-risk` MEDIUM (always) + `weak-cipher` HIGH (separate). EMAIL-08 says "additional" — implies layered. Each finding has distinct remediation guidance. | ✓ |
| Single composite finding | One HIGH finding combining both risks. Cleaner UX but loses remediation specificity. | |
| Downgrade-risk only on plaintext-fallback | Suppress downgrade-risk MEDIUM when a HIGH cipher finding fires. Reduces noise but contradicts EMAIL-08's "regardless" language. | |

**User's choice:** Layered: emit both.
**Notes:** Dashboard de-dupes by `finding_id`, not by endpoint. "Enforce TLS" and "rotate ciphers" are distinct remediation conversations.

---

## Chaos lab layout

| Option | Description | Selected |
|--------|-------------|----------|
| `labs/email/` + fresh self-signed cert per service | Matches `labs/storage|kubernetes|vault` convention. Postfix and Dovecot each get their own openssl-generated RSA-2048 cert under `labs/email/certs/`. Reproducible from scratch via Makefile. | ✓ |
| `labs/email/` + reuse `certs/scenarios/` | Lives in `labs/email/` but mounts existing self-signed certs from `certs/scenarios/`. Less duplication, couples chaos lab to legacy CA. | |
| Merge into `quantum-chaos-enterprise-lab/docker-compose.yml` | Add postfix+dovecot under profile `email`. Single compose to manage, breaks `labs/` convention. | |

**User's choice:** `labs/email/` + fresh self-signed cert per service.
**Notes:** Decoupled from `certs/scenarios/`. CI / fresh checkouts can regenerate certs without manual openssl invocation.

---

## Claude's Discretion

- Internal helper organization inside `email_scanner.py` (one function per protocol vs. shared dispatcher).
- Logging verbosity for per-port refusals and per-fallback events.
- Whether to add `--include-email` / `--no-email` override flags during planning.
- `email_scan_json` payload shape — flat vs. per-port nested.
- `[motion]` extras content for Phase 32 (likely empty or sslyze-only since stdlib is already vendored).

## Deferred Ideas

- MX autodiscovery from a domain — `target_expander.py`, future milestone.
- Active STARTTLS-stripping detection — out of scope for an agentless scanner; document in finding description.
- Broker scanning (Phase 33), motion subscore wiring (Phase 34), CBOM integration (Phase 35), dashboard motion tab (Phase 36).
