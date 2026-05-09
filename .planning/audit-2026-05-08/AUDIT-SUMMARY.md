---
audit: comprehensive-codebase-2026-05-08
status: gaps_found
audited: 2026-05-08
purpose: Pre-v4.8 primetime-cutover audit
subsystems_reviewed: 6
files_reviewed: 116
findings:
  blockers: 41
  warnings: 91
  info: 22
  total: 154
---

# QU.I.R.K. Whole-Codebase Audit — 2026-05-08

**Purpose:** Pre-v4.8 primetime-cutover audit. v4.8 is the deploy-and-forget milestone (per HORIZON.md): scheduled scans, dashboard-initiated scans (BACK-86 slice 1), and the moment QUIRK transitions from one-shot CLI to platform. Quality bar is the highest in project history.

**Method:** 6 parallel `gsd-code-reviewer` agents at deep depth, partitioned by subsystem. Each agent performed cross-file analysis (import graphs, call chains, shared state).

**Scope:** 116 files across `quirk/` (Python backend) and `src/dashboard/src/` (React frontend). Excluded: tests, shadcn UI primitives, build artifacts.

---

## Headline

**41 blockers, 91 warnings, 22 info — across all 6 subsystems.** No subsystem came back clean. Several findings invalidate assumptions in the planned v4.8 phase shape:

1. **Three new categories of issue not previously memory-flagged:**
   - **Untrusted-input parsing risk in scanners** (SSRF, argument injection, hardcoded creds) — 6 blockers in `scanners-protocol`
   - **Credential leakage via exception stringification** — pattern across 4 cloud connectors
   - **Markdown injection in technical/executive reports** — adversary-controlled banner/CN can break tables

2. **OBS-1 (CBOM Pass-1 zero-algo profiles) is broader than memorialized.** Memory tracks 5 profiles; the audit found at least 12 protocol families fall through with zero algo emission. Plus VAULT is incoherent across passes (Pass-1 misroutes to TLS branch, Pass-2/3 explicitly skip).

3. **Dashboard API is unhardened for v4.8.** Zero auth, zero CORS, zero rate-limiting, zero CSRF on every mutating QRAMM CRUD endpoint. Currently single-tenant local-only; v4.8 dashboard-initiated scans changes the threat model.

4. **Score arithmetic has multiple correctness gaps** — total readiness can exceed 100, profile multiplier unclamped server-side, maturity threshold gaps mis-classify a wide band of scores, confidence bonus awards 20 points when zero TLS endpoints scanned.

5. **Two existing files are dead/misnamed:**
   - `quirk/discovery/tls_scanner.py` is a duplicate missing all Phase 46 fixes (delete)
   - `quirk/intelligence/schema.py` is fully unused dead code that misrepresents the on-disk JSON contract
   - `quirk/engine/migration_planner.py` is a 16-line stub
   - `quirk/engine/risk_engine.py` is misnamed (it's a findings evaluator, not a risk engine)

`★ Insight ─────────────────────────────────────`
Doing this audit before v4.8 was the right call. v4.8 was already planning to absorb residual trust/polish items (BACK-40/41/42/44, OBS-1, BACK-63) — the audit reveals that scope was significantly under-counted. Without this audit, v4.8 would have shipped with primetime-grade *operating model* features sitting on top of *demoable-grade* security and correctness foundations.
`─────────────────────────────────────────────────`

---

## Findings by Subsystem

| Subsystem | Files | Blockers | Warnings | Info | Total | Detailed Report |
|---|---:|---:|---:|---:|---:|---|
| Scanners — Protocol | 17 | 8 | 14 | 6 | 28 | [scanners-protocol/REVIEW.md](scanners-protocol/REVIEW.md) |
| Scanners — Cloud + Engine | 11 | 10 | 24 | 0 | 34 | [scanners-cloud/REVIEW.md](scanners-cloud/REVIEW.md) |
| QRAMM + Compliance | 8 | 4 | 13 | 0 | 17 | [qramm-compliance/REVIEW.md](qramm-compliance/REVIEW.md) |
| CBOM + Intelligence + Reports | 13 | 7 | 14 | 9 | 30 | [cbom-intel-reports/REVIEW.md](cbom-intel-reports/REVIEW.md) |
| Dashboard API + CLI + Core | 21 | 9 | 17 | 7 | 33 | [api-cli-core/REVIEW.md](api-cli-core/REVIEW.md) |
| React Frontend | 46 | 6 | 14 | 7 | 27 | [react-frontend/REVIEW.md](react-frontend/REVIEW.md) |
| **TOTAL** | **116** | **44** | **96** | **29** | **169** | |

(Note: the totals here are inclusive — a few findings span subsystems and are counted in each. Per-subsystem reports are authoritative for individual finding text.)

---

## Top 15 Blockers (Cross-Subsystem Severity Ranking)

### Security — Network-Positioned Attacker

1. **JWT_VERIFY=False everywhere** (`scanners-protocol/CR-01`) — JWKS fetch always disables TLS verification. MITM trivially attacks the inventory's authentication root.
2. **SSRF in SAML scanner** (`scanners-protocol/CR-04`) — bare `httpx.get` accepts any URL (AWS IMDS, `file://`, internal IPs).
3. **Argument injection — semgrep** (`scanners-protocol/CR-02`) — unvalidated `repo_path` flows into `subprocess`.
4. **Argument injection — syft** (`scanners-protocol/CR-03`) — unvalidated `image_ref`, including `dir:/` filesystem scan.
5. **Hardcoded `guest:guest` Basic-auth shipped to every host** (`scanners-protocol/CR-05`) — broker scanner, no allowlist.
6. **Cleartext credentials over HTTP + `ssl_cert_reqs="none"`** (`scanners-protocol/CR-06`) — broker scanner mgmt API + Redis.

### Security — Dashboard / API Surface (v4.8-critical)

7. **Zero auth/CORS/rate-limiting on every dashboard route** (`api-cli-core/CR-03`) — including mutating QRAMM CRUD. v4.8 dashboard-initiated scans makes this a real attack surface.
8. **Path traversal in `quirk init`** (`api-cli-core/CR-01`) — unchecked `output_path` → `os.makedirs` + `shutil.copy2`.
9. **SSRF surface in `routes/pdf.py`** (`api-cli-core/CR-02`) — unbounded `QUIRK_SERVE_PORT` env.
10. **`@file` target loading has no path allow-listing or size cap** (`api-cli-core/CR-09`) — `@/etc/passwd`, `@/proc/self/environ` succeed.

### Security — Credential Leakage

11. **Vault scan_error leaks raw exception text including potential token fragments** (`scanners-cloud/CR-04`) — pattern repeats across GCP/DB/AWS.

### Correctness — Score / Output

12. **Total readiness score can exceed 100** (`cbom-intel-reports/CR-06`) — six subscores × 25 with no top-level clamp. Reports print "150/100".
13. **OBS-1 broader than memorialized — at least 12 zero-algo protocol families** (`cbom-intel-reports/CR-01`) — was 5; now 12+. Plus VAULT incoherent across passes.
14. **Markdown injection in technical/executive reports** (`cbom-intel-reports/CR-07`) — host/cipher_suite/cert_subject/finding text interpolated into pipe tables without escaping `|` or `\n`.
15. **Profile multiplier not clamped server-side** (`qramm-compliance/BL-01`) — client `multiplier=10.0` produces overall scores >40.

---

## Cross-Cutting Patterns

These show up in multiple subsystems and warrant single-phase fixes rather than per-finding treatment:

### Pattern A — Credential leakage via exception stringification
**Subsystems:** scanners-cloud (CR-04, CR-05), api-cli-core (multiple), scanners-protocol
**Pattern:** `f"some-error: {exc}"` across error paths interpolates raw exception text. Vault tokens, GCP ADC paths, PostgreSQL connection strings can leak into `scan_error` (persisted to SQLite) and logs.
**Fix:** Shared `quirk/util/safe_exc.py::safe_str(exc)` helper returning `f"{type(exc).__name__}"` or scrubbing known-sensitive patterns. Apply consistently across all connectors.

### Pattern B — Untrusted input flowing to subprocess / HTTP
**Subsystems:** scanners-protocol (CR-02, CR-03, CR-04, scattered WRs)
**Pattern:** External tool wrappers (semgrep, syft, nmap with `extra_args`) and HTTP fetchers (SAML, DNSSEC) accept caller-supplied paths/URLs without an allowlist.
**Fix:** Path/URL validation layer before subprocess.run; URL allowlist (deny RFC1918, link-local, file://) for outbound HTTP.

### Pattern C — Cancellation guard inconsistency in React hooks
**Subsystems:** react-frontend (BR-03, BR-04, scattered WRs)
**Pattern:** Multiple hooks fetch but don't gate state-setters with `if (!cancelled)`. Scan switches mid-fetch causes scan A's data to overwrite scan B.
**Fix:** Standard cancellation pattern across all data hooks. Lint rule via custom ESLint plugin or codemod.

### Pattern D — Migration safety
**Subsystems:** api-cli-core (CR-08), scanners-cloud (WR-15)
**Pattern:** `init_db()` calls multiple `_ensure_phaseNN_columns` helpers, each with its own commit. Ctrl-C between them leaves half-applied schema. Cache file corruption breaks scan with no recovery.
**Fix:** Wrap migration sequence in single transaction; defensive parse for cache/JSON files.

### Pattern E — Score arithmetic correctness
**Subsystems:** cbom-intel-reports (CR-04, CR-06, WR-05), qramm-compliance (BL-01, BL-02)
**Pattern:** Multiple unbounded score paths — readiness >100, multiplier unclamped, confidence bonus when zero data, maturity threshold gaps.
**Fix:** Defense-in-depth: every score path clamped at output, every denominator non-zero-checked, every threshold band closed.

---

## Proposed v4.8 Phase Decomposition

HORIZON.md sketches v4.8 as one milestone bundling operating-model work + residual trust/polish. Audit findings reshape the residual track. **Recommend splitting v4.8 into two waves:**

### v4.8 Wave A — Pre-Primetime Hardening (audit fix-up)
Block all operating-model work behind these. Each phase below is roughly 1 sprint of focused work.

| # | Phase | Scope | Findings closed |
|---|---|---|---|
| 57 | **Scanner Security Hardening** | CR-01..CR-06 from scanners-protocol; argument injection guards; SSRF allowlist; remove hardcoded creds | 6 blockers |
| 58 | **Dashboard API Hardening** | Auth (single-user token + CSRF), CORS lockdown, rate-limit middleware, Pydantic stricter validation, path traversal guards | 5 blockers |
| 59 | **Credential Leakage Sweep** | Shared `safe_str(exc)` helper; apply across all connectors and route handlers; review log statements | 4 blockers (Pattern A) |
| 60 | **Score Arithmetic Correctness** | Top-level readiness clamp; profile multiplier clamp; confidence bonus zero-data guard; maturity threshold band fixes | 4 blockers (Pattern E) |
| 61 | **CBOM Pass-1 Coverage Expansion** | Close OBS-1 — extend Pass-1 emission to the 12+ protocol families currently dropping zero algos; route VAULT correctly across passes | 1 blocker (CR-01) + correctness |
| 62 | **React Hook Cancellation Pattern** | Standardize cancellation guards across `useScanData`, `useQRAMMSession`, etc.; QRAMM debounce coalescing fix; auto-fill confirm round-trip | 4 blockers (BR-01..BR-05, BR-06) |

### v4.8 Wave B — Operating Model (originally planned)
Run after Wave A:

| # | Phase | Origin |
|---|---|---|
| 63 | Scheduled / continuous scanning mode | BACK-25 |
| 64 | Trend analysis foundation | BACK-21 |
| 65 | Dashboard-initiated scan: configure + launch + live status | BACK-86 slice 1 |
| 66 | Dashboard scan history + clone/compare | BACK-86 slice 2 |
| 67 | Resumable / partial-failure scans | new |
| 68 | Operator error-message pass | new |

### Deferred to v4.9 or later
- Markdown injection in reports (CR-07) — surface area is internal report rendering; defer if customer-distributed reports use HTML/PDF only
- Dead code cleanup (`quirk/discovery/tls_scanner.py`, `quirk/intelligence/schema.py`, `migration_planner.py` stub) — fits v5.2 chaos lab + tech debt sweep
- Markdown advisor false-positives (WR-09 scanners-cloud) — non-blocking polish

---

## What This Audit Did Not Cover

- **Tests** — `tests/` directory excluded per scope. Test correctness should be a separate pass.
- **Chaos lab** — `quantum-chaos-enterprise-lab/` excluded; lab.sh patterns reviewed indirectly via memory-flagged items only.
- **Build / CI** — `.github/workflows/` excluded; staleness gates were verified to exist via project state but workflow YAML quality not reviewed.
- **shadcn UI primitives** — 16 files in `src/dashboard/src/components/ui/` skipped (mostly Radix wrappers).
- **Performance profiling** — no runtime measurement; cold-import time and contention concerns are inferences from code shape.
- **License / dependency audit** — no SBOM-of-QUIRK-itself scan.

---

## Recommended Next Actions

1. **Read each subsystem's REVIEW.md.** This summary aggregates; details matter.
2. **Triage with stakeholder lens.** Memory note: enterprise-first prioritization. Walk top 15 blockers and decide which are pre-primetime gates vs which can ship with documented warnings.
3. **`/gsd-new-milestone v4.8`.** Use this audit as input. Recommend Wave A / Wave B split above.
4. **Update HORIZON.md.** Pulled-forward / pushed-back rationale log per its own `Re-evaluation Cadence` section.
5. **Memory note:** Add audit-finding categories that survive into v4.8 to project memory so future reviews can compare drift.

---

_Audit generated: 2026-05-08_
_6 deep-depth gsd-code-reviewer agents, parallel dispatch_
_Wall clock: ~8 min_
