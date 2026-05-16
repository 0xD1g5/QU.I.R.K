# Phase 84: Release Engineering - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

QU.I.R.K. has a signed, attestable release pipeline:
- PyPI distribution name confirmed (`quirk` if available; `qu-i-r-k` fallback)
- GitHub Actions Trusted Publishers configured (no stored API tokens)
- Sigstore attestations automatic via PyPA publisher action
- CHANGELOG automation via `towncrier` with per-PR fragments under `changelog.d/`
- Single canonical version source of truth (pyproject.toml + dynamic `__version__`)
- Public-facing governance docs published: `SECURITY.md`, `CODE_OF_CONDUCT.md`, `docs/release-process.md`

Wave B — depends on Phase 83 (integration gate green).

</domain>

<canonical_refs>
- `.planning/REQUIREMENTS.md` — RELENG-01..RELENG-08 verbatim
- `.planning/ROADMAP.md` — Phase 84 (5 success criteria — verify in roadmap)
- `pyproject.toml` — current version + package metadata
- `quirk/__init__.py` — current `__version__` location
- `tests/test_version.py` — Phase 37 invariant enforcing version parity across 6 surfaces
- `.github/workflows/` — existing CI workflows
- `docs/release-notes/4.4.0.md` — existing release-notes format (Phase 37)

</canonical_refs>

<decisions>
## Implementation Decisions

### Area 1 — PyPI distribution name
- **`quirk` if available, fallback to `qu-i-r-k`.** RELENG-01 task: `pip index versions quirk` check. If unavailable, switch to `qu-i-r-k` and log v4.10-D-NN decision before any release commits land. README badges, install commands, Trusted Publishers config all derive from the chosen name.

### Area 2 — CHANGELOG automation
- **Per-PR fragments under `changelog.d/`** (modern towncrier convention; not `news/` from REQUIREMENTS RELENG-04 wording). Each PR drops `changelog.d/<issue_or_pr>.<kind>.md` (kinds: feature, bugfix, doc, removal, misc).
- `towncrier build` consumes fragments and prepends to `CHANGELOG.md` at release time; fragments are removed via towncrier's `--remove` flag.

### Area 3 — Version source of truth (D-84-R1: REVERSES RELENG-08 WORDING)
- **`pyproject.toml [project.version]` is the canonical source.** `quirk/__init__.py::__version__` is DERIVED via `importlib.metadata.version("quirk")`. Modern Python packaging best practice (PEP 621 + importlib.metadata is the recommended pattern as of 2024+).
- RELENG-08 wording says `__init__.py` is canonical and pyproject derives — this is the legacy pattern. Honor the user's decision (modern direction).
- `tests/test_version.py` (Phase 37) is updated to enforce parity in the new direction: `pyproject.toml` value is the truth, all other surfaces equal that.
- Six derived surfaces per Phase 37: pyproject.toml (SoT), `quirk/__init__.py::__version__`, CLI banner, dashboard footer, CBOM metadata, CHANGELOG.md heading.

### Area 4 — Trusted Publishers + attestations
- **GHA OIDC + `pypa/gh-action-pypi-publish`** in `.github/workflows/release.yml`. Trusted Publishers config at PyPI side: project name + workflow filename + environment name (e.g., `release`).
- Sigstore attestations: `attestations: true` flag on the publisher action — keyless, automatic, no secrets management.
- `docs/release-process.md` documents the attestation verification command for downstream consumers (e.g., `gh attestation verify` or `cosign verify-blob`).

### Cross-cutting
- `SECURITY.md` at repo root — 90-day vuln disclosure SLA, GitHub private vulnerability reporting enabled, point of contact, scope statement.
- `CODE_OF_CONDUCT.md` at repo root — Contributor Covenant v2.1 (canonical).
- `docs/release-process.md` — version policy (semver commitments, EOL cadence, what triggers major/minor/patch) + step-by-step release runbook + attestation verification.

</decisions>

<code_context>
### Reusable assets
- `tests/test_version.py` (Phase 37) — 6-surface parity test (to be updated for new SoT direction)
- `docs/release-notes/4.4.0.md` — existing release-notes shape (Phase 37); towncrier may need to be configured to produce something compatible

### Established patterns
- Markdown docs under `docs/`
- GitHub Actions workflows under `.github/workflows/`
- pyproject.toml is already the build-system source (PEP 621)

### Integration points
- `pyproject.toml` — version source + towncrier config (`[tool.towncrier]` block)
- `quirk/__init__.py` — replace literal `__version__ = "..."` with `__version__ = importlib.metadata.version("quirk")`
- `tests/test_version.py` — flip SoT direction (assert all surfaces == pyproject.toml value)
- `.github/workflows/release.yml` — NEW; tag-triggered build + publish + attestation
- `.github/workflows/changelog-fragment-check.yml` — NEW (optional); PR check that asserts each non-trivial PR carries a `changelog.d/` fragment
- `SECURITY.md` — NEW (root)
- `CODE_OF_CONDUCT.md` — NEW (root)
- `docs/release-process.md` — NEW
- `changelog.d/` — NEW directory + `.gitkeep` + README explaining fragment format
- `CHANGELOG.md` — already exists from Phase 37; towncrier prepends to it
- `pyproject.toml` deps — towncrier as dev dep

</code_context>

<specifics>
- towncrier config block: `[tool.towncrier]` with `package = "quirk"`, `directory = "changelog.d"`, `filename = "CHANGELOG.md"`, sections for feature/bugfix/doc/removal/misc
- Trusted Publishers config to be done manually at PyPI side AFTER the workflow file is committed and the v4.10.0 tag exists (the publisher action errors with a clear message if not configured); document the manual step in release-process.md
- SECURITY.md vuln disclosure SLA: 90 days standard; coordinated disclosure via GitHub private vulnerability reporting
- CODE_OF_CONDUCT.md: Contributor Covenant v2.1 verbatim with project-specific contact at the end

</specifics>

<deferred>
- Automated changelog-fragment-check workflow — nice-to-have; skip if scope is tight
- Cosign blob signing for non-PyPI artifacts (Docker image in Phase 85) — Phase 85 scope

</deferred>
