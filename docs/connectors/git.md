# Git / Source Code Connector Setup

QU.I.R.K.'s source code connector uses semgrep to scan Git repositories for cryptographic
anti-patterns: weak algorithm usage, hardcoded keys, insecure random number generation, and
deprecated protocol invocations.

## Prerequisites

- semgrep installed — the connector looks for `semgrep` on your `PATH`:

  ```bash
  # Via pip
  pip install semgrep

  # macOS
  brew install semgrep
  ```

- The repository must be accessible as a local filesystem path, or cloneable via HTTP/SSH

## config.yaml Snippet

```yaml
connectors:
  enable_source: true
  source_targets:
    - "/path/to/local/repo"              # local filesystem path
    - "https://github.com/org/repo"      # public GitHub repo (cloned temporarily)
    - "http://gitea.internal/org/repo"   # internal Gitea instance
```

Each entry in `source_targets` is passed directly to semgrep as the scan path. Remote URLs
require git to be installed and the URL to be accessible from the scan host.

## What Gets Scanned

semgrep runs QU.I.R.K.'s built-in crypto anti-pattern ruleset (`p/cryptography`) against all
source files in the repository. The ruleset targets common insecure patterns across multiple
languages:

| Anti-Pattern | Finding type | Example |
|--------------|--------------|---------|
| Weak hash algorithm | `WEAK_ALGORITHM` | `hashlib.md5()`, `hashlib.sha1()`, `DES.new()` |
| Hardcoded cryptographic key | `HARDCODED_KEY` | `key = "mysecretkey123"` |
| Weak random for cryptographic use | `WEAK_RANDOM` | `random.randint()` for key generation |
| Deprecated TLS protocol version | `DEPRECATED_PROTOCOL` | `ssl.PROTOCOL_TLSv1`, `ssl.PROTOCOL_SSLv3` |

## Supported Languages

The `p/cryptography` semgrep ruleset covers: Python, Go, Java, JavaScript/TypeScript, Ruby.

Other file types in the repository are skipped automatically.

## How the Scan Works

QU.I.R.K. calls:

```
semgrep --json --config p/cryptography <repo_path>
```

Each finding from the `results` list is converted to a QU.I.R.K. finding with:
- The semgrep `check_id` as the rule identifier
- The file path and line number as the location
- The full semgrep finding JSON stored for dashboard drill-down

The default scan timeout is **300 seconds** per repository.

## Private Repository Access

**SSH-authenticated repos:**

```bash
ssh-add ~/.ssh/id_ed25519
```

QU.I.R.K. inherits SSH agent state from the host environment.

**Token-authenticated HTTP repos (Gitea, GitHub):**

Include credentials in the URL:

```yaml
source_targets:
  - "http://admin:your-token@gitea.internal/org/repo"
```

Or use a `~/.netrc` file to store credentials without embedding them in `config.yaml`:

```
machine gitea.internal
login admin
password your-token
```

## Graceful Degradation

If semgrep is not found on `PATH`, the source connector returns an empty result set and logs:

```
semgrep not found — install with: pip install semgrep
```

All other scanners (TLS, SSH, cloud, container) continue to run normally. Install semgrep and
re-run to include source code results.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Empty results for all repos | semgrep not on PATH | Run `which semgrep`; if not found, run `pip install semgrep` |
| `git clone` fails for remote URL | SSH key not loaded or HTTP credentials missing | Run `ssh-add` or embed credentials in the URL |
| Scan times out | Large monorepo exceeding 300s | Narrow scope by pointing `source_targets` at a specific subdirectory instead of the repo root |
| `Rules fetch failed` | No internet access for `p/cryptography` ruleset | Pre-download the ruleset: `semgrep --config p/cryptography --no-rewrite-rule-ids .` on a machine with internet, then use the cached rules path |
