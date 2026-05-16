# Phase 77: INFO/Code Quality + Audit Ledger Closure - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Close all 29 INFO-severity audit findings across the four subsystems (protocol scanner, CBOM/intelligence, API/CLI, React frontend) AND bring `AUDIT-TASKS.md` to **zero bare-open rows** — every one of the 169 findings carries an explicit closed, deferred-with-rationale, or wont-fix-with-rationale disposition. This is the **milestone-completion gate** for v4.9.

**In scope (mapped to INFO-NN + LEDGER-01):**

- **INFO-01** — Protocol scanner INFOs (closes scanners-protocol/IN-01..06)
- **INFO-02** — CBOM/intelligence INFOs (closes cbom-intel-reports/IN-01..09)
- **INFO-03** — API/CLI INFOs (closes api-cli-core/IN-01..07)
- **INFO-04** — React frontend INFOs (closes react-frontend/IN-01..07)
- **LEDGER-01** — All 4 bare `[ ] deferred-*` and `[ ] wont-fix` rows in AUDIT-TASKS.md gain inline rationale; final invariant: zero `[ ] open` rows remain

**Out of scope:**

- All BLOCKER and WARNING rows (closed by Phases 58, 59, 60, 61, 62, 64.1, 69, 70, 71, 72, 73, 74, 75, 76)
- Any new feature work — v5.0 starts fresh
- Any UAT-SERIES new test cases — these are internal code-quality polish

</domain>

<decisions>
## Implementation Decisions

### Protocol scanner INFOs (INFO-01)

- **D-01 (IN-01):** Add a 3-line comment above the SSLContext downgrade site in `quirk/util/tls_capabilities.py` (or wherever) explaining WHY the downgrade is necessary (legacy server probing). Cite the audit row.
- **D-02 (IN-02):** Add DNSSEC algorithm 9 (RSASHA1-NSEC3-SHA1) and 11 (Reserved per RFC 8624) to `DNSSEC_ALG_MAP` in `quirk/scanner/dnssec_scanner.py`. Both flagged as legacy/weak per RFC.
- **D-03 (IN-03):** `SHA1_INDICATORS` substring matching tightened via the Phase 74 `quirk/assessment/migration_advisor.py::_matches` word-boundary helper (or the Phase 73 `quirk/util/weak_crypto.py::is_weak_cipher` if SHA1 is already in the token set there). Researcher confirms which reuse is cleaner.
- **D-04 (IN-04):** `quirk/scanner/fingerprint.py::_http_probe_plain` Host header set to the actual target hostname, not literal `localhost`. Fixes virtual-host routing in HTTP probes.
- **D-05 (IN-05):** `_is_pfs` / `_is_weak` duplicated across email/broker/tls scanners deduplicated into a single helper. If suitable, consolidate into `quirk/util/weak_crypto.py` (Phase 73 NEW). Else create `quirk/util/tls_cipher_classify.py`.
- **D-06 (IN-06):** `kerberos_scanner.py::_derive_realm` IPv4 detection currently uses dotted-quad string heuristic. Replace with `try: ipaddress.ip_address(host); except ValueError: ...` block.

### CBOM/intelligence INFOs (INFO-02)

- **D-07 (IN-01):** PLATFORM_VERSION single source: `__version__` in `quirk/__init__.py`. All other modules import via `from quirk import __version__ as PLATFORM_VERSION`. Researcher inventories the 4-6 duplicate sites.
- **D-08 (IN-02):** `_extract_ssh_algorithms` `JSONDecodeError` no longer silent; `except json.JSONDecodeError as e: logger.warning("...: %s", safe_str(e)); return []`.
- **D-09 (IN-03):** Trend analysis fetches all endpoints into memory per session. Add a streaming query (`yield_per(N)`) or batch by chunk_size=1000. Researcher confirms the SQLAlchemy session shape.
- **D-10 (IN-04):** `evidence.py::_PROTOCOL_KEYS` extended to include CONTAINER, SOURCE, AWS, AZURE, GCP, K8S, VAULT (researcher confirms the missing keys against the canonical scan_json shape).
- **D-11 (IN-05):** Roadmap baseline-governance item should appear when len < min_items AS WELL AS when no baseline-governance item exists. Add a separate check.
- **D-12 (IN-06):** Migration Paths truncation at 10 gains an indicator: `... and {remaining} more (see full report)`.
- **D-13 (IN-07):** `html_renderer::roadmap_section` dead timeframe-comparison branch removed (researcher locates the unreachable condition; verifies via mutation test).
- **D-14 (IN-08):** `writer::hosts_count` set with falsy hosts collapses to single `""`. Filter out falsy hosts before set construction.
- **D-15 (IN-09):** Delete `quirk/intelligence/schema.py::IntelligenceReport` dataclass entirely. Researcher confirms zero importers via `grep -r "IntelligenceReport" quirk/ tests/`.

### API/CLI INFOs (INFO-03)

- **D-16 (IN-01):** QRAMM endpoint return types tightened from `Dict[str, Any]` to TypedDict or explicit dataclass. Researcher inventories which endpoints + scope to the worst offenders.
- **D-17 (IN-02):** `_FACES` banner `\-` escape: replace with literal `-` (the backslash was a docs misreading). Update the misleading comment.
- **D-18 (IN-03):** Interactive TZ fallback emits IANA name (`"UTC"`) not legacy abbreviation string.
- **D-19 (IN-04):** QRAMM magic numbers (0.8, 1.5, 0.10, 0.20) extracted to named constants in `quirk/qramm/scoring.py`: `MULTIPLIER_MIN = 0.8`, `MULTIPLIER_MAX = 1.5`, `MULTIPLIER_LOW_STEP = 0.10`, `MULTIPLIER_HIGH_STEP = 0.20`. Add a docstring tying these to Phase 54 / Phase 75 D-06.
- **D-20 (IN-05):** `app.py` closure-via-default-argument bug — `def _route(req, _store=store)` pattern to capture the `store` reference at definition time. Researcher locates the missing `=` pattern.
- **D-21 (IN-06):** `db.py` `_ensure_*_columns` family collapses to a single generic helper `_ensure_columns(table, expected_cols)`. Researcher inventories all `_ensure_*_columns` functions.
- **D-22 (IN-07):** `quirk/util/targets.py::projected_probe_count` switches from `list(network.hosts())` to `network.num_addresses` attribute access (O(1) count). Zero-memory.

### React frontend INFOs (INFO-04)

- **D-23 (IN-01):** `qramm-assessment.tsx` comment claiming 5-tab updated to 6-tab (or wherever the inaccuracy is). Comment-only.
- **D-24 (IN-02):** `cbom.tsx` / `roadmap.tsx` Cytoscape extension try/catch logs the error instead of swallowing. Pattern: `try {...} catch (e) { console.error('Cytoscape extension registration failed:', e); throw e; }` — re-throw so the visualization fails loudly rather than silently.
- **D-25 (IN-03):** `findings.tsx` / `identity.tsx` column arrays memoized via `useMemo` — currently recreated each render.
- **D-26 (IN-04):** `useQRAMMSession::seededRef` resets to `false` on "New Assessment" flow trigger.
- **D-27 (IN-05):** `cbom.tsx::compByAlg` lookups currently use `[0]` for representative; replace with explicit "first non-zero" or median selection — researcher confirms the desired statistic.
- **D-28 (IN-06):** `print.tsx` `React.createElement` style injection replaced with standard JSX `<style>` element or `useEffect` DOM mutation pattern.
- **D-29 (IN-07):** `useScanData` error propagates the actual fetch URL into the error message: `throw new Error(`Failed to fetch ${url}: ${response.statusText}`)`.

### Audit ledger zero-bare-open (LEDGER-01)

- **D-30 (locked):** Inventory the 4 bare `[ ] deferred-*` / `[ ] wont-fix` rows. For each, append inline rationale matching existing closed-row format:
  - `scanners-cloud/CR-01` (migration_planner.py stub) — already has rationale; verify
  - Any others (researcher inventories)
- **D-31 (locked):** Final invariant assertion: `grep -c "^\| .* \[ \] open" .planning/audit-2026-05-08/AUDIT-TASKS.md` returns `0`. Add a CI test `tests/test_audit_ledger_zero_open.py` asserting this.

### Phase-77 do-not-touch list

- **D-32 (locked):**
  - No new features
  - No CLI flag changes
  - No schema migrations
  - No new pip dependencies
  - QRAMM 120-question taxonomy
  - Recharts component swaps
  - All Phase 72-76 fixes preserved exactly

</decisions>

<canonical_refs>
## Canonical References

- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — 29 INFO rows + 4 bare deferral rows + the zero-bare-open invariant
- `.planning/REQUIREMENTS.md` — INFO-01..INFO-04, LEDGER-01
- `.planning/ROADMAP.md` Phase 77 — 5 SCs (gating; SC-5 is the zero-bare-open invariant)
- `.planning/phases/72-76` — all WARNING-phase precedents
- `quirk/util/weak_crypto.py` (Phase 73) — possible home for D-05 dedup
- `quirk/assessment/migration_advisor.py` (Phase 74) — `_matches` helper for D-03
- `quirk/__init__.py` — D-07 PLATFORM_VERSION home
- All cited per-IN sites

</canonical_refs>

<code_context>
## Reusable Assets / Patterns

- **Phase 73 `quirk/util/weak_crypto.py::is_weak_cipher`** — possible reuse for D-03 SHA1 detection and D-05 dedup target
- **Phase 74 `quirk/assessment/migration_advisor.py::_matches`** — word-boundary regex helper, alternative reuse target for D-03
- **Phase 59 `quirk/util/safe_exc.py::safe_str`** — D-08 exception logging
- **Phase 71 `_MAX_HOSTS_PER_CIDR=1024`** — D-22 sees this as the upper-bound pattern; consult before deciding O(1) vs cap
- **Phase 75 D-06 multiplier range `[0.8, 1.5]`** — D-19 extracts the same constants from magic numbers
- **`useMemo` React idiom** (existing in `src/dashboard/src/`) — D-25 follows
- **`ipaddress.ip_address(...)` IPv4 detection** — D-06 follows

</code_context>

<test_strategy>
## Test Approach

- **Plans organized by subsystem** (4 plans):
  - `77-01` — INFO-01 (protocol scanner): D-01..D-06
  - `77-02` — INFO-02 (CBOM/intelligence): D-07..D-15
  - `77-03` — INFO-03 (API/CLI): D-16..D-22
  - `77-04` — INFO-04 (React frontend): D-23..D-29
- **Plan 77-05** — LEDGER-01 closure: D-30, D-31 + the audit-row flips for all 29 INFO rows (consolidates the row flips across all 4 INFO plans). Depends on PLANs 01-04 completing.
- Each fix gets ≥1 RED-then-GREEN test where behavior changed. Comment-only fixes (D-01, D-23) get an assertion that the comment exists.
- **D-31 CI gate** — `tests/test_audit_ledger_zero_open.py` runs in regular pytest collection.
- **Build verification**: PLAN 77-04 includes `cd src/dashboard && npm run build` exit 0.
- **No new UAT-NN-NN cases** — these are internal polish. The PHASE-77 wrap note in UAT-SERIES.md documents the zero-bare-open milestone closure.

</test_strategy>

<deferred>
## Deferred Ideas (post v4.9)

- **`importlib.metadata` runtime version source** (alternative to D-07) — defer to v5.0 if startup cost becomes acceptable.
- **IntelligenceReport revival** (alternative to D-15 delete) — capture in v5.0 if a typed intelligence pipeline is needed.
- **TypedDict for all QRAMM endpoints** (D-16 broader scope) — Phase 77 narrows to worst offenders; full TypedDict migration is v5.0+.
- **Trend analysis streaming pagination** (D-09 broader) — current fix is yield_per chunking; full server-side pagination is v5.0.

</deferred>
