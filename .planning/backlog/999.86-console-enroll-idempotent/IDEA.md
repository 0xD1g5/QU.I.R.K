# Backlog 999.86 — Make `quirk console enroll` idempotent

**Type:** bug (minor)
**Source:** v5.4 live human-UAT (UAT-112-03), 2026-05-26
**Candidate for:** v5.5

## Problem

`quirk console enroll` is not idempotent: re-running it for an already-provisioned
`sensor_id` exits non-zero. As a result `lab.sh distributed e2e` cannot be re-run
without a full `down -v` to wipe the console DB volume first — the second run dies at
Step 1 ("enrollment failed … empty output").

## Fix

Make `console enroll` idempotent — upsert the `sensors` row (or treat an existing
matching `sensor_id` as success, refreshing token/segment as appropriate) so the e2e
harness is repeatable without a teardown. Add a regression test for the re-enroll path.

## References

- `.planning/v5.4-deferred-uat.md` (notes)
- `quirk/cli/console_cmd.py` (enroll path)
- `quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh:50-80`
