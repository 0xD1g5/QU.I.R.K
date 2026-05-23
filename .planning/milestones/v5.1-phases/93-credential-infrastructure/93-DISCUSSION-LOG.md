# Phase 93: Credential Infrastructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-22
**Phase:** 93-credential-infrastructure
**Areas discussed:** Credential input & argv-leak UX, Zeroization rigor, Security-review gate deliverable, Phase-93 credential consumption scope

---

## Credential input & argv-leak UX

### Q1 — How should the CLI accept credentials (argv-leak risk)?

| Option | Description | Selected |
|--------|-------------|----------|
| Flags take a reference, not the secret | `--auth-bearer` triggers a prompt or reads an env var / `@file`; raw token never an argv value | ✓ |
| Allow inline secret + warn | Accept `--auth-bearer <token>` but emit a security warning | |
| Allow inline, document risk only | No runtime warning; caveat in docs | |

**User's choice:** Flags take a reference, not the secret.
**Notes:** Reuse v4.8 Phase 58 hardened `@file` reader + path-traversal guard.

### Q2 — Source precedence when multiple present?

| Option | Description | Selected |
|--------|-------------|----------|
| Prompt > env > flag-ref | Interactive prompt overrides env overrides flag reference | ✓ |
| Flag > env > prompt | Explicit flag wins (research-suggested order) | |
| Env > flag > prompt | Environment wins (CI-style) | |

**User's choice:** Prompt > env > flag-ref.
**Notes:** Favors the most-deliberate, least-loggable source.

---

## Zeroization rigor

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid: bytearray core, str only at inject | bytearray in CredentialContext, overwrite in finally, str only at httpx boundary | ✓ |
| Full bytearray everywhere | bytearray end-to-end; max rigor, more plumbing, diminishing returns | |
| str + documented best-effort | plain str; spend effort on leak-surface scrubbing instead | |

**User's choice:** Hybrid — bytearray core, str only at injection point.
**Notes:** Best-effort nature documented honestly in the AUTH-04 gate regardless.

---

## Security-review gate deliverable (AUTH-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Both: checklist doc + automated leak tests | Markdown 11-surface audit PLUS automated leak-detection test suite | ✓ |
| Automated leak-test suite only | Tests only; no narrative audit | |
| Markdown audit checklist only | Human-reviewed doc only; no new automated tests | |

**User's choice:** Both — markdown audit + automated leak tests.
**Notes:** Doc proves reasoning; tests prevent regression. Must be GREEN before any later phase sends authenticated live traffic.

---

## Phase-93 credential consumption scope

| Option | Description | Selected |
|--------|-------------|----------|
| Wire into existing API/JWT scanner | CredentialContext built AND Phase-3 API/JWT scanner attaches auth headers to live requests | ✓ |
| Infrastructure only — no live consumer | Build plumbing + controls; no scanner sends authed requests yet | |
| API/JWT + generic HTTP/TLS endpoints | Attach auth headers across API/JWT AND general HTTP/TLS probes | |

**User's choice:** Wire into existing API/JWT scanner.
**Notes:** Proves the seam end-to-end; no new finding types in Phase 93 (those land in Phase 94).

---

## Claude's Discretion

- Module path: `quirk/auth/credentials.py` recommended over `quirk/util/credentials.py` (planner to confirm; research split STACK vs ARCHITECTURE).
- `CredentialContext` has zero scanner-module imports; captured into `_wrapped_phase` closures without changing that helper's signature.

## Deferred Ideas

- mTLS client-cert auth (deferred milestone-wide).
- OAuth2 client-credentials token acquisition (Future Requirements).
- Authenticated scheduled scans (architecturally prohibited; actively rejected in this phase).
- `MADV_DONTDUMP` / core-dump protection (out of scope for the consulting use case).
