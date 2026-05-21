# Phase 85: Public-Launch Polish - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous batch, all defaults accepted)

<domain>
## Phase Boundary

Installing and evaluating QU.I.R.K. is frictionless for a security consultant encountering the project for the first time. Deliverables: marketing-grade README at repo root, Homebrew tap formula, multi-arch GHCR Docker image, upgrade guide for v4.x→v4.10, sample CBOM JSON fixtures under `examples/`, and an explicit `curl|bash` non-decision in `docs/release-process.md`. The scope is packaging/marketing polish on top of Phase 84's release pipeline; no new scanner capability, no schema change, no dashboard work.

Out of scope (deferred): Homebrew core submission, multi-distro Linux packages (apt/rpm), Windows MSI, marketing landing page, video walkthrough beyond the animated demo asset link.

</domain>

<decisions>
## Implementation Decisions

### Distribution Namespaces
- **GitHub org/user:** `0xD1g5` (from existing repo URL `https://github.com/0xD1g5/QU.I.R.K.`)
- **Homebrew tap repo:** `0xD1g5/homebrew-quirk` (separate tap repo per LAUNCH-02 — not homebrew-core). Install path: `brew install 0xD1g5/quirk/quirk`.
- **GHCR image:** `ghcr.io/0xd1g5/quirk` (GHCR namespaces are lowercase). Tag `:latest` plus `:vX.Y.Z`. Multi-arch (`linux/amd64` + `linux/arm64`).
- **PyPI distribution:** `qu-i-r-k` (locked in Phase 84 decision v4.10-D-02). All install instructions use `pip install qu-i-r-k[all]`.

### Docker Base Image
- **Base:** `python:3.11-slim` (Debian slim, glibc). Reason: full compatibility with `cryptography` wheels and other binary extensions QU.I.R.K. depends on (nmap subprocess, playwright optional); `alpine` has known musl/cryptography friction; distroless eliminates `--help` debugging affordances for first-run users.
- **Multi-arch build:** GitHub Actions `docker/build-push-action@v6` with `platforms: linux/amd64,linux/arm64` and QEMU setup. Image published from a tag-triggered workflow that runs after the PyPI publish job in `.github/workflows/release.yml` (84-03 added the PyPI job; this phase adds a downstream container job — same workflow file or a new `release-container.yml`, planner's choice).
- **Default CMD:** `quirk --help` so `docker run ghcr.io/0xd1g5/quirk:latest` is informative for first-time evaluation.

### Sample CBOM Fixtures
- **Source:** Generate by running the QU.I.R.K. scanner against the existing chaos lab profiles, not hand-crafted. Use deterministic seed where the scanner supports it; if randomness in serial numbers / UUIDs leaks into output, post-process with `jq` to normalize.
- **Profiles to cover:**
  - **TLS-only** — `tls-weak` profile (legacy ciphersuites, sub-2048 keys)
  - **Identity** — `smime` + `adcs` profiles combined (S/MIME LDAP discovery + AD CS templates)
  - **Data-at-rest** — `dar-database` profile (postgres at-rest crypto)
  - **Data-in-motion** — `tls-weak` + `email` + `broker` profiles combined (TLS + SMTP STARTTLS + AMQP)
- **Storage:** `examples/cbom/` with one `.cbom.json` per profile, named `{profile}.cbom.json`. Pretty-printed for diffability.

### Upgrade Guide Scope
- **Coverage:** v4.x → v4.10 generic (single guide). Justification: REQUIREMENTS.md states schema changes are additive-only across v4.x, so the upgrade is uniform regardless of starting minor — `quirk db migrate` is a no-op on already-current columns and adds any missing additive columns.
- **Structure:** Pre-upgrade checklist → `pip install -U qu-i-r-k` → `quirk db migrate --dry-run` → `quirk db migrate` → verify → rollback note (restore from backup; no in-tool rollback).
- **`quirk db migrate` command:** Net-new CLI subcommand if not already present (RESEARCH check). Idempotent — reports each column as `already-present` or `added`; exits 0 either way; never destructive.

### README Marketing Polish
- **Approach:** Augment, do not rewrite. Existing README has good bones (overview, quickstart, doc table). Phase 85 layers on:
  - **Badge row** above title: CI status, PyPI version, license, Sigstore attestation badge, security policy link
  - **Persona triptych** (3 short paragraphs after value-prop intro): "For the security consultant" / "For the IT generalist" / "For the compliance officer"
  - **Dashboard screenshot** (1 hero image) — captured from a running dashboard against `tls-weak` chaos lab profile; stored at `docs/images/dashboard-hero.png`
  - **Animated demo asset link** — record an asciinema or terminal GIF of `quirk run` against `tls-weak`; link from README, do not embed (keeps clone size small)
  - **3-command quickstart** updated to: `pip install qu-i-r-k[all]` → `quirk init` → `quirk run --config quirk.yaml`. Replace the `git clone` quickstart (move it under a "Develop from source" collapsed section).

### Claude's Discretion
- Exact wording of persona paragraphs, screenshot composition, asciinema script choice, badge SVG providers (shields.io etc.), upgrade-guide tone.
- Whether to add a single-file `.cbom.json` or separate JSON-pretty + JSON-min variants per profile.
- Whether Docker build runs in `release.yml` or a new `release-container.yml` workflow (decided in planning).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk` CLI entrypoint via `pyproject.toml [project.scripts]` (already wired, used by Phase 84 release workflow).
- `chaos-lab/` (or `quantum-chaos-enterprise-lab/` per CLAUDE.md) with `lab.sh` profile orchestrator — directly drives sample CBOM generation.
- `docs/` already has Getting Started, Installation, Configuration Reference, Connector Guides, Report Interpretation, CBOM Guide, Chaos Lab Operator Guide. `upgrade-guide.md` is the new addition.
- `docs/release-process.md` (Phase 84) — add the `curl|bash` non-decision section here per LAUNCH-07.
- `.github/workflows/release.yml` (Phase 84) — extend or pair with a sibling workflow for the container build.
- React dashboard at `src/dashboard/` (pre-built statics served by FastAPI) — screenshot target.

### Established Patterns
- README uses markdown tables for doc navigation — keep the pattern; add a "Quickstart paths" table for `pip` vs `brew` vs `docker`.
- All docs live under `docs/` and are mirrored to Obsidian vault per CLAUDE.md sync workflow — `upgrade-guide.md` follows the same pattern.
- Multi-arch container builds in this codebase: none existing; new pattern.
- CBOM output: `quirk run --output <path>` writes CycloneDX JSON; deterministic mode unconfirmed (planner to verify).

### Integration Points
- Tag-triggered GHCR push hooks into the existing release.yml (Phase 84) or a sibling release-container.yml.
- Homebrew tap is a separate repo (`0xD1g5/homebrew-quirk`); this phase produces the formula content + commit instructions, the actual tap-repo creation is a manual one-time step documented in release-process.md.
- The animated demo asset (asciinema) lives outside the repo (asciinema.org link) — no binary in-tree.

</code_context>

<specifics>
## Specific Ideas

- The persona triptych should mirror the "three personas" framing already used in the project (security consultant, IT generalist, compliance officer per LAUNCH-01 wording).
- Screenshot should show a real scan result, not a placeholder — the `tls-weak` profile produces visibly weak findings that motivate the value prop.
- Homebrew formula must use `pipx`-style isolation (per LAUNCH-02 success criterion) — investigate `brew-pip-resource` patterns vs `language/python` Formula DSL.
- The `curl|bash` non-decision in `docs/release-process.md` is a *security posture* statement — frame it as "we deliberately do not ship a curl-piped installer because piping HTTP to bash defeats the integrity guarantees of Sigstore attestations + Trusted Publishers; install via pip / brew / docker only".

</specifics>

<deferred>
## Deferred Ideas

- Homebrew core submission (after first community uptake; out of scope for v4.10).
- Multi-distro Linux packages (apt/rpm) — backlog.
- Windows MSI installer — backlog (no current Windows user demand).
- Marketing landing page on GitHub Pages — backlog (README is the landing page for v4.10).
- Long-form video walkthrough — backlog (the asciinema demo is the v4.10 deliverable).
- `quirk doctor` first-run sanity check command — backlog candidate for v4.11.

</deferred>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 85 goal + 5 success criteria
- `.planning/REQUIREMENTS.md` — LAUNCH-01..07 detailed acceptance criteria
- `docs/release-process.md` — Phase 84 deliverable; Phase 85 amends with LAUNCH-07 non-decision section
- `.github/workflows/release.yml` — Phase 84 PyPI publish workflow; Phase 85 extends with container build
- `pyproject.toml` — version SoT (Phase 84); distribution name `qu-i-r-k` (Phase 84 D-02)
- `CLAUDE.md` — Obsidian vault sync workflow for `docs/upgrade-guide.md`
- `README.md` — current root README (augment, do not rewrite)
- `quantum-chaos-enterprise-lab/` (or `chaos-lab/`) — source of CBOM fixture generation; profiles `tls-weak`, `smime`, `adcs`, `dar-database`, `email`, `broker`

</canonical_refs>
