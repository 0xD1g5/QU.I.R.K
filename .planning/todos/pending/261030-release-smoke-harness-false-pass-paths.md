# Release smoke harness can report PASS for a run that did not execute (stale transcript, port 8512, no timeout)

**Filed:** 2026-10-30 (Phase 235 post-GO code review, group (a): CR-03, WR-09, WR-10, plus IN-05)
**Priority:** P2. Tooling only, but it is the release gate's own evidence; a false PASS defeats it. Fix before the next rehearsal.
**Source:** `.planning/phases/235-release-launch-gate/235-REVIEW.md` CR-03, WR-09, WR-10, IN-05
**Where it lives:** **[tooling only]**, not in the published package: `scripts/release_smoke.sh`, `scripts/release_smoke_inner.sh`.

## Items

- **CR-03** `release_smoke.sh:255-259, 313-316, 339-342`: `mkdir -p "${OUT}/inner"` never empties it, copy failures
  are swallowed (`2>/dev/null`), `RUN_RC` is never consulted, and the verdict greps `transcript.txt` for
  `RESULT: PASS` anywhere. Re-running a leg with the same `--out` after the container dies prints the OLD PASS. The
  3.15 re-check (`:346-356`) reads a stale `pip-negative.txt` the same way.
  Fix: `rm -rf "${OUT}/inner" "${OUT}/inner-stdout.txt"` first; fail on `docker cp` error; PASS only when
  `RUN_RC == 0` and the transcript's last line is `RESULT: PASS`.
- **WR-09** `release_smoke_inner.sh:445-530`: host legs run `quirk serve --port 8512`, the operator's default
  dashboard port. If theirs is up, the probe gets a 200 from the wrong server and checks 7-9 pass against it.
  Fix: refuse if the port already answers, require `kill -0 "${SERVE_PID}"` after the probe, or use a free port.
- **WR-10** `release_smoke_inner.sh:159-170`: `eval "$1"` with no timeout; a blocking README command hangs the leg
  (host: forever; Linux: until `sleep 7200`, which then triggers CR-03). Fix: watchdog/`timeout 900` for
  non-state-changing commands, keep `cd`/`source` in the shell, record FAIL on expiry.
- **IN-05** `release_smoke.sh:207-210, 52, 340`: dead `run_env()`; `out_dir_ok` runs `mkdir -p` before deciding to
  refuse the path; verdict should compare `tail -n 1`.

## Feasibility & Effort

- **Feasibility: CONFIRMED by review (CR-03 by code read, not executed); fix LIKELY.** Shell-only changes, each
  with a clear mechanical shape. WR-10 is the awkward one because `eval` is deliberate (state must persist).
- **Effort: S** for CR-03, WR-09, IN-05; **M** for WR-10 (macOS has no `timeout`; needs the watchdog split).
- **Unknowns:** whether the 2026-10-29 rehearsal PASS transcripts were produced on fresh `--out` dirs (the evidence
  dir naming suggests yes; verify before 235-18 leans on them).
- **Spike needed?** No. A negative test per item (kill the container mid-run; bind 8512 first) proves each fix.
