---
type: todo
created: 2026-11-16
source: Phase 236 review WR-01 (236-REVIEW.md), filed by plan 236-09
priority: low
area: quirk/intelligence/evidence.py, quirk/util/weak_crypto.py
status: pending
resolves_phase:
owner: "999.132"
---

# Evidence legacy_tls_count does not count the SSLv2/SSLv3-only HIGH tier

`legacy_tls_count` uses `has_legacy_tls_versions_signal`, which matches only TLSv1 and TLSv1.1, while `is_max_legacy_tls` now
puts SSLv2/SSLv3-only servers in the HIGH tier. On identical rows an SSLv3-only server scores 63 (count 0) and a TLS 1.0-only
server scores 62 (count 1). Identical on both surfaces, so this is a scoring-quality defect and not a parity defect.

## Feasibility & Effort

**Feasibility: HIGH.** Count the HIGH tier in the evidence counter (review WR-01 fix). **Effort: S.** Moves scores on both surfaces together.
