---
type: todo
created: 2026-09-22
source: Phase 208 security audit (208-SECURITY.md) — found by deriving the caller set from source, not from a list
priority: medium  # not high: the on-prem threat model in rationale (1) still holds and is the load-bearing reason; what is wrong is rationale (2)'s claimed breadth
requirement: null
resolves_phase: null
---

# `url_allowlist.py`'s AUDIT-09 accepted-risk note overstates its own PinnedIPAdapter coverage

`quirk/util/url_allowlist.py` lines 30-44 formally accept the CWE-367 TOCTOU risk between
`validate_external_url`'s resolution check and the downstream connect. Rationale **(2)** reads:

> Phase 123 SSRF-05 (PinnedIPAdapter): HTTP/HTTPS fetch callers receive `resolved_ip` from
> `ValidationResult` and pin their connection via `PinnedIPAdapter` (or equivalent), closing the
> requests/httpx TOCTOU window by forcing connect to the validated IP rather than re-resolving.

**That describes more coverage than exists.** Derived from source 2026-09-22:

```bash
grep -rln "PinnedIPAdapter" quirk/ | grep -v __pycache__
# quirk/notify/channels/email.py
# quirk/scanner/rest_fuzzer.py
# quirk/util/pinned_adapter.py      (the adapter itself)
# quirk/util/url_allowlist.py       (the docstring making the claim)
```

`quirk/ticketing/jira.py` and `quirk/ticketing/servicenow.py` are both HTTP/HTTPS fetch callers
acting on an **operator-supplied URL**, and **neither pins** (`grep -c PinnedIPAdapter` = 0 in
both). `servicenow.py` at least has `_NoRedirectHandler`, which is arguably the "(or equivalent)"
the note hedges with; `jira.py` has **no** redirect control at all, because it delegates HTTP to
the third-party `jira` SDK and never sees the connection.

## Why this matters more than a typo

This is not a new defect — the posture predates Phase 208 and the gap is real but narrow under the
on-prem threat model. The problem is that **the record is the control**. An accepted-risk note has
no test, no gate, and no `last_verified`; the only thing standing behind it is that someone read it
and believed it. A future reviewer checking "is TOCTOU handled?" reads rationale (2), sees a
mechanism named, and moves on — which is exactly what makes a stale security rationale worse than
an absent one. Compare CLAUDE.md's repeated finding that a hand-maintained list drifts from the
real set; this is that failure mode inside a security artifact.

Phase 208's COV-06 claim is **unaffected** — it asserts ordering (guard fires before
`JIRA(...)` is constructed), which is verified and true. TOCTOU is a different window.

## Feasibility & Effort

- **CONFIRMED** — all claims above re-derived from source 2026-09-22 (grep counts quoted).
- **Effort: S** for the honest-documentation fix; **M** if pinning is actually extended.
- Two options, and they are not equivalent:
  1. **Correct the note (S)** — name the real users (`email.py`, `rest_fuzzer.py`), state plainly
     that `jira.py` and `servicenow.py` do not pin, and say why that is accepted (on-prem model,
     TLS cert verification, `_NoRedirectHandler` for ServiceNow / third-party SDK for Jira).
     This makes the record true without changing posture.
  2. **Extend pinning (M)** — `servicenow.py` is plausible since it owns its `urllib` handler
     chain. `jira.py` is the hard one: the `jira` SDK owns the session, so pinning means either
     injecting a `requests.Session` with the adapter mounted (if the SDK accepts one) or
     accepting that this caller cannot pin. **Spike the SDK's session-injection surface before
     committing to this.**
- Recommendation: do (1) now regardless — a false security record should not survive a phase that
  knows it is false — and decide (2) separately on its own evidence.

Related: [[project_functional_review_findings_unverified]] (symptoms reliable, scope often wrong —
reproduce before actioning).
