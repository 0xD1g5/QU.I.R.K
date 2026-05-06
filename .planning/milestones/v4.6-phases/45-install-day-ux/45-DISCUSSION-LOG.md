# Phase 45: Install-Day UX - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-03
**Phase:** 45-install-day-ux
**Areas discussed:** [all] composition, Advisory finding shape, Where advisory is emitted, ImportError pattern reuse

---

## [all] composition

| Option | Description | Selected |
|--------|-------------|----------|
| Scanners only (Recommended) | [all] = cloud + db + motion + redis. No Playwright download. Dashboard stays opt-in. | |
| Everything except impacket | [all] = cloud + db + motion + redis + dashboard. One-stop install. Pulls Playwright binaries. impacket excluded due to pyOpenSSL conflict. | ✓ |
| Two meta-extras | [all] = scanners only; [full] = scanners + dashboard. More docs surface. | |

**User's choice:** Everything except impacket
**Notes:** User explicitly chose one-stop-install ergonomics over install size. Plan must document the Playwright binary cost in user-facing install docs.

---

## Advisory finding shape

### Question 1 — finding shape

| Option | Description | Selected |
|--------|-------------|----------|
| INFO + distinct category (Recommended) | Severity INFO, category="coverage_gap". One finding per skipped scanner. Persisted to DB. Renders in a dedicated "Coverage Gaps" section. | ✓ |
| LOW + same finding stream | Severity LOW, mixed with normal findings. Pollutes finding count and may skew readiness score. | |
| INFO + aggregated single finding | One INFO finding listing all skipped scanners. Lighter but harder to track over time. | |

### Question 2 — score impact

| Option | Description | Selected |
|--------|-------------|----------|
| No — zero score impact (Recommended) | Advisory findings are coverage signals, not security issues. Excluded from severity weighting and readiness calculation. | ✓ |
| Yes — small confidence penalty | Reduces confidence subscore (not severity-weighted score). Honest but more complex. | |

**User's choice:** INFO + distinct category; zero score impact
**Notes:** Confidence-subscore penalty captured as deferred idea — revisit if consultants report misleading confidence on scans with missing extras.

---

## Where advisory is emitted

| Option | Description | Selected |
|--------|-------------|----------|
| Centralized pre-scan probe (Recommended) | Single registry. Probe runs at scan start. Single source of truth. Pairs with Area 4 helper. | ✓ |
| Decentralized at scanner skip-time | Each scanner self-emits when AVAILABLE flag is False. 6+ duplicated emission sites; config-disabled scanners stay silent. | |
| Hybrid: central registry, scanner-emitted | Registry holds metadata; scanners call shared helper. Middle-ground complexity. | |

**User's choice:** Centralized pre-scan probe
**Notes:** Probe consults config `enable_*` flags so config-disabled scanners do NOT generate noise. Only scanners that are enabled-but-unavailable produce a finding.

---

## ImportError pattern reuse

| Option | Description | Selected |
|--------|-------------|----------|
| New helper, no migration (Recommended) | Add quirk/util/optional_extra.py with registry. Existing scanners keep their per-file try/except + *_AVAILABLE flags. Tests untouched. | ✓ |
| New helper + migrate all scanners | Helper as above, AND replace each scanner's try/except. Cleanest end state but touches 6+ scanner files and test suites. Risk of breaking patch points. | |
| Inline the registry, no helper module | Registry lives directly in probe code. No new util module. Smallest diff but registry isn't reusable. | |

**User's choice:** New helper, no migration
**Notes:** Decision driven by test-fragility concern — broker_scanner tests patch SSLYZE_AVAILABLE and SslyzeScanner module-level names. Migration deferred to a dedicated cleanup phase after v4.6.

---

## Claude's Discretion

- Exact field name for the new finding category on FindingItem (`category` / `kind` / `finding_type`) — researcher matches existing schema naming
- Exact wording of per-scanner install-hint strings — must contain `pip install quirk[<extra>]` literal
- Whether the report renderer's "Coverage Gaps" section is a new template block or a filter on existing rendering
- Where in the scan lifecycle the centralized probe is invoked (likely the scan orchestrator)

## Deferred Ideas

- Unify scanner optional-import patterns onto the new helper (post-v4.6 cleanup phase)
- Confidence-subscore penalty for coverage gaps (revisit if scans-with-missing-extras feel misleadingly confident)
- Aggregated/compact rendering mode for advisories in noisy enterprise scans
- `quirk doctor` / dependency-status CLI subcommand to surface missing extras before a scan
