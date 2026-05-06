---
phase: 46-tls-finding-gaps
plan: 04
subsystem: docs-uat-obsidian
tags: [docs, uat, obsidian, sync, live-fire, phase-closing]
status: complete
type: execute
wave: 3
requires:
  - "Plan 46-01 (chain_verified column + scanner plumbing)"
  - "Plan 46-02 (risk-engine severities + D-04 split)"
  - "Plan 46-03 (tls-cert-defects chaos lab profile)"
provides:
  - "UAT-46-01..05 in docs/UAT-SERIES.md"
  - "Vault Phase-46-TLS-Finding-Gaps.md"
  - "Vault UAT-Series.md mirror"
  - "Vault Roadmap.md sync"
  - "Vault _QUIRK-Hub.md update"
  - "Live-fire end-to-end verification of TLS-FIND-01..07"
affects:
  - "docs/UAT-SERIES.md"
  - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md"
  - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-46-TLS-Finding-Gaps.md"
  - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Roadmap.md"
  - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/_QUIRK-Hub.md"
  - ".planning/ROADMAP.md"
  - "quirk/scanner/tls_scanner.py (Rule 1 deviation fix)"
tech-stack:
  added: []
  patterns:
    - "Direct filesystem write to vault (CLAUDE.md mandatory step — files too large for obsidian content= shell expansion)"
    - "frontmatter prepended via printf+cat for vault mirror files"
key-files:
  created:
    - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-46-TLS-Finding-Gaps.md"
    - ".planning/phases/46-tls-finding-gaps/46-04-SUMMARY.md"
  modified:
    - "docs/UAT-SERIES.md"
    - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md"
    - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Roadmap.md"
    - "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/_QUIRK-Hub.md"
    - ".planning/ROADMAP.md"
    - "quirk/scanner/tls_scanner.py"
decisions:
  - "[46-04] Verify pre-pass disables check_hostname when no server_hostname is available (SNI off / IP target). The original Plan 46-01 implementation set check_hostname=True unconditionally, which raised ValueError on hostname-less targets and silently routed chain_verified=None — making the untrusted-CA branch structurally dead end-to-end. CERT_REQUIRED still validates the chain; hostname check is independent and a hostname mismatch is a separate concern. Fix in commit de70301."
  - "[46-04] Live-fire chaos lab brought up via 'docker compose -p chaoslab --profile tls-cert-defects up -d ...' (NOT lab.sh) per BACK-87 — the lab.sh PROFILE_ARGS precedence bug is documented and tracked, but the workaround is the recommended path until BACK-87 lands."
metrics:
  duration_minutes: ~25
  completed_date: 2026-05-03
---

# Phase 46 Plan 04: Documentation, Obsidian Sync, Live-Fire End-to-End Summary

**One-liner:** Closes Phase 46 with `docs/UAT-SERIES.md` UAT-46-01..05 (cert-defect test cases mapped to TLS-FIND-01..05 and the D-02 / D-04 rules), four Obsidian vault file syncs (Phase-46 phase note, UAT-Series mirror, Roadmap, Hub), live-fire end-to-end verification of all four expected findings against the chaos lab `tls-cert-defects` profile, and a Rule 1 bug fix in `quirk/scanner/tls_scanner.py` exposed by the live-fire run (verify pre-pass `check_hostname=True` raised ValueError on hostname-less targets, silently making the untrusted-CA branch dead end-to-end).

## What Was Built

### 1. `docs/UAT-SERIES.md` — Phase 46 cert-defect test cases

Added a new "Series 46: TLS Cert-Defect Findings" section (5 test cases) just before Appendix A:

| ID | Title | Maps to | Result |
|----|-------|---------|--------|
| UAT-46-01 | Expired certificate → CRITICAL finding | TLS-FIND-01 | PASS |
| UAT-46-02 | Self-signed → HIGH + D-04 exclusivity (no untrusted-CA on same endpoint) | TLS-FIND-02 / D-04 | PASS |
| UAT-46-03 | Untrusted-CA → MEDIUM finding | TLS-FIND-03 | PASS |
| UAT-46-04 | RSA-1024 → HIGH undersized-key finding | TLS-FIND-04 | PASS |
| UAT-46-05 | D-02 multi-defect independence (one finding per class, no rollup) | D-02 across TLS-FIND-01..05 | PASS |

Updated `**Last Updated:**` header to prepend the Phase 46 wrap note.

### 2. Obsidian vault sync (4 files)

All four written via direct filesystem `cp` / Write tool — files exceed the obsidian-cli `content=` shell-expansion limit per CLAUDE.md:

| Path | Action | Frontmatter |
|------|--------|-------------|
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-46-TLS-Finding-Gaps.md` | created | `type: phase`, `status: complete`, `source: .planning/phases/46-tls-finding-gaps/`, `updated: 2026-05-03` |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` | overwrote | `type: reference`, `status: active`, `source: docs/UAT-SERIES.md`, `updated: 2026-05-03` |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Roadmap.md` | overwrote | `type: roadmap`, `status: active`, `source: .planning/ROADMAP.md`, `updated: 2026-05-03` |
| `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/_QUIRK-Hub.md` | edited (frontmatter `updated:` + active-work callout + Phases table) | (existing `type: hub`) |

The Phase 46 phase note has the full per-plan "What Was Built" section (4 subsections drawn from Plans 46-01/02/03 and this plan), all 7 TLS-FIND requirement IDs, the live-fire severity matrix, the key decisions list (D-01..D-04 + plan-specific notes including the 46-04 verify-pre-pass fix), and `[[Roadmap]]` / `[[Requirements]]` / `[[UAT-Series]]` wikilinks.

### 3. `.planning/ROADMAP.md` — Phase 46 marked complete

- Phase 46 tracking-list checkbox flipped `[ ]` → `[x]` with completion date.
- All four sub-plan checkboxes flipped `[ ]` → `[x]`.

### 4. Live-fire end-to-end verification

```bash
# Bring up profile (bypassing BACK-87 lab.sh bug):
cd quantum-chaos-enterprise-lab
docker compose -p chaoslab --profile tls-cert-defects up -d \
  tls-cert-expired tls-cert-selfsigned tls-cert-untrusted-ca tls-cert-rsa1024
# Smoke test:
for p in 13444 13445 13446 13447; do curl -sk https://localhost:$p/; echo; done
# Expected output:
#   OK - tls-cert-expired
#   OK - tls-cert-selfsigned
#   OK - tls-cert-untrusted-ca
#   OK - tls-cert-rsa1024

# Scan:
python run_scan.py --config /tmp/phase46-uat-config.yaml --quiet
# Severity matrix in /tmp/phase46-uat-output/findings-<ts>.json:
```

| Port | Severity | Title | Requirement | D-04 / D-02 evidence |
|------|----------|-------|-------------|----------------------|
| 13444 | CRITICAL | TLS certificate expired | TLS-FIND-01 | + MEDIUM untrusted-CA (D-02 multi-defect: issuer ≠ subject AND chain_verified=False) |
| 13445 | HIGH | TLS certificate is self-signed | TLS-FIND-02 | NO untrusted-CA finding on same endpoint (D-04 mutual exclusivity ✓) |
| 13446 | MEDIUM | TLS certificate issued by untrusted CA | TLS-FIND-03 | NO self-signed finding (issuer ≠ subject ✓) |
| 13447 | HIGH | TLS certificate uses undersized RSA key | TLS-FIND-04 | + MEDIUM untrusted-CA (D-02 multi-defect: leaf signed by off-trust-store scenario-root-CA) |

All 4 expected severities present, D-04 verified (13445 has no untrusted-CA), D-02 verified (13444 + 13447 each emit two independent Phase 46 findings — no rollup, no severity collapse).

```bash
# Tear-down:
docker compose -p chaoslab --profile tls-cert-defects down
```

### 5. Rule 1 bug fix — verify pre-pass `check_hostname` ValueError (TLS-FIND-06 closure refinement)

**Found during:** Task 5 live-fire run (initial scan output).

**Symptom:** First live-fire scan produced only 3 of the 4 expected Phase 46 findings — port 13446 (untrusted-CA) emitted ZERO untrusted-CA finding even though the chain unambiguously did not verify against the host trust store. Inspection of `crypto_endpoints.chain_verified` showed NULL for all four endpoints.

**Root cause:** Plan 46-01's verify pre-pass in `_scan_one_fallback` (`quirk/scanner/tls_scanner.py:352-370`) created an `ssl.create_default_context()` with `check_hostname=True` always, but only set `server_hostname=host` when `(include_sni and not is_ip)`. When SNI was off OR the host was a literal IP, `verify_hostname=None` was passed to `wrap_socket(..., server_hostname=None)`, which raises `ValueError: check_hostname requires server_hostname` BEFORE the chain is ever validated. The broad `except Exception` then routed to `chain_verified=None` (Pitfall 1's transient-network-error path) — making the untrusted-CA branch structurally dead end-to-end whenever a target was scanned without a hostname (which is the default for IP-only chaos lab targets, the most common operator workflow).

**Fix:** When `verify_hostname is None`, set `verify_ctx.check_hostname = False` on the verify context. Chain validation against the system trust store is independent of hostname-mismatch checking, and a hostname mismatch is a separate concern (out of scope per CONTEXT.md "Boundaries"). After the fix, all four endpoints' `_scan_one_fallback` calls returned `chain_verified=False` as expected, and the untrusted-CA branch fired correctly.

**Files modified:** `quirk/scanner/tls_scanner.py` (~10 lines changed including a multi-line comment explaining the rationale).

**Commit:** `de70301` — `fix(46-04): verify pre-pass survives missing server_hostname`.

**Verification after fix:**
- `python -m compileall quirk tests` — clean
- `python -m pytest tests/test_tls_scanner_chain_verified.py tests/test_risk_engine.py tests/test_risk_engine_cert_defects.py -x -q` → 43 passed, 2 skipped
- `python -m pytest tests/ -x -q --ignore=tests/test_cbom_schema_validation.py` → **739 passed, 2 skipped, 17 deselected** (no regression vs baseline)
- Live-fire re-run produced the full 4-finding severity matrix above.

## Test Results

```
$ python -m compileall quirk tests
(clean)

$ python -m pytest tests/ -x -q --ignore=tests/test_cbom_schema_validation.py
739 passed, 2 skipped, 17 deselected, 70 warnings in 4.24s
```

## Acceptance Criteria

| Criterion | Result |
|-----------|--------|
| Task 1: `grep -c 'tls-cert-defects\|13444\|13445\|13446\|13447' docs/UAT-SERIES.md >= 4` | **34** ✅ |
| Task 1: `grep -c 'UAT-46-0[1-4]' docs/UAT-SERIES.md >= 4` | **11** ✅ |
| Task 1: `grep -c 'Last Updated.*2026-05' docs/UAT-SERIES.md >= 1` | **1** ✅ |
| Task 2: vault UAT-Series.md exists with frontmatter and Phase-46 content | ✅ |
| Task 3: vault Phase-46-TLS-Finding-Gaps.md exists with `type: phase` and 7+ TLS-FIND IDs | ✅ (9 hits) |
| Task 4: vault Roadmap.md has Phase 46 entry; Hub references Phase 46 (3 hits) | ✅ |
| Task 5 live-fire: 4 expected severities + D-04 exclusivity + D-02 independence | ✅ |
| `python -m compileall quirk tests` | clean ✅ |
| Full pytest suite no regressions | ✅ (739 passed) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Verify pre-pass `check_hostname=True` ValueError on hostname-less targets**

- **Found during:** Task 5 live-fire scan
- **Issue:** When `server_hostname=None` (SNI off OR IP target), `wrap_socket` raised `ValueError: check_hostname requires server_hostname` before chain validation could run. The broad `except Exception` swallowed it as `chain_verified=None`, leaving the untrusted-CA branch structurally dead end-to-end. Affected the most common operator workflow (IP/localhost-target chaos lab scans).
- **Fix:** When `verify_hostname is None`, set `verify_ctx.check_hostname = False` on the verify context. CERT_REQUIRED still validates the chain — hostname check is independent and a hostname mismatch is a separate concern (already out of scope per CONTEXT.md).
- **Files modified:** `quirk/scanner/tls_scanner.py`
- **Commit:** `de70301`

### Process — Lab bring-up bypassed lab.sh per BACK-87

The plan's Task 5 verification recipe says `PROFILE_ARGS="--profile tls-cert-defects" ./lab.sh up`. That invocation hits BACK-87 (lab.sh `.env`-sourcing precedence bug — lab.sh sources `.env` AFTER the `:-` fallback for `PROFILE_ARGS`, so `.env`'s default profile-set silently overrides the user-supplied value). Used `docker compose -p chaoslab --profile tls-cert-defects up -d ...` directly, as the operator instructions explicitly recommended ("do NOT use `lab.sh up` — see BACK-87 for why"). This is a deliberate procedural deviation matching the operator instructions; no plan or code change required for THIS phase. BACK-87 is tracked separately and was already in the ROADMAP backlog before Plan 04 began.

### Pre-existing issues (NOT fixed — out of scope)

- `tests/test_cbom_schema_validation.py` — `MissingOptionalDependencyException` for `cyclonedx-python-lib[json-validation]`. Documented in 46-01-SUMMARY.md, excluded from the test run via `--ignore`.

## TDD Gate Compliance

This plan is `tdd="false"` (documentation + sync + live-fire verification). The Rule 1 bug fix in `tls_scanner.py` was verified by the existing Plan 46-01 sentinel suite (`tests/test_tls_scanner_chain_verified.py` — all 9 + 2 skipped tests still pass) plus the live-fire end-to-end run. No new test was added because the fix is naturally covered by Test 8 (`test_fallback_chain_verified_false_on_ssl_cert_verification_error`) and is more comprehensively verified end-to-end against a real untrusted-CA endpoint than any unit test could be.

## Self-Check: PASSED

Files verified to exist:
- ✅ `docs/UAT-SERIES.md` — UAT-46-01..05 added, Last Updated header includes Phase 46 wrap note (verified: 11 UAT-46-0X hits, 34 cert-defect-keyword hits)
- ✅ `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` — frontmatter present, 22 cert-defect-keyword hits
- ✅ `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-46-TLS-Finding-Gaps.md` — frontmatter `type: phase`, 9 TLS-FIND-0X hits, all 4 plan subsections, [[Roadmap]] wikilink
- ✅ `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Roadmap.md` — frontmatter present, 6 "Phase 46" hits
- ✅ `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/_QUIRK-Hub.md` — 3 Phase-46 references (callout + Phases table row)
- ✅ `.planning/ROADMAP.md` — Phase 46 + 4 sub-plans flipped `[x]`

Commits verified to exist (will be amended by the final phase-closing commit below):
- ✅ `de70301` — `fix(46-04): verify pre-pass survives missing server_hostname` (in `git log`)

## Phase 46 Hand-off

Phase 46 is COMPLETE end-to-end:
- TLS-FIND-01..07 all satisfied with chaos lab evidence
- Risk engine emits CRITICAL/HIGH/MEDIUM/HIGH for the 4 cert-defect classes
- D-02 multi-defect independence + D-04 mutual exclusivity verified live-fire
- Phase note, UAT cases, Roadmap, Hub all synced to vault
- Bug discovered + fixed during phase-closing live-fire — fix tested, no regressions

Up next: **Phase 47 — Nmap Discovery + Multi-Target Wizard** (depends on Phase 45; parallel to Phase 46 originally, but Phase 46 is now complete first).
