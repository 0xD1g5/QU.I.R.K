---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-CONFIG-B-* (configuration.md Dashboard form vs. presets precedence)
priority: medium
area: quirk/engine/profiles.py (apply_profile, _set_if_default)
status: pending
resolves_phase: null
---

# apply_profile replaces an explicit scan value that equals the profile's baseline default

The "Dashboard form vs. presets precedence" section promised that an explicit operator value always beats the scan
profile because `apply_profile` checks `_user_set_fields`. That is only true for `connectors.enable_email` and
`connectors.enable_broker`. For the scan timeout and concurrency fields `apply_profile` uses `_set_if_default`, which
overwrites a value that is `None` **or equal to a hard-coded baseline default**, so an explicit value that happens to equal
the baseline is silently replaced:

```
scan.fingerprint_concurrency: 200   +  --profile quick   ->  300   (the explicit 200 is gone)
scan.tls_concurrency: 200           +  --profile quick   ->  250
scan.tls_concurrency: 150           +  --profile quick   ->  150   (kept, only because 150 != the 200 baseline)
```

(`.venv/bin/python -c` driving `quirk.config.config_from_dict` then `quirk.engine.profiles.apply_profile`; see
`quirk/engine/profiles.py` `_set_if_default` and `base_concurrency_default = 200`.) The Advanced panel therefore cannot
reliably express "I want exactly 200", and the baseline constants (200, 5) no longer match `ScanCfg`'s own defaults
(`tls_concurrency` 150, `ssh_concurrency` 100, `tls_seconds` 6), so which values count as "default" is accidental.

`docs/configuration.md` now documents the real behaviour; it should be reverted to a guarantee if this is fixed.

- [ ] Record which scan fields the operator set (a `ScanCfg._user_set_fields`, as `ConnectorsCfg` already has) and make
      `apply_profile` skip them.
- [ ] Add a test: explicit value equal to the old baseline survives each profile.
- [ ] Update the precedence section of `docs/configuration.md` and regenerate `docs/quirk-master-guide.md`.

## Feasibility & Effort

**CONFIRMED** by the live `apply_profile` run above (re-run before starting). Effort **S-M**: `ConnectorsCfg` already
shows the pattern (`conn_raw.keys()` stored at load time, `quirk/config.py:954`); the work is plumbing the same set
through `ScanCfg`/`TimeoutsCfg` and the `timeouts:` sub-table, plus the flat legacy aliases. Unknown: the interaction with
the deprecated flat fields (`tls_timeout_seconds` etc.), which `apply_profile` writes while the scanners read
`scan.timeouts.*`. A spike on that mismatch first is worthwhile.
