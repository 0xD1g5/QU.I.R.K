# Phase 58: Dashboard API Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-09
**Phase:** 58-dashboard-api-hardening
**Areas discussed:** Token configuration, Mutating route scope, Rate limiting approach, CSRF mechanism

---

## Gray Area Selection

| Area | Offered | Selected |
|------|---------|----------|
| Token configuration | ✓ | ✓ (via recommended path) |
| Mutating route scope | ✓ | ✓ (via recommended path) |
| Rate limiting approach | ✓ | ✓ (via recommended path) |
| CSRF mechanism | ✓ | ✓ (via recommended path) |

**User's response:** "please move forward with recommended suggestions for each area" — all four areas explored with Claude's recommended decision applied to each.

---

## Token Configuration

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-generated on first `quirk serve` | Printed to stdout, stored in config — good UX but breaks headless/CI | |
| `QUIRK_API_TOKEN` env var only | Familiar Unix pattern, but no YAML config fallback | |
| Env var (priority) + YAML field (fallback) | `QUIRK_API_TOKEN` wins; `security.api_token` as fallback; disabled when neither set | ✓ |
| YAML-only | Misses CI/automation use case | |

**User's choice:** Recommended (env var + YAML fallback, auth disabled when neither set)
**Notes:** Extends the `security:` YAML block already established in Phase 57. Backward-compatible — existing installs that never exposed the port don't need to configure a token.

---

## Mutating Route Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Auth on mutating routes only (POST/PUT/DELETE/PATCH) | GET reads are public | |
| Auth on all routes except GET /api/health | Scan results contain sensitive crypto data — reads shouldn't be public either | ✓ |
| Auth on every route including /api/health | Breaks monitoring / health checks | |

**User's choice:** Recommended (all routes auth-required except GET /api/health; rate limiting on POST/PUT/DELETE/PATCH only)
**Notes:** 7 mutating routes enumerated: `POST /api/export/pdf`, `POST/DELETE /api/qramm/sessions`, `POST /api/qramm/sessions/{id}/answers`, `POST /api/qramm/sessions/{id}/score`, `POST /api/qramm/profiles`, `POST /api/qramm/assessment/draft`.

---

## Rate Limiting Approach

| Option | Description | Selected |
|--------|-------------|----------|
| slowapi (FastAPI-native) | Mature, wraps `limits` library — needs new pip dep | |
| starlette-ratelimit | Less maintained | |
| In-process token bucket (zero new deps) | ~30 lines, `collections.defaultdict(deque)` + `time.monotonic()`, adequate for local-first | ✓ |

**User's choice:** Recommended (in-process token bucket, zero new deps)
**Notes:** The "zero new pip deps" constraint was explicit in v4.6; the spirit carries to v4.8 for a hardening phase. If the tool evolves to multi-instance, replace with Redis-backed `limits` then.

---

## CSRF Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Double-submit cookie | Server generates token, client must echo — stateful, requires wiring | |
| Synchronizer token (server-side) | Classic server-side session token — overkill for local JSON API | |
| Custom request header (X-Quirk-Request: 1) | Stateless; browsers can't set custom headers cross-origin without CORS preflight (which we block) | ✓ |
| Origin/Referer header check | Less reliable — some proxies strip Referer | |

**User's choice:** Recommended (custom request header, stateless)
**Notes:** The React SPA calls JSON APIs via `fetch()`, not HTML form submissions. The real CSRF threat is cross-origin JS — a custom header blocks this completely since browsers enforce same-origin policy on custom headers. Combined with the CORS allowlist lockdown (HARDEN-API-02), this covers the full threat model. Returns 403 (not 401) to distinguish CSRF failure from auth failure.

---

## Claude's Discretion

- Exact FastAPI `Depends()` wiring shape for bearer auth (plain function vs `Security()` with `HTTPBearer`)
- Whether to use FastAPI's built-in `CORSMiddleware` (obvious choice)
- Internal structure of `quirk/dashboard/api/middleware/` package
- Fuzz test implementation (pytest parametrize vs data file)
- Whether `TargetFileError` extends `ValueError` or is a standalone exception class
- Playwright redirect-guard: `page.route()` interception vs `page.on("response")` (chose `page.route()` — fires before DNS)

## Deferred Ideas

- `quirk token generate` CLI command for UX convenience — out of scope for hardening phase
- Rate limiter backed by Redis for multi-instance scenarios — in-process bucket adequate now
- Audit logging of authenticated requests — no multi-user audit requirement this milestone
- `SameSite=Strict` cookie CSRF if auth ever moves to cookies — not applicable to current bearer-token design
