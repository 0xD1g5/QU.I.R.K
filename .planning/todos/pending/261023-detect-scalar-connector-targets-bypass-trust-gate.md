---
type: todo
created: 2026-10-23
source: Phase 230 review round R12 (CR-01), the 230-REVIEW-R12.md finding
priority: high
area: quirk/config.py (connector *_targets coercion), quirk/util/target_trust.py (_field_values), every scanner that iterates a *_targets list
status: pending
resolves_phase: null
owner: "999.136"
---

# A scalar `*_targets` value can reach a scanner as a str while the trust gate checks the whole string

R12 CR-01 was measured for `kerberos_targets`.
- `kerberos_targets: dc01.corp.local` (a YAML scalar) loaded as a `str`.
- `enforce_trusted_targets` wraps a scalar as `[raw]` (`quirk/util/target_trust.py:239-248`), so it checked `"dc01.corp.local"`.
- `scan_kerberos_targets` then iterated the str one character at a time. `"0"` resolves to `0.0.0.0`, so the local host was probed, and the real KDC was never scanned.

Phase 230 fixed only `kerberos_targets`: config wraps a scalar, and the scanner treats a bare str as one target.

Enumerated from source on 2026-10-23 (`dataclasses.fields(ConnectorsCfg)` plus a grep for `conn_raw["<name>"] =`). These **11** `*_targets` fields have no load-time scalar coercion:
- `jwt_targets`, `container_targets`, `source_targets`;
- `saml_targets`, `dnssec_targets`, `smime_targets`, `adcs_targets`;
- `codesign_targets`, `pg_targets`, `mysql_targets`.

Only `kerberos_targets` and `broker_targets` are coerced.

**UNVERIFIED per consumer:** whether each scanner iterates the value directly. Some may wrap it themselves. Measure each one; do not assume.

- [ ] For each of the 11 fields, load a scalar YAML value and record what reaches the scanner and what the trust gate checked.
- [ ] Coerce scalars at load time in one place, a loop over every `*_targets` field derived from `ConnectorsCfg`, not a hand list. Keep list elements as they are, because `_as_str_list` turns `None` into `"None"`.
- [ ] Add a run-time test that enumerates the `*_targets` fields and asserts that a scalar loads as a one-element list for each.

## Feasibility & Effort

- **CONFIRMED** for `kerberos_targets` (R12 evidence, fixed in Phase 230). **LIKELY** for some of the 11 others.
- **LIKELY** effort **S**: one loop in `config.py` plus one parametrised test. Dashboard-built configs write lists, so GUI parity is unaffected.
