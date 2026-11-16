---
type: todo
created: 2026-11-16
source: Phase 236 review WR-07 (236-REVIEW.md), filed by plan 236-09
priority: low
area: quirk/util/weak_crypto.py
status: pending
resolves_phase:
owner: "999.132"
---

# A row with no tls_version and a legacy-only supported list gets the LOW tier instead of HIGH

`is_max_legacy_tls` returns False when `tls_version` is empty, so `tls_version=None` with `tls_supported_versions="TLSv1,TLSv1.1"`
falls to the LOW "offered alongside TLS 1.2+" tier on both surfaces, where D-01 says HIGH.

Regression lock to add with the fix: a case in `test_is_max_legacy_tls` (`tests/test_weak_crypto_helper.py`) asserting
`is_max_legacy_tls(None, "TLSv1,TLSv1.1")` is True. The gate family `legacy_supported_only` will not catch the change: it compares
HIGH/CRITICAL parity between the surfaces, and the fix moves both surfaces together, so that family stays green either way.

## Feasibility & Effort

**Feasibility: HIGH.** Infer the maximum from the supported list when the version is empty. **Effort: S.**
