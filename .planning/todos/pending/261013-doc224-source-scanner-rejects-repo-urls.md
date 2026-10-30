---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-LAB; ledger row DCL-CHAOSLAB-0088 (docs/chaos-lab.md §3.8 source_targets block)
priority: medium
area: quirk/scanner/source_scanner.py, quirk/util/subprocess_input.py (validate_repo_path), docs/configuration.md (source_targets rows)
status: pending
resolves_phase: null
owner: "999.127"
---

# `connectors.source_targets` rejects repository URLs, but the docs say URLs work

`scan_source_repo` validates every target with `validate_repo_path`, which requires an existing local directory
(`quirk/util/subprocess_input.py:149-150`, reason `nonexistent_path`). A URL target becomes one SOURCE row with
`scan_error_category="invalid_input"` (`quirk/scanner/source_scanner.py:47`) and semgrep never runs. Observed
in-process: `scan_source_targets(["http://labadmin:admin123@localhost:20006/labadmin/crypto-antipatterns-python"])`
-> one row, `invalid_input`. Nothing clones a repo before the scan (`run_scan.py:3203` passes the list straight in).

`docs/chaos-lab.md` §3.8 told operators to put the lab's Gitea URLs in `source_targets`; GC2 replaced that with a
`git clone` step plus local paths. `docs/configuration.md:407` and `:455` still describe `source_targets` as
"Git repo paths or URLs" (outside gc2-LAB's ownership; reported to the orchestrator) — **fixed in Phase 224** (both tables now say local directories only; the `https://` example was replaced).
The interactive wizard still invites URLs: `quirk/interactive.py:199` prompts `"Source code paths or Git URLs"`.

- [ ] Either support URL targets (shallow clone into a temp dir, then scan) or reject them with a clear error
      message instead of a generic `invalid_input` row.
- [ ] Make `docs/configuration.md` match whichever behaviour ships (currently documents rejection).
- [ ] Fix the `quirk/interactive.py:199` wizard prompt to match whichever behaviour ships.

## Feasibility & Effort

**CONFIRMED** (source read plus the in-process call above). Effort **S** for a clear error message; **M** for
clone support (needs a git dependency check, temp-dir cleanup, credential handling for private repos, and the
CR-02 argv-injection guard extended to URLs). Unknown: whether credentialed URLs should be allowed at all, given
they would land in config files. No spike needed for the error-message option.
