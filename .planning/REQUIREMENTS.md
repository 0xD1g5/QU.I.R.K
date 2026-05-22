# QU.I.R.K. — v5.0 Requirements

**Milestone:** v5.0 — Stabilization + Tech Debt Sweep
**Opened:** 2026-05-22
**Status:** active

> Stabilization milestone. Zero new Python packages (`defusedxml` is *removed*, not replaced), no score-engine redesign, no new scanner surface. Closes known gaps: dependency hygiene, scoring residuals deferred from v4.10.1, chaos-lab coverage, and the OQS-nginx PQC-hybrid scoring-ceiling anchor. Numbering continues at Phase 87; HORIZON guardrail ≤6 phases. Research: `.planning/research/SUMMARY.md`.

---

## Milestone v5.0 Requirements

### Dependency Hygiene (DEP)

- [x] **DEP-01**: `.github/workflows/dashboard-quality.yml` bumps `actions/setup-node` `node-version` from `20` to `24`; the dashboard-quality CI job passes green on a real run. (GitHub runner default-switch 2026-06-16, hard removal 2026-09-16 — `release-container.yml` has no Node step.) ✅ Node 24 verified green through Setup Node + Install + **Build + Lint** on PR #4 run 26297453788; downstream a11y/axe gate (pre-existing baseline drift, node-independent) deferred to `BACK-A11Y-01`.
- [x] **DEP-02**: `defusedxml` removed from `pyproject.toml`. A shared `quirk/util/xml_safe.py` exposes a hardened lxml parser ~~constant~~ **factory** (`make_safe_parser()`, per decision D-04 — lxml parsers are not thread-safe) with `resolve_entities=False`, `no_network=True`, `load_dtd=False`, `dtd_validation=False`, `huge_tree=False`; `nmap_parser.py` and `saml_scanner.py` both use it (saml_scanner's defusedxml fallback branch removed). A billion-laughs / XXE pytest asserts the payload is neither expanded nor fetched — per lxml 6 (D-07) the assertion is `root.text is None` (entity dropped), the correct encoding of the same guarantee.

### Scoring Residuals (SCORE)

- [x] **EVIDENCE-TALLY-01**: Resolved **correct-by-design / won't-fix** at the subscore level — subscores are orthogonal per-category (`25 + category-local penalties`); `tests/test_scoring_orthogonal_contract.py` forward-locks the 6-family contract. `quirk/intelligence/scoring.py` math unchanged (D-01). Overall critical-cap deferred (separate model change).
- [x] **RENDER-CLI-01**: **Verified-no-bug** at the data layer (`tests/test_score_render_parity.py`) — CLI markdown matches the canonical engine, anchored to the 0–100 contract. Single engine confirmed (assessment engine deleted); no divergence → no fix (D-04).
- [x] **RENDER-PDF-01**: Same parity gate covers HTML/PDF (`html_renderer.py` passes `subscores` to the template). Live visual render deferred to human-UAT (UAT-88-01..03).
- [x] **SCORE-CBOM-01**: All five profiles satisfied — ssh-weak + source emit real algorithm components (D-05); database/registry/storage-s3 emit affirmative hardcoded `quirk:coverage-note` Properties (D-06). Closes Phase 42 OBS-1. No new scanning.
- [x] **SCORE-XPARENCY-01**: Reports show six subscores as `Label: N/25` + the `sum → ÷1.5 → overall` rollup across writer.py, executive.py, report.html.j2 (`tests/test_score_transparency.py`). Closes BACK-63.

### Chaos Lab Coverage (LAB)

- [x] **LAB-01**: `postgres-tls` chaos-lab profile (sslyze `--starttls postgres`); `docker-compose.yml`, `lab.sh` (auto-derived profiles), README, and `expected_results_*.md` oracle all updated in the same change (CLAUDE.md rule). Closed-lab-01 (89-01): weak `ssl_ciphers=AES128-SHA:AES256-SHA`, TLS 1.2 only.
- [x] **LAB-02**: `redis-tls` standalone profile (direct-socket TLS); same lab-sync obligations satisfied. Closed-lab-02 (89-01): weak `tls-ciphers "DES-CBC3-SHA:AES128-SHA:AES256-SHA"`, TLS 1.2 only.
- [x] **LAB-03**: `smtp-starttls` — closed as already-covered by the `email` profile (D-01). Port 30587 (Postfix submission) exposes SMTP STARTTLS; scanner emits `protocol=SMTP-STARTTLS, service_detail=SMTP-STARTTLS:587` (HIGH, EMAIL-09). No standalone smtp-starttls service added. Coverage note added to `expected_results_v4.md` under `## Profile: email`. Requirement: closed-covered-by-email-profile (D-01).
- [x] **LAB-04**: `kafka-tls` profile (`apache/kafka:3.9.0`, PEM keystore, TLS listener 39093 with plaintext 39092 healthcheck); same lab-sync obligations satisfied. Closed-lab-04 (89-01): weak `ssl.cipher.suites=TLS_RSA_WITH_AES_128/256_CBC_SHA`, separate-file PEM keystore (RESEARCH Pitfall 2 avoided), TLS 1.2.
- [x] **LAB-05**: `grpc-tls` profile — custom minimal Go gRPC server (ALPN h2, port 39443). D-03 empirical gate PASSED: sslyze `ServerScanStatusEnum.COMPLETED`, cert CN=grpc-tls.chaos.local RSA-2048, ECDHE-RSA TLS 1.2+1.3 suites detected. Four-file lab-sync complete (docker-compose.yml + lab.sh auto-derive + README + expected_results_v4.md). Requirement: closed-lab-05.
- [x] **LAB-06**: Identity-lab evidence verified end-to-end (BACK-78) — Kerberos/SAML/DNSSEC connectors enabled in `config.yaml` with live lab targets + DNSSEC resolver override (127.0.0.1:15353). Closed-lab-06 (89-02): live scan confirmed `dnssec_weak_algo_count=2` and `saml_weak_signing_count=2` flow non-zero into the identity subscore (`identity_trust=22`). The end-to-end run surfaced + fixed a latent crash (custom Logger lacked stdlib printf/`.warning` API → all three connectors threw inside `_wrapped_phase`, silently zeroing counters; fixed in `quirk/logging_util.py`, commit 5d22d98). **Deferred (human-verify):** `identity_weak_etype_count` (kerberos) needs the `identity` extra/impacket + a live KDC (macOS port-88 caveat) — tracked in HUMAN-UAT, wiring confirmed correct.

### Post-Quantum Scoring Ceiling (PQC)

- [x] **PQC-01**: `oqs-nginx` chaos-lab profile using `openquantumsafe/nginx` **pinned by image digest** (not `:latest` — group names rename across oqs-provider releases), serving an X25519MLKEM768 hybrid endpoint; same lab-sync obligations.
- [x] **PQC-02**: The scanner observes and classifies the PQC-hybrid endpoint. Detection strategy (raw `ssl.SSLContext`/`curl --curves` probe vs. an ADVISORY finding documenting that full detection needs an OQS-compiled sslyze) is resolved at `/gsd-discuss-phase 90` after the image digest is pinned and sslyze's actual output is observed. Outcome: either a genuine `quantum-safe` CBOM component or a clearly-scoped advisory.
- [x] **PQC-03**: The readiness model reflects PQC-hybrid as the scoring ceiling — a new `pqc_hybrid_endpoint_count` evidence counter and an `agility` bonus in `SCORE_WEIGHTS`, with `tests/test_score_weights_invariant.py` updated. Sequenced AFTER the SCORE phase so the invariant-sum changes don't collide.

### Code Cleanup & Bookkeeping (CLEAN)

- [x] **CLEAN-01**: Tier-A dead-code removal (file-/comment-/syntax-level, no call-graph risk): BACK-53 legacy sqlite remnants, BACK-55 stale comments, BACK-56 `datetime.utcnow` deprecation. CI guards against regression where applicable.
- [x] **CLEAN-02**: Tier-B dead-code removal (function/module deletions): BACK-49/50/51/52/54, each validated by `vulture`/AST call-graph analysis (NOT grep — dynamic imports, `__init__` re-exports, and optional-extra paths can hide reachability) plus a clean-venv smoke test after each deletion batch. ✅ _extract_cert_key_type + RichText deleted (BACK-50); BACK-52 schema portion superseded-by-D-15 (IntelligenceReport preserved per Phase 77 D-15 CI gate); D-02b vulture catalogue at docs/dead-code-candidates.md.
- [x] **CLEAN-03**: BACK-62 — Nyquist `VALIDATION.md` bookkeeping updates brought current.
- [x] **CLEAN-04**: BACK-58 — JWT `verify=False` documented as an intentional inspection-mode advisory.

### Release (REL)

- [ ] **REL-01**: Version bumped to `5.0.0` (SoT `pyproject.toml`); towncrier release notes built; `docs/UAT-SERIES.md` updated and synced to Obsidian; Obsidian phase/roadmap notes synced; `v5.0.0` tag created.

---

## Future Requirements (deferred to v5.1+)

- **OQS-compiled sslyze** — full native PQC-hybrid group detection (if PQC-02 ships as an advisory rather than a real probe). Requires a custom nassl/sslyze build with the OQS provider.
- Whichever HORIZON candidate is *not* v5.0: Candidate A (Authenticated Scanning + API depth) or Candidate B (Adoption & Integration — SIEM/ticketing/notification export) leads the v5.1 sketch.

---

## Out of Scope (this milestone)

| Item | Reason |
|------|--------|
| New capability surface (auth scanning, SIEM export, multi-tenancy) | v5.0 is a deliberate stabilization "breathe" cycle; capability work is v5.1+. |
| Score-engine redesign (subscores as 0–100, weighted average) | The v4.10.1 surgical model holds; PQC-03 adds one bonus weight, not a redesign. |
| Net-new Python packages | Stabilization principle — `defusedxml` is removed with nothing added; new chaos profiles reuse/standard images only. |
| Full native PQC-hybrid detection via OQS-compiled sslyze | Deferred to v5.1 if PQC-02 ships as advisory; out of scope for a stabilization milestone's effort budget. |

---

## Traceability

| Requirement | Phase | Plan | Status |
|-------------|-------|------|--------|
| DEP-01 | 87 | 87-01 | ✅ done (989be0c, 326b247; PR #4) |
| DEP-02 | 87 | 87-02 | ✅ done (eda16ff, d89a4c2, 2e85981) |
| EVIDENCE-TALLY-01 | 88 | 88-01 | ✅ done — won't-fix/orthogonal lock (3a13c8d, 7c23c55) |
| RENDER-CLI-01 | 88 | 88-01 | ✅ done — verified-no-bug, parity gate (3a13c8d) |
| RENDER-PDF-01 | 88 | 88-01 | ✅ done — parity gate; visual → UAT-88 |
| SCORE-CBOM-01 | 88 | 88-02 | ✅ done (3f0ec45, eb304fc) — OBS-1 closed |
| SCORE-XPARENCY-01 | 88 | 88-01 | ✅ done — 3-surface decomposition (7c23c55) |
| LAB-01 | 89 | 89-01 | ✅ done — postgres-tls weak-TLS profile |
| LAB-02 | 89 | 89-01 | ✅ done — redis-tls standalone weak-TLS profile |
| LAB-03 | 89 | 89-03 | ✅ done — closed-covered-by-email-profile (D-01) |
| LAB-04 | 89 | 89-01 | ✅ done — kafka-tls weak-TLS profile (PEM keystore) |
| LAB-05 | 89 | 89-03 | ✅ done — grpc-tls lab profile + D-03 ALPN gate PASSED |
| LAB-06 | 89 | 89-02 | ✅ done — identity evidence live-verified (dnssec=2, saml=2); kerberos etype deferred (HUMAN-UAT) |
| PQC-01 | 90 | 90-01 | ✅ done (6491f35, e5c61da) — oqs-nginx profile + four-file lab-sync |
| PQC-02 | 90 | 90-02 | ✅ done (7b1c0be, 1403254) — PQC probe + classifier alias + evidence counter |
| PQC-03 | 90 | 90-03 | ✅ done (00e24f5, 41e172d) — agility_pqc_hybrid_bonus weight + invariant 283.0/37 |
| CLEAN-01 | 91 | 91-01 | ✅ done (67786fe) — datetime.utcnow() fixed in tests; v3.x/v4.x comments swept |
| CLEAN-02 | 91 | 91-02 | ✅ done (d027474, 6fd5f98) — _extract_cert_key_type + RichText deleted (BACK-50); BACK-52 schema portion superseded-by-D-15 (option-a: IntelligenceReport preserved per Phase 77 D-15 CI gate); D-02b vulture catalogue at docs/dead-code-candidates.md |
| CLEAN-03 | 91 | 91-01 | ✅ done (7ea806a, 89e8063) — conftest DB isolation; VALIDATION.md frontmatter updated; CONCERNS.md stale entries annotated |
| CLEAN-04 | 91 | 91-01 | ✅ done (89e8063) — JWT allow_insecure_jwks documented in operators-guide.md + configuration.md |
| REL-01 | 92 | TBD | pending |

**Coverage:** 21 requirements across 6 phases (87–92). Final phase/plan mapping set by the roadmapper.
