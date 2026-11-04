---
type: todo
created: 2026-11-03
source: "Phase 235.1 research Open Question 1"
priority: medium
area: quirk/scanner/container_scanner.py
status: pending
owner: "999.127"
target_release: "5.29"
---
# Container scanner returns `[]` when syft runs but fails

**Filed:** 2026-11-03 (Phase 235.1 research, Open Question 1). Explicitly kept OUT of SRCSCAN-03 scope.

## The defect

`quirk/scanner/container_scanner.py:91-101`: when syft is present and runs, but exits non-zero, times out, or emits
unparsable JSON, the `except (...)` branch logs a warning and `return []`. The caller records the container scan as
"ran" with zero findings: the same false-clean class as source-scanner WR-01 / IN-04 that 235.1-03 fixed for semgrep.
The return code is also never inspected after a successful `json.loads`.

## Candidate fix

Mirror 235.1-03: per-target in-band error rows (`protocol="CONTAINER"`, redacted `scan_error`, category `timeout` /
`exception`), keep other images' results, raise only when every image failed, redact image refs / absolute paths
before building the message, and pin the score effect (measured through `derive_report_findings`).

## Feasibility & Effort

- **Feasibility:** CONFIRMED by reading the code; fix LIKELY (pattern already proven in source_scanner.py).
- **Effort:** S-M (about half a day: loop rewrite, tests, score pin, CHANGELOG disclosure).
- **Unknowns:** whether `CONTAINER` error rows are assessable in `evidence.py` the same as `SOURCE` (measure, do not assume).
- **Spike needed?** No.
