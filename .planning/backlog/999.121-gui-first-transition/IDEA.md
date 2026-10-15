# 999.121 — GUI-first transition: close the gaps between "dashboard-first" positioning and the product

**Filed:** 2026-10-12 (operator decision during `/gsd-plan-phase 224`)
**Priority:** P2 (positioning has changed; these are the places the product still assumes a shell)
**Horizon entry:** `HORIZON.md` Open-Item Ledger, row `999.121`.

## Why this exists

On 2026-10-12 the operator repositioned QU.I.R.K. from "CLI + local web dashboard" to
**dashboard-first, CLI-complete** (`PROJECT.md` "What This Is"; Phase 224 CONTEXT D-16 applies it
to the user-facing docs). Development effort was already GUI-first: of the files touched in the last
300 commits, ~720 were dashboard source or built statics, vs 7 in core `quirk/`. Phase 224 only
changes **docs**. This item holds the **product** work that makes the positioning complete. Each
sub-item has its own pending todo (listed below).

Also parked here: the former `PROJECT.md` clause "a SaaS platform on the strategic roadmap". It had
no live owner and was removed under Phase 224 D-09 ("docs describe only what ships"). Revive it as
its own row if it becomes a real intent.

## Sub-items (one todo each, `.planning/todos/pending/`)

1. `261012-gui-first-bare-quirk-launches-cli-wizard.md`: bare `quirk` starts the interactive
   CLI wizard, not the dashboard.
2. `261012-gui-first-cli-only-admin-commands-triage.md`: 11 subcommands have no API route. Triage
   which ones belong in the GUI. Includes the remote-bind token setup that needs a shell.
3. `261012-gui-first-per-scan-report-download.md`: the dashboard serves reports for the latest scan only.
   Phase 227 (2026-10-15, D-09) re-homed two doc224 todos here as members of this sub-item:
   `261012-doc224-dashboard-job-reports-not-downloadable.md` and
   `261013-doc224-reports-route-latest-only-premise-is-false.md` (both `owner: "999.121"`).

## Feasibility & Effort

All checks run 2026-10-12 against `origin/main` `a073cab9`.

- **The local on-ramp is already GUI-capable: LIKELY.** Phase 224 verifies it by command-run.
  `quirk/dashboard/api/routes/jobs.py:708` (`POST /jobs`) builds the job YAML from form values
  (`:198`), so no hand-written config is needed. `quirk/dashboard/api/middleware/auth.py:55` passes
  through when no token is configured. `src/dashboard/src/context/AuthProvider.tsx:9` treats that
  200 as authenticated (no login screen). `quirk/dashboard/server.py:158` opens the browser.
- **Sub-item 1: CONFIRMED gap, effort S-M.** It changes default CLI behaviour, so it needs a
  compatibility decision: scripts or users may rely on bare `quirk` → wizard. The likely shape is
  bare `quirk` on a TTY → `quirk serve`, with the wizard behind an explicit flag/subcommand. Unknown:
  how many docs/tests pin the wizard default (`run_scan.py:1840` area).
- **Sub-item 2: CONFIRMED gap, effort M-L, most of it triage.** These subcommands are dispatched
  in `run_scan.py` (`_sys.argv[1] == ...`) with no matching route among the dashboard routers:
  token, compliance, cve, ticket, doctor, init, db, export, errors, analyze-token, console. Several
  are legitimately operator/CLI-only (db, errors, console, init). The triage is the deliverable;
  porting comes after.
- **Sub-item 3: CONFIRMED gap, effort M.** `quirk/dashboard/api/routes/reports.py:155-185`
  selects the newest stamp in the output dir. Reports for earlier scans exist on disk but have no
  route. The memory/precedent that artifacts are stamped by render time, not `scan_run_id`, means
  the scan↔report association has to be built first. That is the main unknown, so spike it.
- **Sub-item 3, re-homed doc224 members:** `quirk/dashboard/api/routes/reports.py:15` (re-grepped 2026-10-15) still states "nothing on disk associates them", the premise the second todo calls false; the first todo's job-report links hit the same latest-only route.
- **Spike?** Only for sub-item 3's scan↔report association. 1 and 2 are design decisions.
