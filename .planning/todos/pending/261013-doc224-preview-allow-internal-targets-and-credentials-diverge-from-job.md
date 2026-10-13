---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger parts 224-12/224-13, docs/configuration.md Port Scope / precedence)
priority: medium
area: quirk/dashboard/api/config_preview.py (resolve_effective_config), quirk/dashboard/api/routes/jobs.py (create_job)
status: pending
resolves_phase: null
---

# Effective Config preview shows a different `security` and credential state than the job it previews

`resolve_effective_config` calls `build_job_config_dict(..., allow_internal_targets=False, ...)`
unconditionally (`quirk/dashboard/api/config_preview.py:119`). The real submission reads the flag from
the server config (`quirk/dashboard/api/routes/jobs.py:857-859`) and writes that value into the job.
The preview also takes no credentials argument, so the `broker_credentials` / `snmp_v3_credentials`
fragments that `create_job` adds (`jobs.py:908` and the lines after it) never appear in it.

Observed (isolated HOME; QUIRK_CONFIG_PATH pointing at a server config with
`security.allow_internal_targets: true`): the preview resolved `security.allow_internal_targets = False`,
while the job dict built the way create_job builds it had `True`. The preview route renders a Security
section (`quirk/dashboard/api/routes/config.py:62`), so the operator sees `false` for a scan that runs
with `true`.

docs/configuration.md ("Dashboard form vs. presets precedence") now lists the three differences: this
flag, the temporary output paths, and credentials.

- [ ] Load the server's `allow_internal_targets` in `resolve_effective_config` the same fail-closed way
      create_job does, or drop the Security section's value from the preview.
- [ ] Decide whether the preview should show credential-name fragments (as set / not set).

## Feasibility & Effort

- **Feasibility: CONFIRMED.** One hard-coded argument at `quirk/dashboard/api/config_preview.py:119`; the
  load pattern to copy is at `quirk/dashboard/api/routes/jobs.py:854-863`.
- **Effort: S** for the flag plus a test; credentials display is a small design decision.
- **Unknowns:** whether the create_job D-08 availability gate (`jobs.py:800`), which reuses the preview
  resolver, should see the real flag too. It does not read `security` today.
- **Spike:** no.
