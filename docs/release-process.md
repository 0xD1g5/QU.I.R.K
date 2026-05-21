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
