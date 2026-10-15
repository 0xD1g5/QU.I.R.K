---
type: todo
created: 2026-10-13
source: Phase 224 GC3 (REST3) wording sweep; ledger rows DCL-CLOUDCONSOLE-0159, DCL-ADMIN-0156 (docs/deployment-cloud-console.md §7 Audit trail, docs/admin-guide.md §3.4)
priority: low
area: quirk/dashboard/api/middleware/rate_limit.py, quirk/dashboard/api/routes/sensor.py, quirk/models.py (IntegrationDelivery)
status: completed
completed: 2026-10-14
resolves_phase: 225.1
---

# Rate-limited sensor pushes leave no audit row, and push audit rows carry no sensor id or source address

`quirk/dashboard/api/routes/sensor.py:25` promises an `IntegrationDelivery` row "on EVERY attempt". The rate limiter
(`quirk/dashboard/api/middleware/rate_limit.py:22`, 60 mutating requests per minute per client IP) answers HTTP 429
before the route or `require_sensor_auth` runs, so those attempts are not audited. Probe
(`work/probes/gc3-rest3-push-ratelimit-audit-probe.py` in the phase directory: 70 bogus-bearer pushes from one client
through the real app) -> `{401: 60, 429: 10}` and 60 `sensor_push` rows.

Separately, the audit row has no sensor id or client-address column (`quirk/models.py:340-346`: id, scan_id,
finding_hash, destination, status, attempted_at, error_summary), so the compromise-response step in
docs/admin-guide.md §3.4 cannot attribute rejected pushes to a sensor or IP from the audit table; only the uvicorn
request log has the address.

- [ ] Decide whether a 429 on `/api/sensor/push` should write a `sensor_push` audit row (rate_limited).
- [ ] Consider adding `client_ip` (and, after auth, `sensor_id`) to the push audit row.
- [ ] Update docs/deployment-cloud-console.md §7 and docs/admin-guide.md §3.4 if either changes.

## Feasibility & Effort

- **CONFIRMED** by the probe above and the middleware order at `quirk/dashboard/api/app.py:113-125` (RateLimit is
  innermost middleware, still ahead of the route dependencies).
- Effort **S/M**: the 429 audit is a small change in `rate_limit.py` (path check + row write needs a DB session in
  middleware, which it does not have today: **UNKNOWN** cost); the extra columns need an additive migration in
  `quirk/db.py`.


## Resolution (225.1-13)

Both the `rate_limited` audit row and the `client_ip` / `sensor_id` columns shipped; the D-12 cut option was not taken.
