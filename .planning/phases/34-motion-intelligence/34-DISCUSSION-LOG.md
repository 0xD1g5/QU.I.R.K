# Phase 34: Motion Intelligence — Discussion Log

**Date:** 2026-04-28
**Mode:** default (no flags)
**Format:** human reference only — not consumed by downstream agents.

---

## Gray Areas Surfaced by Analysis

Phase 34 is unusually constrained: REQUIREMENTS.md MOTION-01..04 lock the field names, weights, and multipliers. Analysis surfaced four narrow wiring decisions, plus one notable spec asymmetry.

**Asymmetry flagged:** MOTION-01 declares 6 evidence counters; MOTION-02 declares only 5 ratios. `motion_email_starttls_missing_count` has no matching weight entry. Resolved as decision D-01 below.

**Naming mismatch flagged:** ROADMAP prose says the 6th subscore sits "alongside tls, ssh, api, identity, data_at_rest" — but `scoring.py:202` returns `{hygiene, modern_tls, identity_trust, agility_signals, data_at_rest}`. Resolved as decision D-04.

---

## Areas Selected for Discussion

User selected all four:
- ☑ STARTTLS-missing scoring
- ☑ Subscore key naming
- ☑ Driver integration
- ☑ Verification approach for SC-1

---

## Q1 — STARTTLS-missing scoring

**Question:** How should `motion_email_starttls_missing_count` be scored, given the MOTION-01/MOTION-02 asymmetry?

**Options presented:**
1. Fold into `motion_email_plaintext_ratio` (Recommended) — single 12.0 weight covers both signals.
2. Add a new ratio entry (`motion_email_starttls_missing_ratio`) — diverges from REQUIREMENTS.md.
3. Finding-only, no scoring — counter exists but doesn't drive any ratio.

**Selected:** Fold into plaintext_ratio.

**Rationale:** Mathematically merges two semantically equivalent signals (mail traffic without TLS). Treats the spec asymmetry as intentional dedup. No REQUIREMENTS.md change needed.

---

## Q2 — Subscore key naming

**Question:** How should `data_in_motion` join the existing subscores given the ROADMAP prose vs `scoring.py` mismatch?

**Options presented:**
1. Append `data_in_motion` only (Recommended) — keep existing 5 keys, add 6th.
2. Rename to roadmap names + add 6th — bigger blast radius.
3. Defer naming question — explicitly note rename as future work.

**Selected:** Append data_in_motion only.

**Rationale:** Zero churn for dashboard, API, and stored reports. ROADMAP prose treated as aspirational. Rename captured in deferred ideas (D-05).

---

## Q3 — Driver integration

**Question:** Should `motion_drivers` join `top_drivers` ranking?

**Options presented:**
1. Merge into `top_drivers` (Recommended) — motion findings can surface in executive summary.
2. Keep separate — motion only visible via Phase 36 dashboard tab.

**Selected:** Merge into top_drivers.

**Rationale:** Consultant-facing executive summary should show worst-issue-first regardless of category. Plaintext Kafka with weight 14.0 deserves to outrank smaller TLS findings. Mirrors how `identity_trust` and `dar` joined the pool.

---

## Q4 — Verification approach for SC-1

**Question:** How is SC-1 ("plaintext-broker scan produces lower data_in_motion") verified?

**Options presented:**
1. Unit tests with synthesized evidence (Recommended) — fast, no Docker.
2. Integration tests via chaos labs — end-to-end proof, slower.
3. Both — belt-and-suspenders.

**Selected:** Unit tests with synthesized evidence.

**Rationale:** Pure scoring-engine math change; deterministic unit tests are the appropriate granularity. End-to-end validation deferred to Phase 36 dashboard work where Docker is already in scope.

---

## Deferred Ideas

- Rename existing 5 subscore keys to ROADMAP prose names (v4.5+) — D-05.
- `motion_email_starttls_missing_ratio` as its own weight — rejected; revisit if real-engagement telemetry shows the fold under-weights it.
- Integration test against chaos labs for SC-1 — folded into Phase 36 scope.

---

## Claude's Discretion (per decisions in CONTEXT.md)

- `motion_impacts` block: inline in `compute_readiness_score()` vs `_compute_motion_subscore()` helper.
- Order of new fields in `EvidenceCounters` dataclass.
- Test file naming convention (`tests/intelligence/test_motion_subscore.py` vs existing patterns).
