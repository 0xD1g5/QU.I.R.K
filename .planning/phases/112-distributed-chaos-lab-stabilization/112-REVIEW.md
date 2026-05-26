---
phase: 112-distributed-chaos-lab-stabilization
reviewed: 2026-05-26T00:00:00Z
depth: standard
iteration: 2
files_reviewed: 6
files_reviewed_list:
  - quirk/cli/sensor_cmd.py
  - quirk/util/url_allowlist.py
  - quantum-chaos-enterprise-lab/docker-compose.distributed.yml
  - quantum-chaos-enterprise-lab/sensor.Dockerfile
  - quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh
  - tests/test_distributed_topology.py
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: clean
---

# Phase 112: Code Review Report (Iteration 2 — Post-Fix Re-Review)

**Reviewed:** 2026-05-26
**Depth:** standard
**Files Reviewed:** 6
**Status:** clean

## Summary

Re-review of Phase 112 after remediation of 7 findings from iteration 1
(CR-01, CR-02, CR-03, WR-01, WR-02, WR-03, IN-01).

All seven findings are confirmed resolved. No new Critical or Warning issues
were found. The security-sensitive CR-03 change (`--allow-internal-console` /
`allow_internal_console` persistence) passes every verification criterion.
The distributed lab and its test suite are now correct and ready to ship.

---

## Finding-by-Finding Verification

### CR-01: Sensor services idle — RESOLVED

Both `sensor-a` and `sensor-b` in `docker-compose.distributed.yml` now use:

```yaml
entrypoint: []
command: ["tail", "-f", "/dev/null"]
```

Neither `--target` nor `--allow-self-signed` appear in any `command:` block.
The `test_both_sensors_scan_crypto_internal` topology test asserts
`--target` is absent from all sensor `command:` arrays and that
`sensor-config.yaml` is volume-mounted (the real scan-target path). Both
assertions are non-tautological and pass against the current compose file.

### CR-02: Console healthcheck URL — RESOLVED

The `console` service healthcheck is now:

```yaml
test: ["CMD", "curl", "-f", "http://localhost:8512/api/health"]
```

This matches the FastAPI route registered under `prefix="/api"`. The
`depends_on: console: condition: service_healthy` on both sensor services
will now resolve correctly once the server starts.

### CR-03: `--allow-internal-console` SSRF bypass — RESOLVED AND VERIFIED

This was the security-sensitive change. Every criterion from the verification
checklist passed:

**(a) Default path still blocks RFC1918 (no silent weakening).**
`_cmd_enroll` reads `allow_internal: bool = bool(getattr(args, "allow_internal_console", False))`.
The default is `False`. Without the flag, `validate_external_url` is called with
`allow_internal=False` — the existing RFC1918/loopback/link-local blocks are
unchanged. `test_enroll_ssrf_guard_exits_nonzero` directly tests this path with
`allow_internal_console = False` and asserts non-zero exit.

**(b) Cloud metadata IPs remain ALWAYS blocked.**
In `url_allowlist.py` (lines 141-143), the metadata check fires BEFORE the
`allow_internal` bypass gate:

```python
# 2a. Metadata service — always blocked, even with allow_internal=True.
if ip in _METADATA_IPS:
    return ValidationResult(False, RC_METADATA_SERVICE_IP, _redact_preview(url))

# 2b. allow_internal bypass for non-metadata IPs.
if allow_internal:
    return ValidationResult(True, "", "")
```

`_METADATA_IPS` contains both `169.254.169.254` (AWS/GCP/Azure EC2 metadata)
and `fd00:ec2::254` (IPv6 EC2 metadata). The check order is structurally
correct — there is no path through the function where `allow_internal=True`
allows a metadata IP through.

`tests/util/test_url_allowlist.py` includes parametrized tests
`allow_internal_metadata_still_blocked_v4` and
`allow_internal_metadata_still_blocked_v6` that call
`validate_external_url(url, allow_internal=True)` with both metadata IPs and
assert `ok=False, reason=RC_METADATA_SERVICE_IP`.

`test_sensor_cmd.py::test_enroll_allow_internal_console_passes_rfc1918` calls
the real `validate_external_url` (not mocked) with `http://10.30.0.5:8512`
and asserts exit 0. This simultaneously proves RFC1918 is accepted and does
not introduce a metadata bypass (the address is plain RFC1918, not
169.254.x.x).

**(c) `verify=True` / `follow_redirects=False` / `_NoRedirectHandler` unchanged.**
`httpx.Client(verify=True, follow_redirects=False)` at `sensor_cmd.py:577`
is unchanged. No `verify=False` occurs anywhere in the file (grep confirms
zero hits). `_NoRedirectHandler` import at line 48 is present. The security
contract comment block at the top of the file (lines 15-24) explicitly states
`verify=True is HARDCODED` and `follow_redirects=False prevents
post-validation SSRF bypass`.

**(d) `verify=False` grep gate unaffected.**
The grep gate in `tests/test_sensor_no_verify_false.py` operates on the
`sensor_cmd.py` source file. No `verify=False` string was introduced — the
gate remains green.

**(e) Persistence round-trip is correct.**
`_cmd_enroll` writes `"allow_internal_console": allow_internal` to
`sensor.yaml`. `_cmd_push` reads it back with
`bool(sensor_cfg.get("allow_internal_console", False))` and passes it to
`validate_external_url`. `test_enroll_allow_internal_console_persisted_for_push`
uses a capturing wrapper around the real `validate_external_url` and asserts
`validate_calls[0]["allow_internal"] is True` when the sensor.yaml has
`allow_internal_console: true`. The round-trip is exercised end-to-end.

### WR-01: Tautological ordering test — RESOLVED

`test_e2e_script_enroll_push_merge_order` now uses a regex
`r'^\s*(?!\s*#).*quirk\s+.*<keyword>'` with `re.MULTILINE`. The negative
lookahead `(?!\s*#)` correctly rejects comment lines (verified against all
eight comment lines in the script that mention `push`, `enroll`, or `merge`).
The pattern matches the first actual `quirk console enroll` line (pos 1641),
then the first `quirk sensor push` line (pos 3699), then `quirk sensor merge`
(pos 4412), satisfying `enroll < push < merge`. The assertion is
non-tautological.

### WR-02: Sensor Dockerfile runs as root — RESOLVED

`sensor.Dockerfile` now includes:

```dockerfile
RUN useradd --create-home --shell /bin/bash quirk
USER quirk
WORKDIR /home/quirk
```

Both sensor services use `cap_add: [NET_RAW]` in the compose file instead of
root. The Dockerfile includes an explanatory comment stating why `NET_RAW` is
used via `cap_add` rather than running as root.

### WR-03: Empty-token guards absent — RESOLVED

After each token extraction in `distributed-e2e.sh`, explicit guards are
present:

```bash
if [[ -z "${TOKEN_A}" ]]; then
  echo "ERROR: enrollment failed for sensor-a (empty token — console may not be ready)" >&2
  exit 1
fi
```

Equivalent guard exists for `TOKEN_B`. The guards are placed before the
tokens are consumed by `quirk sensor enroll`, so an empty token never
propagates silently.

### IN-01: `import re` inside loop — RESOLVED

`import re` is now at module level in `tests/test_distributed_topology.py`
(line 17), alongside `import shutil`, `import subprocess`, and `import yaml`.
No import appears inside any loop body.

---

## No New Issues Found

A targeted review of the `--allow-internal-console` change surface found no
new defects:

- The `allow_internal_console` field is boolean-coerced on both read
  (`bool(getattr(..., False))`) and write — a YAML `true`/`false` or a
  Python `True`/`False` both parse correctly.
- The `_cmd_enroll` hint message (`if not allow_internal and result.reason == "internal_ip"`)
  is correctly gated so it does not print the hint when the operator is
  already using `--allow-internal-console`.
- No `allow_internal_console` handling was added to `export-results` or
  `merge` subcommands, which is correct — those paths have no console network
  I/O and do not call `validate_external_url`.
- The e2e script passes `--allow-internal-console` only to `quirk sensor enroll`
  (line 86, 94), not to `quirk sensor push` — correct, because the flag is
  persisted in `sensor.yaml` and push reads it automatically.

---

_Reviewed: 2026-05-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 2 (post-fix re-review)_
