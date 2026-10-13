---
id: 999.123
title: "Reference docs: generate the 'what' from source, shrink the prose to the 'why' and 'how'"
priority: P2
status: open (unscheduled)
created: 2026-10-13
source: Phase 224 (doc-claim ledger) close-out; operator raised "start from scratch with the documents"
---

# Reference docs: generate the "what", shrink to the "why"

## Problem (measured, Phase 224)

Phase 224 verified every checkable claim in the user-facing docs. Three cleanup rounds (GC2, GC3 and the 224-17
D-15 fixes) corrected several hundred false claims and filed about 60 product todos. Even so, three independent
random audits measured a **flat false-claim rate**: 2/56, 3/70, 3/75, pooled **8/201 = 4.0% (Wilson 95% CI
2.0–7.7%)** (`224-EVIDENCE-AUDIT*.md`). Each sweep removed one class of false claim, but the rate did not move,
because false claims are spread across many classes.

The driver is **volume of hand-written claims**, not stale history narration:

| Doc | Lines | Active ledger claims | History-flavoured lines |
|---|---:|---:|---:|
| `docs/operators-guide.md` | 3,851 | 1,608 | ~3% |
| `docs/configuration.md` | 2,617 | 1,537 | ~3% |
| `docs/report-interpretation.md` | 2,448 | 1,351 | ~4% |

That is about 4,500 hand-maintained claims on three pages. Every product change can falsify some of them, so the
4% rate will creep back unless the claim count falls.

**A from-scratch rewrite is NOT the fix.** New prose makes new claims that hit the same code-level traps Phase 224
found: fixture-injected tests on a consumer with no real producer, features no real input reaches, and two
surfaces that disagree. Those traps would produce a similar error rate.

## Proposal

1. **Generate the "what".** Config key/type/default tables, the CLI command and flag reference, and (after a spike)
   the finding-title catalogue, each rendered from source with a byte-match freshness gate. This repeats the
   pattern that has never drifted here: `docs/error-codes.md`, `docs/quirk-master-guide.md`,
   `severity-bands.json`, `score-strings.json` and `docs/cbom-classifier-coverage.md`.
2. **Shrink the prose to the "why" and "how":** task walkthroughs, interpretation and decisions. Link to the
   generated tables instead of restating them.
3. **Rewrite sections only when they are touched,** drawing on the ledger's verified TRUE/FIXED rows
   (`docs/doc-claim-ledger.jsonl`) as the fact base. Never rewrite wholesale.

Target: cut the three docs' hand-written claim count by at least half. Re-run the Phase 224 audit method (a
seeded random sample, adversarial re-derivation) before and after, and report the rate change.

## Feasibility & Effort

- **Config tables: CONFIRMED.** There are 14 config dataclasses in `quirk/config.py` (`AssessmentCfg` :20,
  `TimeoutsCfg` :43, `RetryCfg` :68, `ScanCfg` :87, `TargetsCfg` :256, `ConnectorsCfg` :264, `OutputCfg` :392,
  `IntelligenceCfg` :398, `SecurityCfg` :416, `ReportBrandingCfg` :438, `ReportCfg` :455, `BrokerCredential` :476,
  `SnmpV3Credential` :487, `AppConfig` :510) with about 156 field lines. Key, type and default can be read with
  `dataclasses.fields()`. **Gap:** no field carries `metadata=` (grep finds none), so the *meaning* column needs a
  new convention (field metadata or a side table) before it can be generated.
- **CLI reference: LIKELY.** There is no single parser tree. `run_scan.py` builds a separate
  `argparse.ArgumentParser` per subcommand (e.g. :1252 `init`, :1269 `serve`, :1315 `compliance`) behind an argv
  dispatch. A generator must enumerate the dispatch and walk each parser. Phase 224-16 did exactly that by hand for
  the operators-guide §21 Command Reference, so the method is proven.
- **Finding-title catalogue: UNKNOWN.** Titles are assembled in several modules (`quirk/engine/findings_evaluator.py`
  has only 2 literal `"title":` keys). Enumerating them needs a spike; a run-time collection over a fixture
  corpus may beat static extraction.
- **Effort: L** across all three docs. S–M per generated table. The prose shrink is the bulk of the work and is
  editorial.
- **Unknowns:** whether the ledger gate's anchors can reference generated sections (rows for generated text should
  probably be replaced by the freshness gate itself), and how much prose depends on the tables inline.
- **Spike:** yes, for the finding-title catalogue only. Config and CLI can go straight to plan.

## Not in scope

The front-door docs (README, getting-started, installation, quirk-overview) were verified exhaustively in Phase 224
(FD round) and are short. This item is about the deep reference docs.
