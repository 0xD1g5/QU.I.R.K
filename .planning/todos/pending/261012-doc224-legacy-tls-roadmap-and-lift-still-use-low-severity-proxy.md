---
type: todo
created: 2026-10-12
source: Phase 224 gap closure A (docs/report-interpretation.md section 7 and 7.1)
priority: medium
area: quirk/intelligence/roadmap.py, quirk/intelligence/score_lift.py, quirk/intelligence/scoring.py
status: pending
resolves_phase: null
---

# The legacy-TLS roadmap trigger and its score lift still key on LOW-severity counts, which scoring no longer reads

The scorer reads the endpoint-derived `evidence["legacy_tls_count"]` (`scoring.py:459`, Phase 211-03), and
`evidence.py` always emits it. Two neighbours were not moved with it:

1. `quirk/intelligence/roadmap.py:149` still sets `legacy_tls_count = sev.get("LOW", 0)`, so the "Disable legacy TLS
   versions" roadmap item appears for ANY LOW-severity finding (for example "Legacy TLS cipher suites accepted" or a
   container-library LOW) and not for a scan whose only legacy-TLS signal is the endpoint predicate.
2. `quirk/intelligence/score_lift.py:79-81` (`_resolve_legacy_tls_versions`) zeroes `finding_severity_counts["LOW"]`,
   which the scorer ignores whenever `legacy_tls_count` is present. Run live 2026-10-12 with evidence carrying both
   `finding_severity_counts.LOW = 3` and `legacy_tls_count = 3`:

        compute_item_lifts(ev, [{"title": "Disable legacy TLS versions"}])                      -> {}
        compute_item_lifts(<same without legacy_tls_count>, [...])                               -> {'legacy-tls-versions': 8}

   So on real evidence the item never shows a `(+N pts)` badge and the projected score does not include it, although
   resolving legacy TLS removes the 14-point Modern TLS driver.

The guide's section 7.1 lists "disable legacy TLS versions" among the nine items that can carry a badge; today it
cannot on a real scan.

- [ ] Make `roadmap.py` read `evidence["legacy_tls_count"]` (falling back to the LOW proxy only for hand-built dicts,
      exactly as `scoring.py:459` does).
- [ ] Make `_resolve_legacy_tls_versions` zero `evidence["legacy_tls_count"]` as well as the LOW count.
- [ ] Add a lift test whose evidence carries `legacy_tls_count` (the existing fixtures omit it).

## Feasibility & Effort

**CONFIRMED** by the two live `compute_item_lifts` calls above and by reading `roadmap.py:149` and `score_lift.py:79-81`.
Effort **S** (three one-line changes plus a test). Moving the roadmap trigger changes which items some scans list
(roadmap goldens may move). **Spike**: not needed.
