---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure GC3-OPS (fork A); ledger rows DCL-OPS-A-0138, DCL-OPS-GC3A-0004..0006 (docs/operators-guide.md §2.4 security.trusted_targets)
priority: high
area: quirk/util/target_trust.py (enforce_trusted_targets), quirk/dashboard/api/routes/jobs.py (create_job trusted-targets check, build_job_config_dict security block)
status: completed
resolves_phase: 225.1
completed: 2026-10-14
---

# The CLI trusted_targets check skips `targets.include_ips`

Related: `261013-doc224-trusted-targets-skips-broker-targets-and-schedules` already covers the dashboard broker-target
and scheduled-scan gaps (gap 2 below is the same defect, recorded here with this round's probe). The new finding in this
todo is gap 1.

`security.trusted_targets` is documented as the scan-consent allowlist. Two gaps let a scan reach a host outside it:

1. **CLI: `targets.include_ips` is never checked.** `enforce_trusted_targets` (`quirk/util/target_trust.py:102-106`)
   builds its list from `targets.fqdns`, `targets.cidrs` and the `broker_targets` hosts only. `include_ips` is the
   starter template's main target list. Live probe
   (`.planning/phases/224-doc-claim-ledger-verification/work/probes/gc3-ops-A-trusted-targets-parity-probe.sh`):
   trusted_targets `[127.0.0.1]`, `include_ips: [127.0.0.2]` -> the real CLI scan completes (rc 0); the same host in
   `fqdns` -> rc 1 "not in the trusted-targets allowlist".
2. **Dashboard: connector targets are never checked.** `create_job` checks only the form targets
   (`jobs.py:718`, `:742`) against the server config. The generated job config's `security` block
   (`jobs.py:306`) carries only `allow_internal_targets`, so the spawned `run_scan.py` sees an empty allowlist and its
   own gate is allow-all. Probe `gc3-ops-A-trusted-targets-dashboard-probe.py`: a `broker_targets` host outside the
   allowlist is accepted with 201.

The operators-guide now states both gaps. A consent control should not depend on which field a target is typed into.

- [x] Add `include_ips` (and every connector target list that names hosts) to `enforce_trusted_targets`.
- [x] Write the server's `trusted_targets` into the generated job config, or check connector targets in `create_job`.
- [x] Add tests for an `include_ips` and a dashboard `broker_targets` target outside the allowlist.

## Feasibility & Effort

- **CONFIRMED** gap 1 at `quirk/util/target_trust.py:102-106` (no `include_ips`) and by the live probe above.
- **CONFIRMED** gap 2 at `quirk/dashboard/api/routes/jobs.py:718` (`all_valid_tokens = valid_fqdns + valid_cidrs`) and
  `:306` (security block without `trusted_targets`).
- **LIKELY** effort **S/M**: one-line addition for `include_ips`; propagating `trusted_targets` into the job config is a
  small change, but enumerating every connector target field (jwt/saml/dnssec/kerberos/adcs/pg/mysql/vault...) that
  names a host is the M part. **UNKNOWN**: whether IP ranges in `include_ips` (expanded later by
  `target_expander`) need CIDR-containment checks. No spike needed.
