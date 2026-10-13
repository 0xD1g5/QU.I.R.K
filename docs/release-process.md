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
- **CLI exit codes** — the numeric exit codes the `quirk` commands return.

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
  `importlib.metadata.version("quirk-scanner")` (with a `tomllib` fallback for
  unpackaged in-tree dev runs).
- The CLI banner and `--version` output, CBOM metadata, and the report writer's
  platform and intelligence versions all flow from `quirk.__version__`. The
  `CHANGELOG.md` section heading is the exception: towncrier writes it from the
  `--version` argument you pass in step 4.
- `tests/test_version.py` enforces parity across the version-bearing surfaces
  (package, CBOM builder, report writer, intelligence config, installed
  distribution metadata) — `pyproject.toml` is the truth, every other surface
  must match. Its CLI `--version` subprocess check is marked `xfail(strict=False)`,
  so that one leg cannot fail the suite; confirm `quirk --version` yourself
  after the bump.

**To bump the version, edit `pyproject.toml [project.version]` and no other code or
packaging metadata.** A version literal in any code surface is a regression. The one
hand-maintained exception is prose: the README title (`# QU.I.R.K. — vX.Y.Z`, line 13)
is not derived from `pyproject.toml` and is updated by hand in step 9.

## Release Runbook

Step-by-step procedure for cutting a release. All steps are required.

**Interpreter rule:** run every command in this runbook with `.venv/bin/python`,
`.venv/bin/pytest`, or `.venv/bin/pip` — never bare `python3`/`pip`. A bare
`python3` can resolve to a different interpreter than the project's virtual
environment (on macOS, to Apple's or Homebrew's system Python), and a stale or
orphan `quirk` install in that interpreter answers `importlib.metadata` queries with
a phantom version. `tests/test_version.py::test_single_distribution_provides_quirk`
guards against it: it fails when more than one installed distribution claims the
`quirk` import package.

1. **Verify CI is green on `main`.** Every required check (the Python CI
   workflow's full suite, including the version-parity test; the Dashboard
   Quality workflow; and the Python Staleness Gate) must be passing on the
   commit you intend to tag. If anything is red, fix it before proceeding.

2. **Run a release dry-run before tagging.** Before touching `pyproject.toml`,
   manually trigger `.github/workflows/release.yml` via `workflow_dispatch`
   against `main` (no tag exists yet at this point):

   ```bash
   gh workflow run release.yml --ref main
   gh run watch <run-id>
   ```

   (or, from the browser: Actions tab -> Release -> Run workflow -> branch
   `main` -> Run workflow).

   **What the dry-run DOES run:** the `build` job, and the full
   `windows-package` job — PyInstaller onedir build, the production-signing
   skip (no cert configured), the "CI self-test — ephemeral cert signing
   round-trip" step, and Windows zip assembly.

   **What it deliberately does NOT do:** the `publish` job (PyPI, Trusted
   Publishers + Sigstore) is skipped entirely, and "Attach zip to GitHub
   Release" is skipped — both are gated on
   `github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')`, so a
   `workflow_dispatch` run has zero external side effects, including a
   dispatch that targets a tag ref, since the guard tests the triggering event
   and not just the ref shape.

   **Where the output goes:** the assembled zip is downloadable from the run's
   Artifacts section under the name `quirk-windows-dry-run`.

   **Stop rule:** if the dry-run is red, do NOT proceed to tag. An immutable
   tag turns a pipeline bug into a permanent gap in release history — this is
   exactly what happened with `v5.11.0`, which shipped to PyPI with no Windows
   asset because a `windows-package` step that had never once executed failed
   by construction on the first tag that reached it.

3. **Bump the version in `pyproject.toml`.** Edit `[project.version]` to the
   new value (`X.Y.Z`). This is the only code or metadata edit — every
   runtime version surface derives from it.

4. **Build the changelog with towncrier.**

   ```bash
   towncrier build --version X.Y.Z --yes
   ```

   This consumes every `changelog.d/*.md` fragment, prepends a new
   `## [X.Y.Z] - <date>` section to `CHANGELOG.md`, and removes the consumed fragment
   files. The `--yes` flag skips the interactive confirmation.

5. **Commit the release prep with explicit paths.**

   ```bash
   git add pyproject.toml CHANGELOG.md changelog.d/
   git commit -m "chore(release): vX.Y.Z"
   ```

   Never use `git add -A` — explicit paths only, to avoid sweeping unrelated
   working-tree changes into a release commit.

6. **Tag the release and push.** The tag must be **three-component** semver
   (`v5.15.0`), never two (`v5.15`), and it must actually reach `origin`.

   ```bash
   git tag vX.Y.Z
   git push origin main --tags
   # Confirm it landed — a tag that stays local releases nothing:
   git ls-remote --tags origin | grep vX.Y.Z
   ```

   > **Why this step has its own warning (RVW-004).** `release.yml` used to
   > trigger on `v*.*.*`, which matches three components and *silently matches
   > nothing else*. `v5.9`, `v5.13` and `v5.14` were all two-component tags:
   > pushing them fired no workflow, produced no run, and raised no error, so
   > three milestones were recorded as shipped while PyPI stayed on an older
   > version. `v5.13` was additionally never pushed at all. The trigger is now
   > the looser `v[0-9]*` so a malformed tag still produces a visible run — but
   > the convention remains 3-component, and the `git ls-remote` check above is
   > the cheapest way to catch the never-pushed variant.

7. **Monitor the release workflow.** Pushing the `vX.Y.Z` tag triggers
   `.github/workflows/release.yml`. Watch the GitHub Actions run; the workflow
   builds the wheel + sdist, publishes to PyPI via Trusted Publishers OIDC,
   and generates Sigstore attestations automatically. Unlike the dry-run in
   step 2, this run is a real `push` event against a `refs/tags/` ref, so it
   additionally runs the `publish` job and attaches the Windows zip to the
   GitHub Release.

8. **Verify the published release.** Once the workflow is green:
   - Confirm the new version appears on PyPI:
     `pip index versions quirk-scanner` should list `X.Y.Z`.
   - Confirm the GitHub release page carries the Windows operator zip
     (`quirk-windows-X.Y.Z.zip`). The wheel and sdist are published to PyPI,
     not attached to the GitHub release.
   - Run the downstream attestation verification command (see below) against
     the published artifact as a sanity check.

9. **Update the milestone documentation.** Mark the corresponding milestone
   complete in whatever roadmap you keep, and update the version in the README
   title by hand. The README badges do not embed a version (the PyPI badge reads
   the live version from shields.io), so they need no edit. If a tag ever fails
   to produce a release run — silently, with no red step to notice — the
   Release Tag Hygiene Guard below is the standing backstop that catches it
   on the next scheduled run.

## Release Tag Hygiene Guard

**What it is:** `.github/workflows/release-tag-hygiene.yml`, scheduled
Mondays 09:00 UTC — the same cadence as the Python Staleness Gate — and also
runnable on demand:

```bash
gh workflow run release-tag-hygiene.yml
```

**Why it exists:** the runbook above assumes every pushed tag produces a
release run. It doesn't always. `v5.9` never matched `release.yml`'s then-strict
`v*.*.*` glob (it's a two-component tag), and `v5.10.0` was, at the time,
tagged locally but never pushed to origin. Both incidents produced zero Actions events —
push-time checks have nothing to react to. As a result, three milestones
shipped no Windows build with zero signal that anything was wrong. This
guard runs on a schedule instead, so silence gets checked periodically
rather than trusted.

**What it checks:** every git tag matching the loose pattern `v[0-9]*` is
cross-referenced against successful `release.yml` runs and existing GitHub
Release objects. The loose pattern matches what `release.yml` now triggers on
(`v[0-9]*`) and is deliberately broader than the strict `v*.*.*` glob that
`release.yml` used before RVW-004 and `release-container.yml` still uses — that
mismatch is exactly how `v5.9` got caught instead of silently skipped.

**What red means:** one or more release-like tags exist with no successful
release run and no baseline entry. Remediation options, in priority order:

1. **Re-cut and push the tag correctly** — if the tag was malformed or never
   pushed, fix it at the source.
2. **Push the tag again so a real release run starts** — if the tag is correct
   but the release run failed or never happened. Dispatching `release.yml` by
   hand against the tag ref does not do this: that is a dry run that publishes
   nothing (step 2 of the runbook), even though the guard counts any successful
   `release.yml` run on that ref as backing the tag.
3. **Add a reviewed line to `.github/tag-hygiene-baseline.txt`** — only when
   the gap is a deliberate, dispositioned historical exception (e.g. a
   PyPI-only release), not a current failure waiting to be fixed.

**Baseline file contract:** `.github/tag-hygiene-baseline.txt` holds one
`<tag> <reason>` per line (`#` comments allowed). Adding a line is a
recorded, reviewable disposition — it must never be used to silence a
*current* release failure. The file is seeded with every tag that existed
when this guard was built, so its first scheduled run started green.

## One-Time Setup (per project, never re-run)

These steps must be completed once before the first release can publish. They
are not part of the per-release runbook.

### PyPI Trusted Publisher configuration

On PyPI (`https://pypi.org/manage/account/publishing/`), add a new pending
publisher with these exact values:

| Field                  | Value                |
| ---------------------- | -------------------- |
| PyPI project name      | `quirk-scanner`           |
| Owner                  | `0xD1g5`             |
| Repository name        | `QU.I.R.K`           |
| Workflow filename      | `release.yml`        |
| Environment name       | `release`            |

On first use, PyPI converts the "pending" publisher into a normal Trusted
Publisher.

### GitHub `release` environment

In the repository Settings → Environments, create an environment named
`release`. Optionally restrict deployment to tag pattern `v*` so the
release workflow can only run from a release tag, not from an arbitrary
branch.

### GitHub private vulnerability reporting

Private vulnerability reporting must be enabled on the repository.
`SECURITY.md` points reporters at this channel and assumes it is on. It is
enabled on `0xD1g5/QU.I.R.K`; re-check it after any repository transfer or
rename.

## Attestation Verification (for downstream consumers)

Every release is published to PyPI by the GitHub Actions workflow through
Trusted Publishers with `attestations: true`, so PyPI hosts a Sigstore-signed
provenance attestation (PEP 740) for each uploaded file. Consumers can verify
the provenance of a downloaded artifact before installing it.

### PyPI attestation path

Use PyPA's `pypi-attestations` tool. It fetches the provenance PyPI holds for
the file and checks it against the publishing repository:

```bash
pip install pypi-attestations
pypi-attestations verify pypi \
  --repository https://github.com/0xD1g5/QU.I.R.K \
  pypi:quirk_scanner-X.Y.Z-py3-none-any.whl
```

This prints `OK: quirk_scanner-X.Y.Z-py3-none-any.whl` and exits 0 on success.
Use it for the sdist too:

```bash
pypi-attestations verify pypi \
  --repository https://github.com/0xD1g5/QU.I.R.K \
  pypi:quirk_scanner-X.Y.Z.tar.gz
```

The published file names use an underscore (`quirk_scanner-`), not the
hyphenated distribution name.

`gh attestation verify` does **not** work for these files: the attestations are
stored on PyPI, not in GitHub's attestation store, so the GitHub CLI answers
`HTTP 404` for the wheel's digest. Likewise no `.sigstore` bundle is attached to
the GitHub release, so a `cosign verify-blob --bundle` flow has nothing to
verify against.

### What is deliberately NOT shipped

QU.I.R.K. does NOT ship a `curl | bash` installer (per LAUNCH-07 — this is a
deliberate non-feature). The supported install path carries verifiable
provenance:

- **PyPI** (`pip install quirk-scanner`) — Sigstore attestations via Trusted
  Publishers.

QU.I.R.K. is not distributed as a public container image or a Homebrew
formula; neither channel is offered, so do not look for one.

If you encounter instructions on a third-party site that ask you to pipe a
shell script from the internet directly into `bash` to install QU.I.R.K., do
not run them — they are not endorsed by the project.

## Container Image Build (internal, not a distribution channel)

The release pipeline builds a multi-arch container image on every `v*.*.*` tag
push, in parallel with the PyPI publish workflow. **The resulting GHCR package
is private. QU.I.R.K. does not offer a public container image**, so there is no
supported `docker pull` path for evaluators; install from PyPI instead. A
public image is a deferred item, not a promise of this document.

### Coordinates

- **Workflow:** `.github/workflows/release-container.yml`
- **Trigger:** push of a `v*.*.*` tag. Unlike `release.yml`, this trigger is
  strict, so a two-component tag does not start it.
- **Push target:** `ghcr.io/0xd1g5/quirk` (a private package), tagged `:latest`
  and `:vX.Y.Z`.
- **Platforms:** `linux/amd64`, `linux/arm64` — built via
  `docker/build-push-action` with QEMU emulation in GitHub Actions.

### How the container stays in lock-step with the PyPI wheel

The Dockerfile installs QU.I.R.K. from PyPI:

```dockerfile
RUN pip install --no-cache-dir "quirk-scanner[all]==${QUIRK_VERSION}"
```

`QUIRK_VERSION` is injected by the workflow from the triggering git tag.
Before the build runs, the workflow polls
`https://pypi.org/pypi/quirk-scanner/${version}/json` for up to 10 minutes so the
container build only proceeds once the PyPI release has propagated. The
container therefore installs the same PyPI release as `pip install quirk-scanner`
on the host — there is no parallel build path.

The image's default `CMD` is `quirk --help`.

### What this image deliberately does NOT include

- **`playwright` browsers** — `quirk-scanner[all]` installs the `playwright`
  package (through its `dashboard` extra), but no browser binaries are installed
  in the image, to keep it lean.
- **Distroless / Alpine variants** — `python:3.11-slim` is the only base image.

---

## curl | bash Non-Decision (LAUNCH-07)

**Decision (anti-feature):** QU.I.R.K. deliberately does not ship a `curl <url> | bash`
installer, and never will. This is a permanent security posture, not a backlog item
deferred for later.

### Rationale

Piping HTTP responses directly to a shell defeats the integrity guarantees that the
rest of the release pipeline is built around:

- **Sigstore attestations end at the wheel/sdist.** The PyPI Trusted Publisher OIDC
  workflow (`.github/workflows/release.yml`) signs the artifact bytes. A
  `curl … | bash` trampoline introduces an untrusted intermediary shell script
  that the attestation chain does not cover — the user has no way to verify that
  the script they execute is the script we published, and even if it is, the script
  itself can fetch arbitrary downstream artifacts without further attestation.
- **No attestation verification step is possible.** The supported install path
  funnels through artifacts that are verifiable post-fetch and pre-execute. A
  bash trampoline executes as it streams; verification after the fact is
  meaningless.
- **Defense against TLS-stripping / DNS-hijack scenarios.** A compromised mirror,
  a typosquatted host, or an attacker positioned to MITM HTTPS (for example via a
  rogue CA in a managed device) can substitute their script. `pip install` can
  pin each artifact to a known hash with `--require-hashes`, and the PyPI
  attestation described above ties a file to the repository that built it.
  `curl | bash` verifies nothing.
- **No incident-response surface.** If a `curl | bash` script is found
  compromised, every machine that ever ran it is potentially in scope; there is
  no version pinning, no rollback narrative, no `pip uninstall` story. The
  supported install path leaves a recoverable inventory.

### Supported install path

Use:

- **`pip install quirk-scanner[all]`** — PyPI, published with Trusted
  Publishers and PyPI-hosted Sigstore attestations (verify with
  `pypi-attestations`; see the *Attestation Verification* section above).

### For consumers who need automated provisioning

The right pattern is to wrap the supported install command in your existing
configuration-management tooling — Ansible, Chef, Salt, Puppet, or a plain
shell script you author and review locally — pin an explicit version, and run
`pypi-attestations verify pypi` as a first-class step of the playbook.

This preserves the attestation chain end-to-end; a `curl … | bash` trampoline
cannot.

### Status

**Permanent.** This is not revisited on later milestones; `curl | bash` is an
anti-feature for a security tool — never. Any future contributor proposing a
`curl … | bash` installer should be pointed at this section before any code is
written.
