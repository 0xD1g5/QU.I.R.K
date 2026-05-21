# Security Policy

QU.I.R.K. (Quantum Infrastructure Readiness Kit) is a security-adjacent tool — it
scans for cryptographic posture in production-bearing environments. We take
vulnerability reports against the scanner itself seriously and resolve them on a
coordinated-disclosure timeline.

## Reporting a Vulnerability

**Preferred channel — GitHub private vulnerability reporting:**

Open a confidential advisory at
`https://github.com/<owner>/<repo>/security/advisories/new`.

This is the canonical contact channel. It keeps the report encrypted in transit,
gives us audit history, and lets us coordinate the fix + disclosure with you
inside the repository.

**Do NOT use public GitHub Issues to report a vulnerability.** Public issues
become indexed and searchable the moment they are filed, which would expose
unpatched users to the disclosed weakness. Public issues should only be used as
a triage-only fallback for non-sensitive metadata (e.g., asking us to enable
private reporting if it appears off) — never for vulnerability details, repro
steps, exploitation primitives, or affected versions.

We do not publish a personal email address for security contact. GitHub-native
private reporting is the only supported intake channel for vulnerability
reports.

## Disclosure Policy

We follow a **90-day coordinated disclosure** SLA, measured from the date we
acknowledge receipt of the report (not from the report-submission date):

- **Day 0:** We acknowledge the report within 5 business days.
- **Day 0 — Day 90:** We investigate, develop a fix, and prepare a coordinated
  release.
- **Day 90:** If a fix has not yet shipped, we coordinate with the reporter on
  either (a) a brief extension if remediation is actively in progress and the
  reporter agrees, or (b) public disclosure on the original 90-day timeline.

Reporters are credited by name (or pseudonym, or anonymously — your choice) in
the release notes for the fix release. Opt-out is honored without question.

## Scope

### In-scope vulnerabilities

The following classes of vulnerability are in-scope and will be triaged on the
90-day SLA:

- **Scanner output integrity** — bugs that cause the scanner to omit, suppress,
  or misclassify findings in a way that could hide a real quantum-readiness gap
  (e.g., CBOM tampering paths, finding-suppression logic errors, score
  arithmetic regressions).
- **Dashboard authentication/authorization bypass** — any path that grants
  read or write access to scan output, scan history, or configuration without
  passing the dashboard's auth gate.
- **Remote code execution** in any scanner code path, including via crafted
  inputs (malicious certificates, deliberately malformed CBOMs, JWTs designed
  to abuse a parser, etc.).
- **Secret leakage via scan output** — bugs that cause scan output to embed
  private key material, credentials, or other sensitive plaintext that the
  scanner observed during discovery.
- **Dependency-chain compromise** — issues with how we pin, install, or verify
  upstream dependencies that could allow a malicious package to be substituted
  into a QU.I.R.K. install.

### Out-of-scope

- **Chaos lab containers** (`quantum-chaos-enterprise-lab/`) are deliberately
  misconfigured fixtures. They exist to give the scanner something to find.
  Reports of "this container has weak crypto" or "this container exposes a
  vulnerable port" against the chaos lab are not security vulnerabilities —
  they are working as designed.
- **Dev-mode bypass paths** that are explicitly documented in code as
  development-only conveniences (e.g., `--unsafe-no-auth` style local flags)
  are out of scope. If you believe a dev-mode bypass is reachable in a
  production install, that IS in scope — file it.
- **Vulnerabilities requiring local filesystem access at scanner-user
  privilege level** (e.g., "if I can write to `~/.quirk/config.yaml` I can
  cause the scanner to do X"). These are equivalent to "I am already the
  user" and do not represent a security boundary the scanner protects.

## Sigstore Attestations

Every QU.I.R.K. release published to PyPI ships with Sigstore attestations
generated automatically by the GitHub Actions release workflow via
keyless OIDC signing. Downstream consumers can verify provenance before
install — see [`docs/release-process.md`](docs/release-process.md) for the
exact `gh attestation verify` and `cosign verify-blob` commands.

If you discover a release whose Sigstore attestation does NOT verify against
the expected GitHub Actions workflow identity, treat that as a high-severity
in-scope report and use the GitHub private vulnerability reporting channel
above.

## Supported Versions

The latest minor release line receives security fixes. The previous minor
release line receives security-only fixes for 6 months after the next minor
ships. Older lines do not receive fixes.

For the canonical version policy (semver commitments, EOL cadence, bump
triggers) see [`docs/release-process.md`](docs/release-process.md).
