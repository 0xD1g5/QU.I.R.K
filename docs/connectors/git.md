# Git / Source Code Connector Setup

QU.I.R.K.'s source code connector drives semgrep against local source-code checkouts (known defect: currently non-functional, ruleset unavailable; for
example a Git working copy). It scans directories on the scan host's filesystem; it does not
clone repositories.

> **Known defect (5.28.0):** source code scanning does not work. The connector asks Semgrep for
> the registry pack `p/cryptography`, and that pack no longer exists: the Semgrep registry
> answers HTTP 404 for `https://semgrep.dev/c/p/cryptography` (observed 2026-10-12) and semgrep
> exits 7. With semgrep installed, a scan records a "ruleset unavailable" scan error
> (`SourceRulesetUnavailable: ruleset unavailable: semgrep exited 7`), Scan Coverage shows the
> source phase as `skipped: failed (...)`, and the source domain reads Not assessed. It
> produces no source findings. Because the scan error counts against the hygiene and TLS
> error-rate readiness inputs, a scan with `source_targets` configured scores lower than one
> without. Disable `connectors.enable_source` until the ruleset is replaced.

## Prerequisites

- semgrep installed — the connector looks for `semgrep` on your `PATH`:

  ```bash
  # Via pip
  pip install semgrep

  # macOS
  brew install semgrep
  ```

- The repository must already exist as a directory on the scan host's local filesystem (clone
  it yourself first if needed)

## config.yaml Snippet

```yaml
connectors:
  enable_source: true
  source_targets:
    - "/path/to/local/repo"              # existing local directory
    - "/srv/checkouts/another-repo"      # another existing local directory
```

Each entry in `source_targets` (known defect: ruleset unavailable) is passed to semgrep as the scan path, after QU.I.R.K. validates
it. Entries that start with `-`, contain `..` or shell metacharacters, or are not an existing
directory (including every `http://`, `https://` or `ssh://` URL) are rejected and reported as an
`invalid_input` error instead of being scanned.

## What Gets Scanned

The connector is designed to run a Semgrep registry ruleset (maintained by Semgrep, not shipped
with QU.I.R.K.) against the directory. The ruleset it requests is currently unavailable, so no
patterns run; see the known defect above.

## How the Scan Works

QU.I.R.K. calls (the `p/cryptography` pack named here is the unavailable ruleset; this is the
known defect described above):

```
semgrep --json --config p/cryptography -- <repo_path>
```

If the ruleset were available, each entry from the `results` list would be converted to one QU.I.R.K. endpoint record with:
- The semgrep `check_id` as the rule identifier
- The file path and line number (`path:line`) as the location
- The full semgrep result JSON stored in `source_scan_json` (never reached today: known defect, ruleset unavailable)

The default scan timeout is **300 seconds** per repository; raise `scan.timeouts.source_seconds`
in `config.yaml` to change it.

## Graceful Degradation

If semgrep is not found on `PATH` (separate from the known defect, ruleset unavailable), the source connector returns an empty result set and, in
verbose runs, logs a message that begins `semgrep is not installed`. The rest of that message
carries an install hint that is known to be wrong; use `pip install semgrep` or
`brew install semgrep` as shown in Prerequisites.

All other scanners (TLS, SSH, cloud, container) continue to run normally. Install semgrep and
re-run to include source code results.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Empty results for all repos | semgrep not on PATH | Run `which semgrep`; if not found, run `pip install semgrep` |
| `invalid_input` / `nonexistent_path` error for a target | The entry is a URL or a path that is not an existing directory | Clone the repository first and list the local directory in `source_targets` |
| Scan times out | Large monorepo exceeding 300s | Raise `scan.timeouts.source_seconds`, or point `source_targets` at a specific subdirectory instead of the repo root |
