# `quirk doctor` exits 0 when the database can never be created

**Filed:** 2026-10-30 (Phase 235 post-GO code review, group (e): WR-03, with IN-02)
**Priority:** P2. Doctor is the install-health check; a false OK sends the failure to the first scan.
**Source:** `.planning/phases/235-release-launch-gate/235-REVIEW.md` WR-03, IN-02
**Where it lives:** **[package]** `quirk/cli/doctor_cmd.py:103-109, 122-130`.

## Items

- **WR-03:** `not os.path.isfile(resolved)` is treated as "first run". Verified by running `_check_db()`: a
  directory at `./quirk-output/quirk.db`, or a regular file named `./quirk-output`, returns
  `{'ok': True, 'informational': True, 'detail': 'no database yet ...'}` and doctor exits 0; the first scan then
  fails to open the DB. Fix: `exists` check first; for a missing path walk up to the first existing ancestor and
  require it to be a writable directory; if the path exists but is not a file, fail.
- **IN-02:** a missing default-path DB is informational (exit 0), but the same state with `QUIRK_DB_PATH` set to a
  not-yet-existing path is a hard failure (exit 1). Apply the same "not created yet" branch to the env-var path.

## Feasibility & Effort

- **Feasibility: CONFIRMED (reproduced by the reviewer); fix LIKELY.** The sketch in the review is close to final.
- **Effort: S.** One function, plus tests for the two bad-path shapes, the writable-ancestor case and the env-var case.
- **Unknowns:** Windows behaviour of `os.access(..., W_OK)` on directories (it is unreliable there); the frozen
  Windows sensor also runs doctor-adjacent code.
- **Spike needed?** No.
