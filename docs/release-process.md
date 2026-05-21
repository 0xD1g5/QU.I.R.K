# QU.I.R.K. Release Process

This document is the canonical reference for cutting a QU.I.R.K. release. It
covers the version policy, the step-by-step runbook, the one-time per-project
setup, and the downstream attestation verification commands.

## Version Policy

QU.I.R.K. follows [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

### What constitutes the PUBLIC API

For semver purposes, the following surfaces are the public API and any
backwards-incompatible change to them triggers a MAJOR bump:

- **Scanner output schema** — JSON/YAML field names, types, and ordering
  guarantees for the top-level scan-output objects consumed by automation.
- **CycloneDX CBOM JSON** — field names and structure within the emitted CBOM.
- **CLI exit codes** — the numeric exit codes documented in the CLI help.

The chaos lab fixtures, internal Python module paths, and test infrastructure
are explicitly NOT public API and may change without a MAJOR bump.

### Semver commitments

| Bump  | Triggers                                                              |
| ----- | --------------------------------------------------------------------- |
| MAJOR | Breaking change to scanner output schema, CBOM JSON, or CLI exit codes |
| MINOR | New scanners, new connectors, new public API surface (backwards-compatible) |
| PATCH | Bug fixes, docs, chaos lab tweaks, performance improvements with no schema impact |

### EOL cadence

- The **current minor release line** receives bug-fix patches and security
  fixes.
- The **previous minor release line** receives security-only fixes for
  **6 months** after the successor minor ships.
- Older lines are end-of-life and receive no further fixes.

### Single source of truth (D-84-R1 / v4.10-D-02)

`pyproject.toml [project.version]` is the canonical version source. Every other
version-bearing surface derives from it:

- `quirk/__init__.py::__version__` resolves at import time via
  `importlib.metadata.version("qu-i-r-k")` (with a `tomllib` fallback for
  unpackaged in-tree dev runs).
- The CLI banner, dashboard footer, CBOM metadata, and `CHANGELOG.md` heading
  all flow from `quirk.__version__`.
- `tests/test_version.py` (Phase 37 invariant) enforces parity across six
  surfaces — `pyproject.toml` is the truth, every other surface must match.

**To bump the version, edit `pyproject.toml [project.version]` and nothing
else.** Any other version literal anywhere in the tree is a regression.

## Release Runbook

Step-by-step procedure for cutting a release. All steps are required.

1. **Verify CI is green on `main`.** Every required check (lint, unit tests,
   staleness gates, version-parity test) must be passing on the commit you
   intend to tag. If anything is red, fix it before proceeding.

2. **Bump the version in `pyproject.toml`.** Edit `[project.version]` to the
   new value (e.g. `4.10.0`). This is the only edit — every other surface
   derives from it.

3. **Build the changelog with towncrier.**

   ```bash
   towncrier build --version X.Y.Z --yes
   ```

   This consumes every `changelog.d/*.md` fragment, prepends a new
   `## X.Y.Z` section to `CHANGELOG.md`, and removes the consumed fragment
   files. The `--yes` flag skips the interactive confirmation.

4. **Commit the release prep with explicit paths.**

   ```bash
   git add pyproject.toml CHANGELOG.md changelog.d/
   git commit -m "chore(release): vX.Y.Z"
   ```

   Never use `git add -A` — explicit paths only, to avoid sweeping unrelated
   working-tree changes into a release commit.

5. **Tag the release and push.**

   ```bash
   git tag vX.Y.Z
   git push origin main --tags
   ```

6. **Monitor the release workflow.** Pushing the `vX.Y.Z` tag triggers
   `.github/workflows/release.yml`. Watch the GitHub Actions run; the workflow
   builds the wheel + sdist, publishes to PyPI via Trusted Publishers OIDC,
   and generates Sigstore attestations automatically.

7. **Verify the published release.** Once the workflow is green:
   - Confirm the new version appears on PyPI:
     `pip index versions qu-i-r-k` should list `X.Y.Z`.
   - Confirm the release page on GitHub carries the wheel, sdist, and
     attestation bundle.
   - Run the downstream attestation verification command (see below) against
     the published artifact as a sanity check.

8. **Update the milestone documentation.** Mark the corresponding milestone
   complete in `.planning/ROADMAP.md` and propagate the release version into
   the README badges if the badge URL embeds the version.

## One-Time Setup (per project, never re-run)

These steps must be completed once before the first release can publish. They
are not part of the per-release runbook.

### PyPI Trusted Publisher configuration

On PyPI (`https://pypi.org/manage/account/publishing/`), add a new pending
publisher with these exact values:

| Field                  | Value                |
| ---------------------- | -------------------- |
| PyPI project name      | `qu-i-r-k`           |
| Owner                  | `<gh-org-or-user>`   |
| Repository name        | `<repo-name>`        |
| Workflow filename      | `release.yml`        |
| Environment name       | `release`            |

After the first successful publish, PyPI converts this from "pending" to a
permanent Trusted Publisher binding.

### GitHub `release` environment

In the repository Settings → Environments, create an environment named
`release`. Optionally restrict deployment to tag pattern `v*` so the
release workflow can only run from a release tag, not from an arbitrary
branch.

### GitHub private vulnerability reporting

Enable private vulnerability reporting in repo Settings → Security & analysis.
`SECURITY.md` points reporters at this channel and assumes it is on.

## Attestation Verification (for downstream consumers)

Every release ships Sigstore attestations generated by the GitHub Actions
workflow via keyless OIDC signing. Consumers can verify the provenance of a
downloaded artifact before installing it.

### GitHub CLI path

```bash
gh attestation verify --owner <gh-org> dist/qu-i-r-k-X.Y.Z-py3-none-any.whl
```

This returns exit code 0 on success and prints the signing identity (the
GitHub Actions workflow that produced the artifact). Use this for sdists too:

```bash
gh attestation verify --owner <gh-org> dist/qu-i-r-k-X.Y.Z.tar.gz
```

### cosign alternative

For environments without the GitHub CLI, `cosign` verifies the same Sigstore
bundle:

```bash
cosign verify-blob \
  --bundle qu-i-r-k-X.Y.Z-py3-none-any.whl.sigstore \
  --certificate-identity-regexp '^https://github.com/<gh-org>/<repo>/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  qu-i-r-k-X.Y.Z-py3-none-any.whl
```

The `--certificate-identity-regexp` pins the verifier to attestations
produced by the official repository workflow. Substitute the actual
GitHub org/repo at install time.

### What is deliberately NOT shipped

QU.I.R.K. does NOT ship a `curl | bash` installer (per LAUNCH-07 — this is a
deliberate non-feature). Every supported install path carries verifiable
provenance:

- **PyPI** (`pip install qu-i-r-k`) — Sigstore attestations via Trusted
  Publishers.
- **Homebrew** (planned) — Homebrew's audit + bottle signing.
- **GHCR** (planned, Phase 85) — cosign-signed container images.

If you encounter instructions on a third-party site that ask you to pipe a
shell script from the internet directly into `bash` to install QU.I.R.K., do
not run them — they are not endorsed by the project.

## Container Image (LAUNCH-03)

Multi-arch container images are published to **GitHub Container Registry**
on every `v*.*.*` tag push, in parallel with — and downstream of — the PyPI
publish workflow.

### Coordinates

- **Workflow:** `.github/workflows/release-container.yml`
- **Trigger:** push of a `v*.*.*` tag (the same trigger that drives
  `release.yml`).
- **Registry:** `ghcr.io/0xd1g5/quirk` (lowercase per GHCR namespace rules;
  the GitHub org `0xD1g5` is normalized to `0xd1g5` for the image path).
- **Tags published per release:** `:latest` and `:vX.Y.Z`.
- **Platforms:** `linux/amd64`, `linux/arm64` — built via
  `docker/build-push-action@v6` with QEMU emulation in GitHub Actions.

### How the container stays in lock-step with the PyPI wheel

The Dockerfile installs QU.I.R.K. from PyPI:

```dockerfile
RUN pip install --no-cache-dir "qu-i-r-k[all]==${QUIRK_VERSION}"
```

`QUIRK_VERSION` is injected by the workflow from the triggering git tag.
Before the build runs, the workflow polls
`https://pypi.org/pypi/qu-i-r-k/${version}/json` for up to 10 minutes so the
container build only proceeds once the PyPI wheel has propagated. This means
**the bits inside the container are byte-identical to `pip install qu-i-r-k`
on the host** — no parallel build path, no source-tree drift.

### Verification after a release

After a tag publish has completed both workflows:

```bash
docker pull ghcr.io/0xd1g5/quirk:vX.Y.Z
docker run --rm ghcr.io/0xd1g5/quirk:vX.Y.Z
```

The container's default `CMD` is `quirk --help`, so a successful run prints
the CLI help banner including the version string. Confirm the version
matches the tag.

For multi-arch confirmation:

```bash
docker buildx imagetools inspect ghcr.io/0xd1g5/quirk:vX.Y.Z
```

The manifest list MUST contain both `linux/amd64` and `linux/arm64`
descriptors.

### One-time setup (first publish only)

The GHCR package is created as **private** on first publish. Flip it to
public so unauthenticated `docker pull` works for evaluators:

1. Open `https://github.com/0xD1g5/QU.I.R.K./pkgs/container/quirk` after the
   first successful `release-container` workflow run.
2. Click **Package settings -> Change visibility -> Public**.
3. Confirm with the package name.

Subsequent publishes inherit the public visibility automatically.

### What this image deliberately does NOT include

- **`playwright` browsers** — `qu-i-r-k[all]` declares `playwright` as an
  optional extra, but the headless browser binaries are out of scope for the
  v4.10 GHCR ship to keep the image lean. Pull them at runtime inside the
  container if a specific scan path needs them.
- **Distroless / Alpine variants** — `python:3.11-slim` is the only base
  (per Phase 85 D-LAUNCH Docker). `alpine` has musl/cryptography wheel
  friction; distroless removes the shell users need for first-run debugging.

## Homebrew Tap (LAUNCH-02)

QU.I.R.K. ships a Homebrew tap formula so macOS consultants can install with a
single command, with no Python / pip / virtualenv knowledge required. The tap
is a **personal/org tap** (`0xD1g5/homebrew-quirk`), **not** homebrew-core —
homebrew-core's submission and review process is too slow for v4.10's launch
window, and a personal tap lets us iterate without external maintainer review.

**End-user install command** (the only line users need):

```bash
brew install 0xD1g5/quirk/quirk
```

The canonical formula source is `Formula/quirk.rb` in this repo. On each
release, the file is copied verbatim into the tap repo so that code review +
changelog continuity happen here, not in the (low-traffic) tap repo.

### One-time tap-repo bootstrap

Do this once, before the first v4.10 release ships:

1. Create the GitHub repo `0xD1g5/homebrew-quirk` (public, MIT-licensed, no
   wiki / no issues — it is a pure formula host). The `homebrew-` prefix is
   mandatory: `brew tap 0xD1g5/quirk` strips the prefix when resolving.
2. Initialize the repo with a top-level `Formula/` directory.
3. Copy `Formula/quirk.rb` from this repo to `Formula/quirk.rb` of the tap repo.
4. Commit + push with message `chore: bootstrap homebrew-quirk tap`.
5. Smoke-test the tap: `brew tap 0xD1g5/quirk && brew tap-info 0xD1g5/quirk`
   (the formula will still fail to install at this stage because the
   `url`/`sha256` are placeholders pointing at a non-existent 0.0.0 release —
   that is expected and resolves at the first real release below).

### Per-release formula update procedure

After every PyPI publish (Trusted Publishers workflow per the earlier
"PyPI Trusted Publishers" section in this document), update the formula:

1. **Wait for PyPI sdist availability.** The sdist must be reachable at:

   ```
   https://files.pythonhosted.org/packages/source/q/qu-i-r-k/qu-i-r-k-X.Y.Z.tar.gz
   ```

   (replace `X.Y.Z` with the release version). PyPI's CDN is usually <30s
   behind the publish step; if `curl -fsSI <url>` 404s, wait and retry.

2. **Compute the sdist sha256:**

   ```bash
   curl -fsSL https://files.pythonhosted.org/packages/source/q/qu-i-r-k/qu-i-r-k-X.Y.Z.tar.gz \
     | shasum -a 256
   ```

3. **Edit `Formula/quirk.rb` in BOTH this repo AND the tap repo.** Update:
   - `url` → bump `X.Y.Z` in both occurrences of the version segment.
   - `sha256` → paste the value from step 2.
   - The formula `version` is implicit from the `url` filename — no separate
     bump needed.

4. **Commit + push both repos** with message
   `chore(homebrew): bump quirk to vX.Y.Z`.

5. **Smoke-test the published install** on a clean macOS arm64 machine:

   ```bash
   brew untap 0xD1g5/quirk 2>/dev/null || true
   brew tap 0xD1g5/quirk
   brew install 0xD1g5/quirk/quirk
   quirk --version   # must print X.Y.Z
   ```

   This exercises the formula's `test do` block via `brew test quirk` as well
   as the actual user install path.

### Why pipx-style venv isolation

Homebrew's system Python (`python@3.11`) should never host third-party
packages — `pip install` into the Homebrew Python is unsupported and breaks
on every `brew upgrade python@3.11`. The standard Homebrew-idiomatic answer
for a Python CLI is a virtualenv created under the formula's `libexec`, with
the entrypoint script symlinked into `bin` via `bin.install_symlink` — that
is exactly what `Formula/quirk.rb` does via `Language::Python::Virtualenv`.
The user-facing effect is identical to `pipx install qu-i-r-k`: one isolated
Python environment per CLI, no cross-contamination, clean `brew uninstall`.
The formula also `depends_on "pipx"` so users have it available for other
Python CLIs, matching Homebrew's published guidance for Python tooling.

### What this section deliberately does NOT do

- **Submit to homebrew-core.** Out of scope for v4.10; the personal tap ships
  immediately and is fully sufficient for the LAUNCH-02 success criterion.
  Revisit homebrew-core as a future milestone once the formula has been
  stable across several releases.
- **Bottle / pre-built binaries.** The formula installs from PyPI sdist on
  the user's machine. Bottle generation requires a homebrew-core-style build
  farm and is not justified for the v4.10 audience.
