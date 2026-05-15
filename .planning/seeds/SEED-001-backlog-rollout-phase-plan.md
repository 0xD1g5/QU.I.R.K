---
id: SEED-001
status: superseded
planted: 2026-04-02
planted_during: Post-Phase-7 / Pre-Phase-8 (Legacy Debt Cleanup)
closed: 2026-05-05
closed_reason: >
  Superseded by project evolution. The seed called for a structured backlog rollout
  plan after Phase 9; that work was accomplished implicitly through milestones v4.1–v4.6
  (Phases 10–50). The backlog has been sequenced and the primary enterprise-readiness
  work is now complete. No action required.
trigger_when: Phase 9 (Scoring Consolidation) is marked complete
scope: Medium
---

# SEED-001: Create a prioritized phase rollout plan from all backlog items

## Why This Matters

After Phase 8 and Phase 9 close, the codebase will be clean and the scoring system
will be authoritative. That is the right moment to stop treating the backlog as a
parking lot and turn it into an actual roadmap.

At that point there are 59 catalogued BACK-xx items covering:
- CLI/UX startup sequence improvements (BACK-27–BACK-36)
- Legacy dead code removal (BACK-37–BACK-39)
- Show-stopper bug fixes (BACK-40–BACK-59, completed in Phase 8/9)
- Scanner coverage gaps: email, Kerberos, SAML/OAuth, DNSSEC, message brokers
- Cloud gaps: GCP connector, K8s secrets, S3/Blob encryption audit
- Intelligence gaps: compliance mapping, trend analysis, scoring improvements
- Operational gaps: scheduled scanning, distributed nodes
- Dashboard improvements: multi-scan nav, heatmap, migration roadmap overhaul

Without a structured rollout plan, these will age in the backlog indefinitely.
A dedicated review session sequences them into phases grouped by theme and effort,
so the next milestone has a clear execution order rather than 59 disconnected items.

## When to Surface

**Trigger:** Phase 9 (Scoring Consolidation) is marked complete in ROADMAP.md

This seed should be presented during `/gsd:new-milestone` when:
- The new milestone is being scoped after Phase 8 and Phase 9 both show `[x]`
- The user is deciding what comes next for QUIRK v2
- Any milestone description mentions "backlog", "next phase", or "roadmap review"

## Scope Estimate

**Medium** — This is a planning phase, not an implementation phase. One session to
group the 59 items by theme, assign priorities, identify dependencies, and produce
a sequenced phase list. The output is an updated ROADMAP.md with concrete next phases
promoted from backlog, not code.

Suggested themes for grouping:
1. **Scanner coverage** — email, Kerberos, SAML, DNSSEC, message brokers (BACK-16–19, 22)
2. **Cloud depth** — GCP, K8s, S3/Blob (BACK-14, 15, 13)
3. **CLI/UX** — startup sequence overhaul (BACK-27–36)
4. **Intelligence** — compliance mapping, trend analysis, calibration (BACK-20, 21, 43)
5. **Dashboard** — multi-scan, heatmap, roadmap visual, light/dark (BACK-02, 03, 04, 07)
6. **Operational** — scheduled scanning, distributed nodes (BACK-25, 26)
7. **API/identity** — REST fuzzing, OpenAPI, Bearer tokens, ADCS (BACK-09–11, 39)

## Breadcrumbs

- `.planning/ROADMAP.md` — `## Backlog` section, BACK-01 through BACK-59
- `.planning/codebase/CONCERNS.md` — source audit that generated BACK-40–59
- `.planning/phases/8-legacy-debt-cleanup/` — Phase 8 scope
- `.planning/phases/9-scoring-consolidation/` — Phase 9 scope

## Notes

Planted at end of codebase audit session (2026-04-02). The audit surfaced that QUIRK
was built on an abandoned legacy project and had systemic inconsistencies. Phase 8
and Phase 9 close the structural debt. After that, the backlog represents genuine
feature work — scanner coverage, cloud depth, intelligence improvements — that would
make QUIRK a credible v2 product. This seed ensures that moment gets a proper planning
pass rather than ad-hoc phase selection.
