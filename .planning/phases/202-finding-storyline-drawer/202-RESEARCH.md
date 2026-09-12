# Phase 202: Finding Storyline Drawer - Research

**Researched:** 2026-09-12
**Domain:** FastAPI read-only endpoint over three independently-evolved finding vocabularies + React/Radix Sheet a11y extension
**Confidence:** MEDIUM — the frontend/Sheet/a11y-harness portion is HIGH confidence (mechanical, verified against source); the backend join (Q1/Q2/Q3) is HIGH-confidence-that-a-problem-exists but the problem is materially worse than either CONTEXT.md or the UI-SPEC assumed. This is reported loudly below, as instructed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — Score-lift attribution is THEME-framed, with the finding's share shown (STORY-02).** The
drawer renders the owning theme's title, the theme's lift with its condition stated, this finding's
position in the theme, and an explicit line that the number is not an individual contribution.
Explicitly REJECTED: dividing `theme_lift / constituent_count` to manufacture a per-finding share —
treat a division here as a blocker. Honest absence inherited from `schemas.py:496-501` — `None`
never renders as `0`.

**D-02 — Narrative arrives via ONE new lazy per-finding endpoint (STORY-01).**
`GET /api/findings/{id}/storyline` (auth-gated like every other route), returning the narrative plus
the D-01 theme attribution, assembled SERVER-SIDE from the existing catalogs. Lazy-fetch-on-open, not
a widened `/api/scan/latest` payload. **This research found the literal endpoint mechanism needs a
disambiguating query parameter and a corrected join — see Q1/Pitfall 1 below; the endpoint SHAPE
(one new lazy per-finding GET route) is unaffected.**

**D-03 — Reuse the existing `Sheet` primitive; do NOT add a drawer library.** No `vaul` or other
drawer dependency.

**D-04 — Extend the EXISTING a11y harness with a drawer capture (success criterion 4).**
`src/dashboard/tests/a11y/run-a11y.mjs`, `pinned-deps.test.ts`, `@axe-core/puppeteer` pinned 4.11.3.
No new tooling, no new runner.

**D-05 — No fourth narrative generator (success criterion 2, locked by the ROADMAP).** Narrative MUST
be sourced from the Phase-99 `ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG` catalogs. If the catalogs are
insufficient for a finding class, surface that gap explicitly (honest absence) — never write new
narrative text in the dashboard layer.

### Claude's Discretion

Component file layout and naming, the endpoint's exact response field names, test file organisation,
and how the theme-attribution block is visually arranged within the drawer (subject to the UI-SPEC).

### Deferred Ideas (OUT OF SCOPE)

- Per-finding score-lift as a genuinely computed number (rather than D-01's theme framing).
- Drawer content in the PDF/print surface.
- `int(delta)` lift truncation (`quirk/intelligence/score_lift.py:164`) — tracked separately at
  `.planning/phases/201-score-lift-roadmap-re-frame/deferred-items.md` item 4. Do NOT address here.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STORY-01 | Operator can open a per-finding storyline drawer from the dashboard findings table, with narrative sourced from the existing Phase-99 catalogs (`ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG`) — no forked fourth narrative generator | See "Architecture Patterns" (route + Sheet extension), "Code Examples" (`_classify_finding` reuse), and Pitfall 2 (title-vocabulary bridge needed for the narrative lookup to actually fire for dashboard-sourced findings) |
| STORY-02 | The drawer shows the finding's score-lift attribution, consuming LIFT-01's per-item number (sequenced after the LIFT phase) | See Q1/Q2/Q3 answers, "Don't Hand-Roll" (`item_progress`, `compute_item_lifts`), and Pitfall 3 (multi-theme tie-break needed before "the" theme's lift can be selected) |
</phase_requirements>


## Summary

D-02's literal endpoint shape (`GET /api/findings/{id}/storyline`) and the UI-SPEC's stated derivation
mechanism (`slug_for_title()` on the finding's own title) do not survive contact with the actual
codebase. Three separate, previously-unverified facts change the plan's shape:

1. **`FindingItem.id` is not a finding identifier — it is `CryptoEndpoint.id`, reused across every
   finding synthesized from that one endpoint row.** A single TLS endpoint routinely produces 2-4
   `FindingItem`s (e.g. legacy TLS + weak ciphers + self-signed cert) that all carry the *same* `id`.
   The literal route `GET /api/findings/{id}/storyline` cannot disambiguate which of those findings
   the operator clicked. **This forces a route signature change: the path `id` must be paired with a
   discriminating query parameter (title) — see Q1 below.**
2. **The dashboard's finding titles and the CLI scan pipeline's finding titles are two independently
   maintained vocabularies for the same conditions, and they diverge for most TLS-hygiene finding
   classes** (e.g. dashboard emits `"Legacy TLS version: TLSv1.1"`; the CLI emits `"Legacy TLS
   versions allowed (TLS 1.0/1.1)"`). `RemediationItemFingerprint` rows are keyed on the CLI's
   vocabulary. A naive fingerprint computed from the dashboard's `FindingItem.title` will silently
   fail to match for roughly half of the finding classes that DO have real theme membership, and will
   render as false A1 ("not mapped") rather than true theme data.
3. **A finding can constitute more than one theme simultaneously, and this is common in real data
   (42% of distinct fingerprints in this repo's live dev DB), not an edge case** — the
   `high-impact-findings` theme is a severity catch-all (any HIGH/CRITICAL finding, whatever its
   title) layered on top of the title-based themes, so most HIGH-severity findings belong to *two*
   `RemediationItemFingerprint` rows under two different slugs. D-01's "the owning theme" (singular)
   does not exist as a data-model invariant; a real design decision is needed for which theme wins,
   and it is not addressed by CONTEXT.md or the UI-SPEC.

None of this contradicts D-01/D-02/D-05's *outcomes* — theme framing, one lazy endpoint, catalog reuse
— but it does mean the *mechanism* named in D-02's prose (`slug_for_title()` on the finding title) is
wrong for the finding-to-theme join and must not be implemented literally. The correct join is a
computed-`finding_fingerprint` lookup against `RemediationItemFingerprint` (see Q1), and a tie-break
rule is needed for the multi-theme case (see "Design tension" below).

**Primary recommendation:** keep D-02's endpoint path shape but add a required `title` query parameter
for disambiguation; join via computed `finding_fingerprint`, not `slug_for_title(finding.title)`;
pick the theme deterministically by priority order (`_SLUG_PRIORITY`, already present) when a finding
constitutes more than one; and treat A5 (no catalog narrative) as the *common* case for TLS-hygiene
findings, not a rare edge case, because `ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG` are scoped to named
cryptographic algorithms only.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Finding → theme fingerprint join, narrative lookup, lift computation | API / Backend | Database / Storage | All three catalogs (`REMEDIATION_CONSTITUENCY`, `ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG`, `RemediationItemFingerprint`) are Python/SQL-only; D-02 forces this assembly server-side |
| Drawer open/close/focus, loading skeleton, absence copy | Browser / Client | — | Pure Radix `Sheet` state + fetch-on-open; no server round trip needed for open/close mechanics |
| a11y baseline capture (open-drawer axe scan) | Browser / Client (headless, build-time) | — | `run-a11y.mjs` runs against the built preview server; it is a client-rendered surface being probed, not a backend concern |
| Persisted remediation membership (`RemediationItemFingerprint`) | Database / Storage | API / Backend (read) | Written once per scan by `run_scan.py`'s CLI pipeline; the dashboard/API only reads it — this phase must not write to it |

## Standard Stack

No new libraries. This phase is 100% additive within the existing stack (FastAPI + Pydantic v2 +
SQLAlchemy on the backend; React + TanStack Table + Radix `Dialog`-based `Sheet` + lucide-react on the
frontend). D-03 explicitly forbids adding a drawer library.

### Core (already in the repo — reused only)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@radix-ui/react-dialog` | ^1.1.15 (`src/dashboard/package.json:25`) | Underlies `Sheet` | Already the drawer primitive per D-03 |
| `@axe-core/puppeteer` | 4.11.3 pinned (`pinned-deps.test.ts`) | a11y capture | D-04's existing harness |
| FastAPI / Pydantic v2 | already installed | new route + response model | matches every other dashboard route |

### Package Legitimacy Audit

**Not applicable.** This phase introduces zero new external packages (D-03 forbids `vaul` or any
drawer dependency; no new Python dependency is needed). No `slopcheck`/registry run was performed
because there is nothing to install.

## Architecture Patterns

### System Architecture Diagram

```
[Findings table row]
        |  operator clicks "Storyline" button (new, focusable, F1)
        v
[findings.tsx: setSelectedFinding + open drawer immediately]
        |  Sheet opens synchronously with FindingItem data already in hand
        |  (title, host, port, severity, description, remediation, quantum_risk)
        |
        |  lazy fetch: GET /api/findings/{id}/storyline?title=<url-encoded title>
        v
[quirk/dashboard/api/routes/scan.py (or new storyline.py), auth-gated]
        |
        |-- 1. Resolve CryptoEndpoint by id -> host, port, scan_run_id
        |-- 2. Disambiguate WHICH finding via title query param
        |       (re-run the single-endpoint slice of _derive_findings,
        |        match against the requested title; 404/absence if no match)
        |-- 3. compute_fingerprint({host, port, title}) via
        |       TicketingChannel.compute_fingerprint  (SHA256, no DB hit)
        |-- 4. Narrative: _classify_finding-style keyword match against
        |       ALGO_IMPACT_MAP / REMEDIATION_CATALOG (Phase 99, D-05)
        |-- 5. Theme membership: query RemediationItemFingerprint WHERE
        |       scan_run_id=X AND finding_fingerprint=fp
        |       -> may return 0, 1, or 2+ rows (multi-theme case)
        |-- 6. Per matched slug: item_progress(scan_run_id, slug) for
        |       closed/total, ORDER BY finding_fingerprint for position,
        |       and compute_item_lifts(evidence, items, profile) for lift
        v
[FindingStoryline JSON response] --> drawer renders S1-S8 per UI-SPEC
```

### Recommended Project Structure
```
quirk/dashboard/api/routes/
├── scan.py                  # OR a new storyline.py — see Claude's Discretion note below
quirk/dashboard/api/
├── schemas.py                # + FindingStoryline response model
src/dashboard/src/
├── pages/findings.tsx        # + Storyline column, trigger button, drawer extension
├── types/api.ts               # + FindingStoryline interface, id: number | null fix
├── hooks/useFindingStoryline.ts   # new fetch hook (mirrors useHardwareDrift.ts's `const url = ...` shape for F10b's extractor)
src/dashboard/tests/a11y/
├── run-a11y.mjs                # + per-route interaction step (F10a)
├── routes.json                 # (contentMarker only — NOT where the interaction step lives, per F10a)
├── fixture-coverage.test.ts    # + HOOK_TARGETS entry (F10b)
├── vite.config.ts              # + /api/findings fixture handler (F10b)
```

**Claude's Discretion note (route module placement):** `scan.py` is already 2100+ lines and already
owns `_derive_findings`, `CryptoEndpoint` queries, and the auth-gated `router`. A new `storyline.py`
route module registered the same way as `connectors.py` (own `APIRouter(dependencies=[Depends(require_auth)])`,
`include_router(storyline.router, prefix="/api")` in `app.py`) keeps the new join logic isolated and
independently testable, at the cost of importing `_derive_findings` (or a shared helper extracted from
it) across modules. Either is workable; a shared helper function
`_finding_by_id_and_title(db, id, title) -> Optional[FindingItem]` extracted from `_derive_findings`'s
per-endpoint loop is the cleanest boundary regardless of which file hosts the new route.

### Pattern: auth-gated read-only router (Q4)
```python
# Source: quirk/dashboard/api/routes/connectors.py:16-44 (verified 2026-09-12)
from fastapi import APIRouter, Depends, HTTPException
from quirk.dashboard.api.middleware.auth import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])

@router.get("/findings/{finding_id}/storyline", response_model=FindingStoryline)
def get_finding_storyline(finding_id: int, title: str, db: Session = Depends(get_db)) -> FindingStoryline:
    try:
        ...
    except Exception as exc:
        # Never str(exc) — connectors.py's own T-193-15 precedent, avoids leaking paths.
        raise HTTPException(status_code=500, detail="Storyline lookup failed") from exc
```
`scan.py`'s own router is built identically at `quirk/dashboard/api/routes/scan.py:106`
(`router = APIRouter(dependencies=[Depends(require_auth)])`) — whichever file hosts the new route,
this is the only construction pattern used anywhere in `quirk/dashboard/api/routes/`.

### Anti-Patterns to Avoid
- **Calling `slug_for_title(finding.title)` on a raw dashboard finding title** — that function is for
  *roadmap item* titles (`"Disable legacy TLS versions"`), not finding titles (`"Legacy TLS version:
  TLSv1.1"`). It will return `None` for virtually every real finding, manufacturing false A1s.
- **Trusting `FindingItem.id` alone as a fetch key without a disambiguator.** Verified: the same `id`
  (`CryptoEndpoint.id`) backs multiple `FindingItem`s at `quirk/dashboard/api/routes/scan.py:138,155,172,194,209,236,266,288,316` — one `ep.id` per line, all inside the same `for ep in endpoints:` loop (`:129`).
- **Assuming `remediation_item_fingerprints` always exists as a table.** DBs that predate Phase 179
  raise `OperationalError: no such table` on a bare query — verified against `./.planning/quirk.db`,
  `./data/quirk.db`, `./quirk/quirk-output/quirk.db` in this repo (see Environment Availability). Any
  query against this table must be wrapped the same "advisory bookkeeping, never fail the request"
  way `_derive_roadmap` wraps its own closure-state and lift lookups
  (`quirk/dashboard/api/routes/scan.py:1140-1147,1163-1167`, both `except Exception: logger.exception(...)`
  degrading to an empty dict).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Finding fingerprint | A new hash formula | `TicketingChannel.compute_fingerprint` (`quirk/ticketing/base.py:110-116`) | Single source of truth for the SHA256(host:port::normalized-title) formula; a second implementation would drift the moment `FINGERPRINT_TITLE_ALIASES` changes |
| Closed/total counts | A raw COUNT query | `item_progress(session, scan_run_id=, slug=)` (`quirk/intelligence/remediation.py:161-181`) | Already exists, already tested, already the function D-01 cites by name |
| Theme lift number | Re-deriving from `RoadmapNode` | `compute_item_lifts(evidence, items, profile=)` (`quirk/intelligence/score_lift.py:131-161`), the same call `_derive_roadmap` makes | Guarantees the drawer's number is identical to the roadmap page's number for the same slug — two independent computations of the same lift is exactly the drift class Phase 201 fixed with `formatScoreNumber()` |
| Number formatting | `.toFixed()` / raw interpolation | `formatScoreNumber()` (`src/dashboard/src/lib/utils.ts:15-16`) | UI-SPEC's Number Formatting Contract; locked, not discretionary |

**Key insight:** every piece of this feature already exists somewhere in the codebase as a tested,
named function. The entire implementation risk is in the *join order* between them (fingerprint →
scan_run_id → slug → item_progress/compute_item_lifts), not in writing new logic.

## Common Pitfalls

### Pitfall 1: `FindingItem.id` collisions across co-occurring findings on one endpoint (NEW — this phase's own root cause)
**What goes wrong:** Clicking "Storyline" on one row silently fetches the wrong finding's narrative/attribution.
**Why it happens:** `id=ep.id` is assigned identically to every `FindingItem` derived from the same `CryptoEndpoint` row (verified at `scan.py:138,155,172,194,209,236,266,288,316`); a TLS endpoint with, say, both a legacy-TLS-version finding and a self-signed-cert finding produces two rows sharing one `id`.
**How to avoid:** Route signature must accept a disambiguator (this research recommends `title` as a required query param, since `(host, port, title)` — already known client-side — is exactly what `compute_fingerprint` needs anyway) and the handler must re-derive the specific finding by matching that title against the endpoint's own candidate findings, not by trusting `id` alone.
**Warning signs:** A regression test that opens the drawer for the *second* finding on a multi-finding endpoint and asserts the narrative names that finding, not the first one found by `id`.

### Pitfall 2: dashboard-vs-CLI finding-title vocabulary drift silently produces false A1
**What goes wrong:** A finding that genuinely belongs to a theme (e.g. an expired cert) renders "Not mapped to a remediation theme" because the fingerprint computed from the dashboard's title (`"Certificate expired"`) never matches a `RemediationItemFingerprint` row written from the CLI's title (`"TLS certificate expired"`).
**Why it happens:** `quirk/dashboard/api/routes/scan.py`'s `_derive_findings()` and
`quirk/engine/findings_evaluator.py`'s `evaluate_endpoints()` are two independently-maintained finding
generators for the same underlying `CryptoEndpoint` conditions — confirmed by the explicit "DO NOT
UNIFY" comment at `quirk/dashboard/api/schemas.py:126-129`. `RemediationItemFingerprint` rows are
written from `evaluate_endpoints()`'s output only (`run_scan.py:4118`, `findings` = `evaluate_endpoints(cfg, endpoints)` at `run_scan.py:4071`).
**How to avoid:** The storyline route must map the endpoint's condition to the *CLI's* canonical title
before computing the fingerprint — not reuse the dashboard's own interpolated title verbatim. Concretely: build a small per-endpoint title-translation table (7-9 entries) mirroring the CLI's exact strings at `quirk/engine/findings_evaluator.py:542,557,573,597,614,640,658,682,703,722,741`, or (cleaner) extract a single shared "canonical finding title for this endpoint condition" helper that both `_derive_findings` and `evaluate_endpoints` can call, so the two vocabularies cannot diverge further. Given D-02's "reuse existing catalogs, no new generator" spirit, a translation table scoped to this phase (not a refactor of either generator) is the lower-risk choice — but it must be reviewed against the ~9 title pairs listed in this document's Q1 answer, not assumed to be a 1:1 match.
**Warning signs:** A finding whose title is byte-identical between the two generators (self-signed, untrusted-CA, undersized-RSA) works "by accident"; a finding whose title differs (HTTP, legacy-TLS, weak-cipher, expired-cert, expiring-cert) silently fails. A test matrix over all ~9 finding classes, not just one, is required to catch this.

### Pitfall 3: multi-theme membership has no "the theme" tie-break today
**What goes wrong:** D-01's copy ("Remediation theme: {theme_title}") assumes exactly one theme per finding; the query in Pitfall 1's fix can return 2+ `RemediationItemFingerprint` rows for the same `finding_fingerprint` under different slugs.
**Why it happens:** `REMEDIATION_CONSTITUENCY`'s `"high-impact-findings"` slug is `("severity", ())` — every HIGH/CRITICAL finding constitutes it, regardless of title, layered on top of any title-based theme match (`quirk/intelligence/remediation.py:98-101` in `_select_constituent_findings`'s severity branch, `remediation_persist.py:244-246`). Verified live: 28 of 67 distinct fingerprints (42%) in `./quirk-output/quirk.db` belong to 2+ slugs simultaneously.
**How to avoid:** Pick deterministically — the existing `_SLUG_PRIORITY` table (`quirk/intelligence/remediation_persist.py:59-74`) already ranks every slug by priority (10 = highest urgency to 920 = lowest); when a finding's fingerprint matches multiple rows, select the **lowest priority number** (i.e., the theme `build_phased_roadmap` would surface earliest) as "the" theme, and do not silently pick "whichever row the query returns first" (SQLite row order is not a stable API contract).
**Warning signs:** A finding's rendered theme differs between two otherwise-identical scan runs, or a plaintext-HTTP finding shows "high-impact-findings" as its theme (a title-blind catch-all label with no useful lift) instead of "plaintext-http-exposure" (the correct, more specific theme).

### Pitfall 4: `remediation_item_fingerprints` table may not exist at all on older DBs
**What goes wrong:** An unwrapped query 500s instead of degrading to honest absence.
**Why it happens:** the table was added in Phase 179; verified live against three DBs in this repo (`./.planning/quirk.db`, `./data/quirk.db`, `./quirk/quirk-output/quirk.db`) that predate it and raise `OperationalError: no such table: remediation_item_fingerprints` on a bare `sqlite3` query.
**How to avoid:** wrap the lookup in the same `try/except Exception: logger.exception(...)` + degrade-to-`None` pattern `_derive_roadmap` already uses for its own closure-state and lift lookups (`scan.py:1140-1147`, `:1163-1167`) so a missing table degrades to A3 (or a comparable honest-absence path), never a 500.
**Warning signs:** integration test against a pre-Phase-179 fixture DB (or a DB with the table simply empty) is required, not just the happy-path DB.

### Pitfall 5 (from parent brief, verified applicable): `.tsx` build discipline
**What goes wrong:** a plan ships source changes without rebuilt statics, and verification reports "feature missing" against stale `quirk/dashboard/static/`.
**Why it happens:** FastAPI serves pre-built statics; Phase 201 and Phase 195 both hit this.
**How to avoid:** `npm run build && npm run lint && npm run test` from `src/dashboard/`, commit the rebuilt `quirk/dashboard/static/` output alongside the source diff, every time a `.tsx` file changes in this phase.

### Pitfall 6 (from parent brief, verified applicable): `None` must never render as `0`
Verified as a real, already-encoded contract at `quirk/dashboard/api/schemas.py:496-501`'s comment
on `score_lift`, and restated as Invariant-adjacent language throughout the UI-SPEC (A2/A3/A4). Applies
identically to `theme_finding_count`, `theme_closed_count`, `finding_position` — a `!= null` guard,
never truthiness, per the UI-SPEC's Type Contract section.

### Pitfall 7: test interpreter
Use `.venv/bin/python` for any new pytest, never bare `python` — the system interpreter lacks
`sslyze` and produces 9 phantom connector failures unrelated to this phase (project-wide, verified
convention per prior phases' memory).

### Pitfall 8 (checked, not applicable): TRIAGE-149 report-writer seam
This phase does not touch `write_reports`/`render_pdf_report` — the drawer is explicitly excluded
from the print/PDF surface (CONTEXT.md `## Deferred Ideas`). No action needed, flagged only because
the parent brief asked it be checked.

## Code Examples

### Fingerprint computation (Q1's core join)
```python
# Source: quirk/ticketing/base.py:110-116 (verified 2026-09-12)
@staticmethod
def compute_fingerprint(finding: dict) -> str:
    host = str(finding.get("host") or "")
    port = str(finding.get("port") or "")
    title = normalize_finding_title(
        str(finding.get("title") or ""), FINGERPRINT_TITLE_ALIASES
    )
    raw = f"{host}:{port}::{title}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
```
This needs only `{host, port, title}` — no DB id required for the hash itself. The DB id is only
needed to resolve *which* `(host, port, title)` triple the operator meant (Pitfall 1).

### Theme membership + progress (Q2)
```python
# Source: quirk/intelligence/remediation.py:161-181 (verified 2026-09-12)
def item_progress(session, *, scan_run_id: str, slug: str) -> Tuple[int, int]:
    rows = (
        session.query(RemediationItemFingerprint)
        .filter(
            RemediationItemFingerprint.scan_run_id == scan_run_id,
            RemediationItemFingerprint.slug == slug,
        )
        .all()
    )
    total_count = len(rows)
    closed_count = sum(1 for row in rows if row.state == "closed")
    return (closed_count, total_count)
```
For `finding_position` (A4's ordering), sort the same `rows` by `finding_fingerprint` and find the
index of the requested fingerprint — this is the ordering the UI-SPEC's A4 entry already names as
"technically stable... `ORDER BY finding_fingerprint`" (`quirk/models.py:691` NOT NULL,
`quirk/models.py:681-683` unique constraint — verified, exact lines).

### Narrative keyword classification (Q3)
```python
# Source: quirk/reports/content_model.py:690-710 (verified 2026-09-12)
def _classify_finding(finding: Dict[str, Any]) -> Optional[str]:
    severity = str(finding.get("severity", "")).upper()
    if severity not in _RISK_SEVERITY_INCLUDE:   # {"CRITICAL","HIGH","MEDIUM"}
        return None
    search_text = " ".join([
        str(finding.get("title", "")), str(finding.get("description", "")),
        str(finding.get("category", "")), str(finding.get("check_id", "")),
    ]).upper()
    for keyword in _ALGO_KEYWORDS:   # RSA, ECC, ECDSA, DH, DSA, WEAK_HASH, MD5, SHA1, ... (content_model.py:442-457)
        if keyword.upper() in search_text:
            return keyword
    return None
```
Reuse this exact function (or import it) for the drawer's narrative section — do not reimplement the
keyword list, per D-05.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| n/a | n/a | n/a | This phase is additive to a stable, recently-hardened (Phase 199-201) scoring/roadmap stack; no external state-of-the-art shift applies |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `title` is the correct, sufficient disambiguator to add as a query param alongside `id` (rather than e.g. a synthetic per-response finding index) | Pattern / Pitfall 1 | If two co-occurring findings on the same endpoint ever share both `id` AND `title` (not observed in current `_derive_findings` — every title differs within one endpoint's finding set), disambiguation would still fail; low risk given current finding-generation code, but not schema-enforced |
| A2 | The `_SLUG_PRIORITY` table is the right tie-break for multi-theme membership (Pitfall 3) | Common Pitfalls | This is Claude's Discretion-adjacent but touches D-01's "the theme" framing; if the operator would rather see the MORE SPECIFIC theme win over the severity catch-all (opposite of lowest-priority-number-wins when `high-impact-findings` is priority 20, near the top), the tie-break direction would need to flip. This is exactly the class of decision this research recommends the planner surface back to CONTEXT rather than silently pick |
| A3 | A per-endpoint title-translation table (Pitfall 2) is lower-risk than extracting a shared canonical-title helper used by both `_derive_findings` and `evaluate_endpoints` | Pitfall 2 | If a future finding class is added to only one of the two generators, the translation table silently goes stale exactly like the drift it exists to fix — this is a known, named trade-off, not an oversight |
| A4 | `evaluate_endpoints(cfg, endpoints)`'s finding dicts and `_derive_findings(endpoints)`'s `FindingItem`s are produced from the SAME underlying `CryptoEndpoint` rows for the SAME scan (i.e., the translation table in Pitfall 2 is 1:1 per condition, not N:1) | Pitfall 2 | Verified by reading both functions' trigger conditions side by side (same `ep.protocol`/`ep.tls_version`/etc. fields), but not verified by running both against the same live scan and diffing counts — recommend the planner add exactly this as a Wave 0 regression test |

## Open Questions

1. **Which theme wins when a finding constitutes 2+ themes (Pitfall 3)?**
   - What we know: it happens in ~42% of real fingerprints in this repo's dev DB; `_SLUG_PRIORITY` gives one plausible deterministic tie-break.
   - What's unclear: whether the operator would prefer the most-specific theme, the highest-lift theme, or the `_SLUG_PRIORITY`-first theme — these three rules pick different winners in different cases.
   - Recommendation: this is a plan-shape decision the planner should either resolve explicitly (documenting the rule as a new D-NN-equivalent) or send back through discuss-phase before execution, since it directly affects what text the operator reads for ~4 in 10 findings that have any theme at all.

2. **Should the drawer disclose that a finding belongs to more than one theme, or silently show only the winner?**
   - What we know: UI-SPEC's copywriting/state matrix has no slot for "this finding also touches theme Y."
   - What's unclear: whether silently picking one theme (per Q1 above) is itself an honesty violation of the spirit of D-01 ("resolving this finding alone does not yield the full amount") if the *other* theme's lift is left completely unmentioned.
   - Recommendation: given D-05/UI-SPEC's locked copy contract and the phase's discretion boundaries, the safest reading is: show one theme (the tie-break winner) and do not invent new UI states for the multi-theme case in this phase — but call this out explicitly as a known simplification in the plan's SUMMARY, since a future phase may need to surface it.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `remediation_item_fingerprints` table | Theme/lift join | ✓ in `./quirk-output/quirk.db` (169 rows, 14 scan_run_ids) | Phase 179 schema | ✗ absent entirely in 3 other local DBs checked (`./.planning/quirk.db`, `./data/quirk.db`, `./quirk/quirk-output/quirk.db`) — must degrade to honest absence, not 500 (Pitfall 4) |
| `.venv/bin/python` | pytest | ✓ | project venv | bare `python` produces 9 phantom failures — do not use |
| Node/npm + `src/dashboard/node_modules` | vitest, a11y harness | ✓ (verified: `@radix-ui/react-dialog` present at `src/dashboard/node_modules/@radix-ui/react-dialog/dist/index.mjs`) | ^1.1.15 pinned | — |

**Missing dependencies with no fallback:** none — the table-absence case has an honest-absence fallback (Pitfall 4).

## Validation Architecture

`nyquist_validation: true` in `.planning/config.json:19` — this section is required.

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest (`.venv/bin/python -m pytest`), config `pyproject.toml:151` `[tool.pytest.ini_options]` |
| Frontend framework | vitest ^2.1.9 (`src/dashboard/package.json`), `npm run test` = `vitest run` |
| a11y framework | Puppeteer + `@axe-core/puppeteer` 4.11.3 via `src/dashboard/tests/a11y/run-a11y.mjs` |
| Quick run (backend) | `.venv/bin/python -m pytest tests/test_dashboard_api.py -k storyline -x` |
| Quick run (frontend) | `cd src/dashboard && npm run test -- findings` |
| Full suite | `.venv/bin/python -m pytest -q -m ""` (backend) + `cd src/dashboard && npm run build && npm run lint && npm run test` (frontend) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STORY-01 | `GET /api/findings/{id}/storyline` returns narrative from `ALGO_IMPACT_MAP`/`REMEDIATION_CATALOG`, no forked generator | integration (backend) | `.venv/bin/python -m pytest tests/test_dashboard_finding_storyline.py -x` | ❌ Wave 0 |
| STORY-01 | Drawer trigger keyboard-operable, opens without leaving findings view | vitest component | `npm run test -- findings.storyline` | ❌ Wave 0 |
| STORY-02 | Theme-framed attribution block matches Invariants 1-3 exactly | vitest component (rendering assertion, per UI-SPEC Invariant 3's `3.5`/`3` absence check) | `npm run test -- storyline-attribution` | ❌ Wave 0 |
| STORY-02 (success criterion 4) | a11y baseline for open/close/focus | a11y capture | `node src/dashboard/tests/a11y/run-a11y.mjs` (against built preview) | Harness exists; new interaction step + fixture handler ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the relevant quick-run command above.
- **Per wave merge:** full backend + frontend suites, plus `run-a11y.mjs` against a fresh `npm run build` preview.
- **Phase gate:** all green, plus `fixture-coverage.test.ts` (HOOK_TARGETS) and `pinned-deps.test.ts` unchanged-pass, before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_dashboard_finding_storyline.py` — new backend integration test file covering: single-theme finding, multi-theme finding (Pitfall 3), unmapped finding (true A1), missing-table DB (Pitfall 4), id-collision disambiguation via `title` (Pitfall 1), and the dashboard-vs-CLI title divergence for at least the 5 diverging finding classes named in Pitfall 2.
- [ ] `src/dashboard/src/hooks/useFindingStoryline.ts` + its `.test.ts` — new fetch hook, following the `const url = "..."` or template-literal shape one of the existing `HOOK_TARGETS` extractors expects (`extractQuotedConstUrl` vs `extractTemplateLiteralPrefix`, `fixture-coverage.test.ts:45-56` region).
- [ ] `src/dashboard/tests/a11y/vite.config.ts` — new `/api/findings` prefix handler (F10b).
- [ ] `src/dashboard/tests/a11y/fixture-coverage.test.ts` — new `HOOK_TARGETS` entry for the storyline hook (F10b).
- [ ] `src/dashboard/tests/a11y/run-a11y.mjs` — new per-route interaction step, `default`-variant-only (F10a/F10c).

## Security Domain

`security_enforcement` is absent from `.planning/config.json` → treat as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (inherited) | `Depends(require_auth)` at router construction, matching every other dashboard route |
| V3 Session Management | no | no new session concept introduced |
| V4 Access Control | yes (inherited) | same auth dependency; no per-finding ownership model exists in this app, so no additional row-level check is needed beyond "authenticated at all" |
| V5 Input Validation | yes | `finding_id: int` path param (FastAPI type coercion -> 422 on non-numeric); `title: str` query param must be length-bounded and not reflected raw into any error message (avoid a reflected-value 500 detail string, per the fixed-string precedent) |
| V6 Cryptography | no direct use | fingerprint computation reuses existing SHA256 helper; no new cryptographic primitive introduced |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Information disclosure via exception detail | Information Disclosure | Fixed 500 detail string, never `str(exc)` — `connectors.py`'s own T-193-15 precedent, verified at `quirk/dashboard/api/routes/connectors.py:38-44` |
| Reflected query param in error text | Information Disclosure | Do not interpolate the `title` query param into any HTTP error detail; log server-side only if needed |
| ID enumeration (`finding_id` is a small sequential int) | Information Disclosure (low severity) | Already true of every other `id`-keyed field in this app (`CryptoEndpoint.id` is sequential); auth gate is the existing, accepted mitigation — no new control needed for this phase |

## Sources

### Primary (HIGH confidence — read directly from this repo, line numbers verified 2026-09-12)
- `quirk/models.py:653-693` (`RemediationItemFingerprint` class + docstring)
- `quirk/dashboard/api/schemas.py:126-152,483-501` (`FindingItem`, `RoadmapNode.score_lift`)
- `quirk/dashboard/api/routes/scan.py:106,120-334,1104-1207,1536-1650` (`_derive_findings`, `_derive_roadmap`, `get_latest_scan`)
- `quirk/dashboard/api/routes/connectors.py:1-65` (auth-gated router pattern)
- `quirk/intelligence/remediation.py:31-181` (`REMEDIATION_KIND_SLUGS`, `REMEDIATION_CONSTITUENCY`, `slug_for_title`, `item_progress`)
- `quirk/intelligence/remediation_persist.py:1-276` (the actual Phase-179 write site, `_select_constituent_findings`, `_normalized`)
- `quirk/intelligence/score_lift.py:131-161` (`compute_item_lifts`)
- `quirk/ticketing/base.py:70-116` (`compute_fingerprint`)
- `quirk/compliance/__init__.py:109-211` (`normalize_finding_title`, `FINGERPRINT_TITLE_ALIASES`)
- `quirk/reports/content_model.py:232-457,690-710` (`ALGO_IMPACT_MAP`, `REMEDIATION_CATALOG`, `_classify_finding`, `_ALGO_KEYWORDS`, `_RISK_SEVERITY_INCLUDE`)
- `quirk/engine/findings_evaluator.py:441-956` (`evaluate_endpoints`, the CLI's own title vocabulary)
- `run_scan.py:4071,4104-4124` (call sites proving `findings` = `evaluate_endpoints(...)` output, and `persist_remediation_snapshot` call)
- `src/dashboard/src/pages/findings.tsx:69-256` (existing Sheet, TanStack Table `row.id` not `FindingItem.id`)
- `src/dashboard/src/lib/utils.ts:15-16` (`formatScoreNumber`)
- `src/dashboard/src/types/api.ts:45-52` (current `FindingItem.id?: number`)
- `src/dashboard/vite.config.ts:8-172` (`a11yFixture()`, 9 existing `startsWith` prefixes)
- `src/dashboard/tests/a11y/fixture-coverage.test.ts:30-84` (`HOOK_TARGETS`, extractor functions)
- `src/dashboard/tests/a11y/run-a11y.mjs:63,145-192` (`ROUTES` destructure, console capture, `contentMarker` gate)
- `src/dashboard/tests/console-allowlist.json` (exactly one entry, verified)
- `src/dashboard/node_modules/@radix-ui/react-dialog/dist/index.mjs:237,301-313` (`DescriptionWarning`, no `NODE_ENV` guard)
- `./quirk-output/quirk.db` (live query: 169 fingerprint rows / 14 scan_run_ids; 3 of those 14 have 0 rows; 28 of 67 distinct fingerprints span 2+ slugs)
- `./.planning/quirk.db`, `./data/quirk.db`, `./quirk/quirk-output/quirk.db` (live query: table absent — pre-Phase-179 schema)
- `.planning/ROADMAP.md:338-357`, `.planning/REQUIREMENTS.md:63-70,112-113`, `.planning/config.json:19`

### Secondary / Tertiary
None used — every claim above was verified directly against this repository's source or live local
databases rather than external search, because the research questions were entirely internal to this
codebase's own two finding-generation paths.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, all reuse of already-vendored/pinned code
- Architecture (route pattern, Sheet extension, a11y wiring): HIGH — every claim checked against source at a specific line
- Finding→theme join (Q1/Q2/Q3, the load-bearing part): MEDIUM — the *existence* of the three problems (id collision, title-vocabulary drift, multi-theme membership) is HIGH confidence (verified by reading source and querying a live DB), but the *recommended fix* for each (title query param, translation table, `_SLUG_PRIORITY` tie-break) is a reasoned proposal, not something already implemented elsewhere to copy verbatim — the planner should treat these three fixes as needing explicit sign-off, not silent adoption

**Research date:** 2026-09-12
**Valid until:** 30 days (stable, internally-verified codebase facts; re-verify if Phase 201's `int(delta)` truncation deferred item is ever picked up, since it would change `compute_item_lifts`' return type from `int` to `float` and interact with the Number Formatting Contract's `4.27` test case)
