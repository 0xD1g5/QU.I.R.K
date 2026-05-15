# Phase 73: CBOM + Intelligence + Reports WARNINGs - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Close all 13 open WARNING-severity audit findings in the CBOM/intelligence/reports subsystem from the 2026-05-08 audit ledger (`cbom-intel-reports/WR-01..WR-14`; WR-05 already closed by Phase 60 SCORE-04). Internal-contract changes and documentation only — no new scan capabilities, no schema changes, no new pip dependencies, **zero customer-facing score regression**.

**In scope (mapped to INTEL-NN requirements):**

- **INTEL-01** — PDF render hardening: blanket `except Exception` narrowed by exception type, Playwright resources released in `finally`, user-visible warning on PDF failure (closes WR-01, WR-02, WR-14)
- **INTEL-02** — Weak-crypto predicate unification: `motion_broker_weak_tls_count` uppercase consistency, ECDSA detection alignment to `cert_pubkey_alg` conventions (EC ↔ ECDSA), SAML weak-detection robust against mixed-case SHA-1, email/broker weak-cipher predicates unified via new `quirk/util/weak_crypto.py::is_weak_cipher` helper (closes WR-03, WR-04, WR-10, WR-11)
- **INTEL-03** — Score weights + roadmap + executive + cipher labels + confidence: SCORE_WEIGHTS documented and CI-gated for invariant (NOT normalized), roadmap double-period artifact removed, executive `_build_interpretation` guards `score['score']` access, TLS 1.2 non-PFS RSA returns `RSA-kex` label correctly, confidence weight overrides pass through clamp+validation, roadmap mutation-after-yield merge rule documented (closes WR-06, WR-07, WR-08, WR-09, WR-12, WR-13)

**Out of scope (deferred to other phases or explicitly do-not-touch):**

- QRAMM + compliance WARNINGs (Phase 74)
- API/CLI core WARNINGs (Phase 75)
- React frontend WARNINGs (Phase 76)
- All BLOCKER-severity rows (already closed in Phase 60 / 61 / 64.1)
- `cbom-intel-reports/WR-05` (`_apply_weighted_impacts` score_cap) — already closed by Phase 60
- Any score normalization that changes SCORE_WEIGHTS sum away from 261 — explicit non-goal per D-06
- Any code path not explicitly named in WR-01..WR-14 (see D-14 do-not-touch list)

</domain>

<decisions>
## Implementation Decisions

### PDF render exception types + finally cleanup (INTEL-01 / WR-01, WR-02, WR-14)

- **D-01 (locked):** `quirk/reports/writer.py` PDF render path replaces the blanket `except Exception:` with `except (PlaywrightError, asyncio.TimeoutError, TimeoutError, OSError, RuntimeError) as e:` and wraps the browser/context lifecycle in a `try/finally`. `finally` block calls `await context.close()` and `await browser.close()` defensively (each wrapped in its own try/except to avoid mask-on-failure). On exception: print `f"PDF generation failed: {safe_str(e)}; scan complete, HTML report at {html_path}"` to stderr via the project's stderr advisory pattern (closes WR-14 in the same task). PlaywrightError import path: `from playwright.async_api import Error as PlaywrightError`.
- **D-01a (Claude's discretion):** If Playwright is not installed (optional `[reports]` extra), the import-guard pattern from Phase 41 / 45 still applies — the narrowed except types are unreachable in that branch, so a `ImportError` fallback path is unchanged. Researcher to verify the existing import-guard idiom.

### Weak-cipher predicate unified helper (INTEL-02 / WR-11, WR-03, WR-10)

- **D-02 (locked):** Create `quirk/util/weak_crypto.py` with:
  ```python
  WEAK_CIPHER_TOKENS: frozenset[str] = frozenset({
      "DES", "3DES", "RC4", "MD5", "NULL", "EXPORT", "ANON", "DES-CBC", "IDEA",
      # SAML SHA-1 family
      "SHA1", "SHA-1",
  })
  def is_weak_cipher(cipher_or_label: str | None) -> bool: ...
  ```
  The function uppercases the input once, then checks `any(t in upper for t in WEAK_CIPHER_TOKENS)`. Both `evidence.py::motion_email_*_weak_tls_count` and `evidence.py::motion_broker_weak_tls_count` predicates route through this helper. SAML SHA-1 detection (WR-10) also uses this helper instead of fragile equality on uppercased fragments. Module precedent: mirrors `quirk/util/safe_exc.py` shape (Phase 59).
- **D-02a (Claude's discretion):** Whether to expose `WEAK_CIPHER_TOKENS` as importable public API or only `is_weak_cipher`. Default: helper public, set private (`_WEAK_CIPHER_TOKENS`) — discourages bypass.

### ECDSA detection alignment (INTEL-02 / WR-04)

- **D-03 (locked):** `quirk/intelligence/evidence.py` ECDSA branch currently does `cert_pubkey_alg.startswith("ECDSA")` but TLS scanner emits `"EC"` (cloud KMS normalizer emits `"ECDSA"`). Unify under a tuple: `cert_pubkey_alg.upper().startswith(("EC", "ECDSA"))`. Add a unit test parametrized over both emitter conventions. Same pattern applied wherever ECDSA detection happens — researcher inventories all sites.

### SCORE_WEIGHTS invariant + documentation (INTEL-03 / WR-06)

- **D-04 (locked):** **DO NOT normalize.** SCORE_WEIGHTS are absolute per-ratio coefficients, not probabilities. Add:
  1. A module-level docstring above `SCORE_WEIGHTS` in `quirk/intelligence/scoring.py` explaining: "Absolute per-ratio coefficients (NOT probabilities). Sum is 261.0 by design. The `_apply_weighted_impacts` function shares score caps across these weights — see CR-06 Phase 60 closure for the cap-sharing rationale. Any contributor adding/removing a weight MUST update `tests/test_score_weights_invariant.py` to match the new expected sum."
  2. A new `tests/test_score_weights_invariant.py` that asserts `sum(SCORE_WEIGHTS.values()) == 261.0` with tolerance `1e-9`. CI failure on accidental rebalance.
  3. The audit row WR-06 evidence note records this as "documented invariant, NOT normalized — preserves all customer-facing scores".

### Roadmap double-period artifact (INTEL-03 / WR-07)

- **D-05 (locked):** `quirk/intelligence/roadmap.py::_why` string-format produces a trailing `..` (a period in the template + a sentence-ending period in the input). Use `textwrap.dedent` or explicit `.rstrip('.') + '.'` normalization at the join site. Researcher locates the exact line; planner picks the minimal fix.

### Roadmap mutation-after-yield documentation (INTEL-03 / WR-08)

- **D-06 (locked):** `quirk/intelligence/roadmap.py` mutates a shared dict after yielding it. This is intentional (merge accumulator pattern) but undocumented. Add a multi-line code comment immediately above the yield site explaining: (a) callers MUST consume each yielded dict before calling `next()`, (b) the mutation is the merge-rule's intended behavior, (c) cite WR-08 closure. No code change. Add a regression test that asserts the merge-after-yield produces the expected final state.

### Executive `_build_interpretation` score guard (INTEL-03 / WR-09)

- **D-07 (locked):** `quirk/reports/executive.py::_build_interpretation` accesses `score['score']` without checking key presence. Guard: `score_val = score.get('score') if isinstance(score, dict) else None; if score_val is None: return _INTERPRETATION_UNAVAILABLE` (where the constant is a module-level fallback string). Pattern mirrors Phase 70 D-07 guard discipline.

### TLS 1.2 RSA non-PFS KEX label (INTEL-03 / WR-12)

- **D-08 (locked):** `quirk/intelligence/evidence.py::_decompose_cipher_suite` (or wherever the cipher decomposer lives — researcher to confirm) currently returns the wrong KEX for RSA non-PFS suites in TLS 1.2. The correct label is `RSA-kex` (with the hyphen) to distinguish from `RSA-auth` (used elsewhere for cert signature). Fix the conditional: when `tls_version == "TLSv1.2"` AND cipher suite lacks `(EC)DHE`, return `RSA-kex` regardless of how the cipher string spells it. Add parametrized test across the 8 known non-PFS RSA TLS 1.2 cipher suites.

### confidence.py weight overrides clamp (INTEL-03 / WR-13)

- **D-09 (locked):** `quirk/intelligence/confidence.py` `apply_weight_overrides` (researcher confirms function name) passes user-supplied override values directly into the weights dict. Add validation: each value passes through `max(0.0, min(1.0, float(v)))`; non-numeric raises `ValueError(f"Confidence override {k!r} must be numeric in [0.0, 1.0], got {v!r}")`. Mirrors Phase 71 D-06 clamp-and-fail-loud pattern. Validate keys against a known-set if available; surface unknown keys as a WARNING log entry rather than a hard error (forward compat).

### motion_broker_weak_tls_count uppercase consistency (INTEL-02 / WR-03)

- **D-10 (locked):** Routed through `is_weak_cipher` per D-02. The current predicate's uppercase token list (`"TLSV1.0"`, `"TLSV1"`) matches against `cipher.upper()`; this works for current TLS output but the helper unifies behavior. Once D-02 lands, the predicate becomes `is_weak_cipher(cipher)` plus an additional TLS-version check via a sibling helper `is_legacy_tls_version(tls_version)` (still in `weak_crypto.py`).

### Phase-73 do-not-touch list

- **D-14 (locked):** Explicitly out of scope for Phase 73:
  - Any change to SCORE_WEIGHTS values themselves — only documentation + invariant test (D-04)
  - `quirk/intelligence/scoring.py::_apply_weighted_impacts` cap-sharing logic — closed by Phase 60 SCORE-04 / CR-06; do not touch
  - `quirk/cbom/builder.py` pass-1/pass-2/pass-3 logic — not under audit in this WR cluster
  - `quirk/intelligence/trends.py` — out of audit scope
  - `quirk/reports/technical.py` Markdown escaping — closed by Phase 61 REPORT-SAN-*
  - PDF rendering engine swap (chromium-headless vs WeasyPrint) — exceeds WR scope; revisit only if reports/writer.py needs structural change
  - Any modification to the `cert_pubkey_alg` field's emitter side (TLS scanner) — D-03 fixes the consumer, not the producer

</decisions>

<canonical_refs>
## Canonical References (downstream agents MUST read)

- `.planning/audit-2026-05-08/AUDIT-TASKS.md` — audit ledger; rows `cbom-intel-reports/WR-01..WR-14` (WR-05 already closed by Phase 60) are the source of truth. Rows must be flipped to `Phase 73 | [x] closed` with per-row evidence (mirrors Phase 72 pattern).
- `.planning/audit-2026-05-08/cbom-intel-reports/REVIEW.md` — detailed audit review with file:line citations.
- `.planning/REQUIREMENTS.md` — INTEL-01..INTEL-03 requirement statements.
- `.planning/ROADMAP.md` Phase 73 section — Goal + 3 Success Criteria (gating).
- `.planning/phases/72-cloud-scanner-warnings/72-CONTEXT.md` — Phase 72 precedent for the audit-row-flip pattern and do-not-touch discipline (D-14 mirrors Phase 72 D-25).
- `.planning/phases/71-protocol-scanner-warnings/71-CONTEXT.md` — Phase 71 clamp + fail-loud pattern (D-09 mirrors PROTO-01 D-06; D-09 also mirrors PROTO-03 D-04 fail-loud allowlist).
- `.planning/phases/60-score-arithmetic-correctness/` (if exists) — Phase 60 closed CR-06 / SCORE-04; D-04 references this for the cap-sharing rationale that future contributors must preserve.
- `quirk/reports/writer.py` — PDF render path (WR-01, WR-02, WR-14 sites).
- `quirk/reports/executive.py::_build_interpretation` — WR-09 site.
- `quirk/intelligence/scoring.py::SCORE_WEIGHTS` — WR-06 site.
- `quirk/intelligence/roadmap.py::_why` — WR-07 site; same module's mutation-after-yield site for WR-08.
- `quirk/intelligence/evidence.py` — WR-03, WR-04, WR-10, WR-11 sites.
- `quirk/intelligence/confidence.py` — WR-13 site.
- `quirk/intelligence/evidence.py::_decompose_cipher_suite` (or equivalent) — WR-12 site.
- `quirk/util/safe_exc.py` — Phase 59 precedent for the new `quirk/util/weak_crypto.py` module shape (D-02).
- `pyproject.toml` — confirm Playwright is in the `[reports]` extra (D-01).

</canonical_refs>

<code_context>
## Reusable Assets / Patterns (from codebase scout)

- **`quirk/util/safe_exc.py::safe_str(exc)` helper** (Phase 59 LEAK-01) — used in D-01 for the user-facing PDF failure message and in any other exception-stringification site this phase touches. AST-gate test in `tests/test_safe_exc_gate.py` already enforces routing.
- **`quirk/util/weak_crypto.py` (NEW, D-02)** — new module created in this phase; mirrors `safe_exc.py` shape (module-level constants + a small set of pure functions). Will be the canonical home for any future weak-crypto predicate consolidation.
- **Phase 60 SCORE-04 / `_apply_weighted_impacts` cap-sharing** — the rationale D-04 cites in the new SCORE_WEIGHTS docstring. Researcher to read the Phase 60 SUMMARY.md for the exact technical phrasing.
- **Stderr advisory pattern** (Phase 41 / Phase 45 install-day advisories) — D-01's user-facing PDF failure message follows the same `print(..., file=sys.stderr)` idiom used for `category=missing_extra` advisories. Researcher confirms the exact format.
- **Clamp + ValueError pattern** (Phase 71 D-06 coverage clamp; PROTO-03 D-04 nmap allowlist) — D-09 confidence-override clamp follows this shape: explicit numeric coercion, range clamp, fail-loud on non-numeric.
- **Module-level frozenset constants** (Phase 71 PROTO-03 `_SAFE_NMAP_ARG_RE`, Phase 70 `_SAFE_COL_TYPE_RE`) — D-02's `_WEAK_CIPHER_TOKENS` follows the same shape: module-private frozenset, public helper function.

</code_context>

<test_strategy>
## Test Approach (high-level — planner refines)

- **One test module per INTEL-NN requirement** (3 modules) — mirrors Phase 72/71 plan-per-requirement granularity:
  - `tests/test_pdf_render_hardening.py` — INTEL-01 (PDF except + finally + user-visible warning)
  - `tests/test_weak_crypto_helper.py` — INTEL-02 (`is_weak_cipher` parametrized table + ECDSA detection alignment + SAML SHA-1 mixed-case)
  - `tests/test_score_weights_invariant.py` + `tests/test_roadmap_double_period.py` + `tests/test_executive_score_guard.py` + `tests/test_confidence_clamp.py` + `tests/test_tls_kex_label.py` — INTEL-03 (one micro-module per WR row to keep tests bounded)
- **RED-then-GREEN per fix** — every guard / clamp / narrowing gets at least one test that proves the failing input is now handled.
- **D-02 (weak_crypto)** — parametrized test table with 30+ cipher strings (weak: DES-CBC-SHA, RC4-MD5, NULL-SHA, EXPORT40-RC2-CBC-MD5, ADH-AES128-SHA, DES-CBC3-SHA, IDEA-CBC-SHA; strong: AES128-GCM-SHA256, ECDHE-RSA-AES256-GCM-SHA384, CHACHA20-POLY1305-SHA256). Asserts both predicates (email + broker) produce identical output for identical input post-unification.
- **D-04 (SCORE_WEIGHTS invariant)** — single assertion + golden-file regression tests in the existing scoring suite to PROVE no customer-facing score changed.
- **D-08 (TLS 1.2 RSA-kex)** — parametrized table across the 8 known non-PFS RSA TLS 1.2 cipher suites: AES128-SHA, AES256-SHA, AES128-SHA256, AES256-SHA256, AES128-GCM-SHA256, AES256-GCM-SHA384, NULL-SHA, NULL-MD5.
- **Audit ledger flip** verified by docs commit asserting all 13 WR-NN rows show `Phase 73 | [x] closed` in `AUDIT-TASKS.md` (Phase 72 / 71 precedent).
- **No new UAT-NN-NN cases needed** — these are internal contracts. Follow Phase 72 wrap pattern: prepend a "Phase 73 wrap" note to `docs/UAT-SERIES.md` `Last Updated:` preamble describing the documented invariant (SCORE_WEIGHTS sum=261, NOT normalized), the new `quirk/util/weak_crypto.py` helper, and the PDF-failure stderr advisory contract.

</test_strategy>

<deferred>
## Deferred Ideas (noted, not in scope)

- **Actual SCORE_WEIGHTS normalization** — would regress all customer-facing scorecards; revisit only as part of an intentional scoring-model bump (v5.0).
- **PDF rendering engine swap (chromium → WeasyPrint)** — exceeds WR scope; capture as backlog if Playwright ever becomes a maintenance burden.
- **TLS scanner emitter unification (EC ↔ ECDSA)** — D-03 fixes the consumer side; the emitter inconsistency is a separate audit row (not in this WR cluster).
- **`is_legacy_tls_version` standalone helper** — declared inside `weak_crypto.py` for D-10; can later move to a dedicated `quirk/util/tls_versions.py` if call sites multiply.
- **Confidence override key allowlist enforcement** — D-09 surfaces unknown keys as WARNING; tightening to ValueError requires inventorying every override consumer.

</deferred>
