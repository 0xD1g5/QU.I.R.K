---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger parts 224-12/224-13, docs/configuration.md security.trusted_targets)
priority: high
area: quirk/dashboard/api/routes/jobs.py (create_job), quirk/dashboard/api/routes/schedules.py, quirk/cli/scheduler_cmd.py
status: completed
completed: 2026-10-14
resolves_phase: 225.1
---

# `security.trusted_targets` is not applied to dashboard broker targets or to scheduled scans

The consent allowlist has two enforcement points (grep for `is_target_trusted|enforce_trusted_targets`
finds only these):
- CLI: `run_scan.py:1985 enforce_trusted_targets(cfg)`, which checks the targets plus
  `connectors.broker_targets` hosts (`quirk/util/target_trust.py:105`).
- Dashboard New Scan: `quirk/dashboard/api/routes/jobs.py:742-743` checks only `all_valid_tokens` (the
  form targets) against the server config.

Two gaps:
1. **Connectors-panel broker targets.** `broker_targets` is a dashboard-settable detail field
   (`quirk/dashboard/api/schemas.py:849`). The job YAML carries no `trusted_targets`, so the scan
   subprocess's own check passes. Probe: `build_job_config_dict(..., connectors_overlay={'enable_broker':
   True, 'broker_targets': ['evil.example:9092']})` -> load_config -> enforce_trusted_targets passed. The
   same config with `trusted_targets: ['api.acme.com']` raises ValueError.
2. **Scheduled scans.** `POST /api/schedules` (`quirk/dashboard/api/routes/schedules.py:146`) and
   `quirk schedule add` make no check. At run time `_materialize_scan_config`
   (`quirk/cli/scheduler_cmd.py:192-198`) starts from `--scan-config` or from a skeleton with no
   `security` block. Without `--scan-config`, an untrusted schedule target is scanned (probe:
   enforce passed with `trusted_targets = []`).

docs/configuration.md now states both gaps.

- [x] create_job: also check `connectors_overlay['broker_targets']` hosts (reuse
      `target_trust._broker_target_hosts`), or write the server's `trusted_targets` into the job YAML so
      run_scan enforces it.
- [x] Schedules: check the target at create/patch time against the server config, and/or have the
      scheduler fall back to the server config's `trusted_targets` when there is no `--scan-config`.

## Feasibility & Effort

- **Feasibility: CONFIRMED.** Both probes reproduce in an isolated HOME. Insertion points:
  `quirk/dashboard/api/routes/jobs.py:741`, `quirk/dashboard/api/routes/schedules.py:157`,
  `quirk/cli/scheduler_cmd.py:198`.
- **Effort: S-M.** Writing `trusted_targets` into the job YAML closes gap 1 in one line, but it changes
  the job's fail-open semantics (`jobs.py:727-731`). The scheduler fallback needs a decision on which
  config the daemon trusts.
- **Unknowns:** whether scheduled runs created before the fix should be re-validated.
- **Spike:** no.

## Resolution (225.1)

- Gap 1 (broker targets): closed by 225.1-08 (every connector host field is checked, and dashboard jobs carry the server `trusted_targets`).
- Gap 2 (schedules): closed by 225.1-10. `POST /api/schedules`, `PATCH enabled:true` and `quirk schedule add` check the server `trusted_targets`; recurring runs without `--scan-config` carry the server `trusted_targets` and `allow_internal_targets`.
- Unknown resolved: schedules created earlier are re-validated when enabled again.
