# Git / Source Code Connector Setup

QU.I.R.K.'s source code connector uses semgrep to scan local source-code checkouts (for
example a Git working copy) with the Semgrep registry ruleset `p/cryptography`. It scans
directories on the scan host's filesystem; it does not clone repositories.

> **Known issue (observed 2026-10-12):** the Semgrep registry returned HTTP 404 for
> `https://semgrep.dev/c/p/cryptography`, the registry URL for a pack named `p/cryptography`,
> while the same URL pattern for other packs such as `p/security-audit` returned HTTP 200. Until the connector's ruleset name is
> corrected, expect the source scan to return no findings. This is tracked as a product bug.

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

Each entry in `source_targets` is passed to semgrep as the scan path, after QU.I.R.K. validates
it. Entries that start with `-`, contain `..` or shell metacharacters, or are not an existing
directory (including every `http://`, `https://` or `ssh://` URL) are rejected and reported as an
`invalid_input` error instead of being scanned.

## What Gets Scanned

semgrep runs the Semgrep registry ruleset `p/cryptography` (maintained by Semgrep, not shipped
with QU.I.R.K.) against the directory. Which patterns and languages it covers is defined by that
ruleset, not by QU.I.R.K.; see the known issue above.

## How the Scan Works

QU.I.R.K. calls:

```
semgrep --json --config p/cryptography -- <repo_path>
```

Each entry from the `results` list is converted to one QU.I.R.K. endpoint record with:
- The semgrep `check_id` as the rule identifier
- The file path and line number (`path:line`) as the location
- The full semgrep result JSON stored in `source_scan_json`

The default scan timeout is **300 seconds** per repository; raise `scan.timeouts.source_seconds`
in `config.yaml` to change it.

## Graceful Degradation

If semgrep is not found on `PATH`, the source connector returns an empty result set and, in
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
