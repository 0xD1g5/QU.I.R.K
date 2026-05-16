---
phase: 71-protocol-scanner-warnings
plan: 02
subsystem: scanner-protocol
tags: [audit-close, WR-03, PROTO-02, logging-hygiene]
requires: []
provides:
  - "Narrowed except clauses + logger.warning in ssh/container/source scanners (WR-03 closure)"
affects:
  - quirk/scanner/ssh_scanner.py
  - quirk/scanner/container_scanner.py
  - quirk/scanner/source_scanner.py
tech_stack:
  added: []
  patterns:
    - "Module-level `_LOG = logging.getLogger(__name__)` (named `_LOG` not `logger` to avoid shadowing the `logger=` kwarg present on public scanner APIs)"
    - "Narrow exception tuple: (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError, json.JSONDecodeError) with `as e` for log formatting"
key_files:
  created:
    - tests/test_subprocess_logging.py
  modified:
    - quirk/scanner/ssh_scanner.py
    - quirk/scanner/container_scanner.py
    - quirk/scanner/source_scanner.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - "Plan-time files_modified target (fingerprint.py) was corrected post-investigation; fingerprint.py does NOT contain the WR-03 swallow pattern. User decided Option A: narrow the 3 actual sites in ssh_scanner / container_scanner / source_scanner. Recorded as approved deviation."
  - "Renamed module-level logger to `_LOG` (not `logger`) because all three scan_* public functions accept a `logger=` kwarg that would otherwise shadow the module logger inside the function body — caught by the first test run, fixed before commit."
metrics:
  duration_minutes: 3
  completed: 2026-05-15
---

# Phase 71 Plan 02: Narrow WR-03 Subprocess Swallows Summary

Replaced the bare `except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):` swallow pattern in 3 scanner modules (`ssh_scanner._run_ssh_audit`, `container_scanner.scan_container_image`, `source_scanner.scan_source_repo`) with a narrowed exception tuple plus `_LOG.warning(...)` so subprocess failures are auditable; partial-result return paths preserved.

## What Was Built

- **3 scanner modules patched** (`quirk/scanner/{ssh,container,source}_scanner.py`):
  - Added `import logging` + module-level `_LOG = logging.getLogger(__name__)`.
  - Replaced `except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):` with `except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError, json.JSONDecodeError) as e:` and added `_LOG.warning("subprocess failed in <func> for %r: %s", target, e)`.
  - Existing partial-result fall-through (`return None` / `return []`) preserved verbatim.
- **3 tests added** (`tests/test_subprocess_logging.py`) — one per module, covering the timeout / FileNotFoundError / JSONDecodeError paths via `monkeypatch` + `caplog`.
- **AUDIT-TASKS.md row WR-03 flipped** to `Phase 71 | [x] closed` with evidence describing the scope correction.

## Deviations from Plan

### Scope Correction (User Option A)

**Found during:** Investigation before Task 1.
**Issue:** Plan frontmatter `files_modified` named `quirk/scanner/fingerprint.py`, but fingerprint.py does NOT contain a `subprocess.*` call wrapped by `except Exception` (it only contains socket/TLS code with `socket.timeout`, `ssl.SSLError`, and a `BaseException` line at the file end — none match WR-03 wording "Bare except Exception swallowing subprocess errors silently").
**Investigation:** Grepped `grep -rn "except (subprocess" quirk/scanner/` and found the actual WR-03 pattern in three sites:

| File | Line | Pattern |
| --- | --- | --- |
| `quirk/scanner/ssh_scanner.py` | 29 | `except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):` |
| `quirk/scanner/container_scanner.py` | 85 | `except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):` |
| `quirk/scanner/source_scanner.py` | 62 | `except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):` |

**User decision:** Option A — narrow all three sites per D-08 ("only narrow the bare excepts that WR-03/08/10 specifically point at"), since the WR-03 audit-row wording does not name a single file and these three sites are the only places in the protocol-scanner subsystem where subprocess exceptions are silently swallowed via a fall-through `Exception`.
**Files modified retroactively:** `files_modified` list in this SUMMARY replaces the plan's `fingerprint.py` entry with the three real sites above plus a renamed test file (`tests/test_subprocess_logging.py` instead of the plan's `tests/test_fingerprint_subprocess_logging.py`).
**Commits:** see Commits section.

### Auto-fixed (Rule 1 — Bug)

**1. [Rule 1 - Bug] Module logger shadowed by `logger=` kwarg**
- **Found during:** First test run (after initial commits 65d3f8e / 8c3b2b7 / eff4c69).
- **Issue:** `scan_container_image(image_ref, timeout, logger=None)` and `scan_source_repo(repo_path, timeout, logger=None)` accept a `logger=` kwarg. The initial commits introduced a module-level name `logger`, which the function-scope parameter shadowed to `None`, causing `AttributeError: 'NoneType' object has no attribute 'warning'` inside the except block.
- **Fix:** Renamed module-level binding to `_LOG` (uppercase, underscore-prefixed) so it can never collide with any user-passed `logger=` kwarg. Applied uniformly across all three scanner modules for symmetry.
- **Files modified:** `quirk/scanner/{ssh,container,source}_scanner.py`
- **Commit:** `eccad5a`

## Commits

| Hash | Message |
| --- | --- |
| `65d3f8e` | `fix(71-02): narrow except + logger.warning in ssh_scanner (WR-03)` |
| `8c3b2b7` | `fix(71-02): narrow except + logger.warning in container_scanner (WR-03)` |
| `eff4c69` | `fix(71-02): narrow except + logger.warning in source_scanner (WR-03)` |
| `eccad5a` | `fix(71-02): rename module logger to _LOG to avoid kwarg shadowing` |
| `acade61` | `test(71-02): verify subprocess failures log warning and return partial result (WR-03)` |

(SUMMARY/audit-flip commit to follow.)

## Verification

- `python -m compileall quirk/scanner/{ssh,container,source}_scanner.py` → all 3 clean.
- `pytest tests/test_subprocess_logging.py -x` → **3 passed in 0.08s**.
- `grep -c "scanners-protocol/WR-03.*Phase 71.*\[x\] closed" .planning/audit-2026-05-08/AUDIT-TASKS.md` → 1.

## Success Criteria

- [x] WR-03 subprocess swallow narrowed and logged (in 3 sites, not 1 — see scope correction)
- [x] 3 new tests pass (plan asked for 2; delivered 3 — one per module)
- [x] Audit ledger row WR-03 closed under Phase 71
- [x] Other broad excepts in scanner code untouched (D-08, D-15 honored — only the WR-03 sites changed)

## Self-Check: PASSED

Files exist:
- FOUND: quirk/scanner/ssh_scanner.py (logger + narrow except verified)
- FOUND: quirk/scanner/container_scanner.py (logger + narrow except verified)
- FOUND: quirk/scanner/source_scanner.py (logger + narrow except verified)
- FOUND: tests/test_subprocess_logging.py (3 tests)

Commits in `git log`:
- FOUND: 65d3f8e, 8c3b2b7, eff4c69, eccad5a, acade61
