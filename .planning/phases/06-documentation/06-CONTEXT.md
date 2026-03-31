# Phase 6: Documentation - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce the complete guide suite that enables a consultant with zero QU.I.R.K. experience to
install the tool, run a scan, and explain the report to a client — entirely from the docs.

Scope: Getting Started, installation, configuration, connector guides (AWS, Azure, Docker, Git),
report interpretation, CBOM guide, chaos lab operator guide.

No new scanners, no UI changes, no packaging changes (Phase 7). Documentation only.

</domain>

<decisions>
## Implementation Decisions

### Doc Home and Navigation (DOC-01..07)
- **D-01:** Create `docs/` folder at repo root with one Markdown file per guide. Structure:
  ```
  docs/
    getting-started.md
    installation.md
    configuration.md
    connectors/
      aws.md
      azure.md
      docker.md
      git.md
    report-interpretation.md
    cbom-guide.md
    chaos-lab.md
  ```
- **D-02:** Update `README.md` as a clean product intro with links into `docs/`. Current README
  is severely stale (still says "qcscan", "Quantum Crypto Scanner", pre-Phase 1 MVP content) —
  it must be fully replaced. README = product intro + Quick Start snippet + links to full docs.
- **D-03:** Plain Markdown, no build step. Works on GitHub, readable offline, works for
  air-gapped engagements. Phase 7 can layer a MkDocs/Material skin on top without restructuring.

### Getting Started Install Path (DOC-01, DOC-02)
- **D-04:** Primary path is the development install (works today):
  ```bash
  git clone ...
  cd quirk
  python -m venv .venv && source .venv/bin/activate
  pip install -e '.[dashboard]'
  playwright install chromium   # for PDF export
  quirk --help
  ```
- **D-05:** Add a callout box with the future PyPI path:
  ```
  > **Note (coming in v4.0):** Once published to PyPI:
  > pip install 'quirk[dashboard]'
  ```
  Phase 7 removes the callout and promotes pip install to the primary path.
- **D-06:** Getting Started must achieve < 10 min from clean macOS or Linux (DOC-01 success
  criterion). Cover: Python 3.10+ check, venv creation, install, config.yaml minimal setup
  (127.0.0.1 target), first scan, `quirk serve`, open browser.
- **D-07:** Windows WSL covered in `installation.md` (separate section, not the Getting Started
  main path). macOS and Linux are primary.

### Report Interpretation Guide (DOC-05)
- **D-08:** Two-layer structure:
  1. **Reference table** — maps every score band (0-40/41-70/71-90/91-100), severity tier
     (CRITICAL/HIGH/MEDIUM/LOW/INFO), and finding type to a plain-English definition.
  2. **"Client Conversation" sidebox** for each major section — suggested language for when a
     client asks "what does this mean for us?" in a live meeting.
  Example sideboxes: quantum-readiness score, severity breakdown, CBOM components, migration
  roadmap, certificate expiry findings.
- **D-09:** Source score labels and thresholds from `quirk/intelligence/scoring.py` (the 4
  subscore model: Hygiene, Modern TLS, Identity, Agility). Severity thresholds from
  `quirk/engine/` risk rules.

### CBOM Guide (DOC-06)
- **D-10:** Three sections: (1) what a CBOM is and why it exists (plain English for compliance
  officers), (2) how QU.I.R.K. produces the CBOM (algorithms → CycloneDX components → quantum
  safety classification), (3) how to cite the CBOM as compliance evidence (NIST SP 800-208,
  CNSA 2.0 mappings, example audit language).

### Connector Setup Guides (DOC-04)
- **D-11:** AWS guide includes:
  - Copy-pasteable least-privilege IAM policy JSON (read-only ACM + KMS + CloudFront + ELBv2)
  - `config.yaml` snippet showing `enable_aws: true` + credential setup
  - boto3 credential chain explanation (env vars, ~/.aws/credentials, IAM role)
- **D-12:** Azure guide includes:
  - RBAC role definition (Reader + Key Vault Reader + Network Reader scoped to subscription)
  - `config.yaml` snippet showing `enable_azure: true` + service principal setup
  - Environment variable list (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET)
- **D-13:** Docker connector guide covers: Docker socket access, Syft installation requirement,
  scan target config. Git connector guide covers: Gitea/GitHub access, semgrep dependency.

### Chaos Lab Operator Guide (DOC-07)
- **D-14:** Write new `docs/chaos-lab.md` as the canonical operator guide covering ALL profiles:
  - Core (always-on): 10 services
  - phaseA / cloud / identity / pki (original profiles)
  - jwt (Phase 4): 4 FastAPI JWT microservices on ports 20001-20004
  - registry (Phase 4): Docker Registry v2 + 3 test images on port 20005
  - source (Phase 4): Gitea + seeded repos on port 20006
  - storage (Phase 4): LocalStack KMS (port 20007) + HashiCorp Vault (port 20008)
  - ssh-weak (Phase 4): OpenSSH on port 20022 (ubuntu:18.04, legacy algorithms)
  - ldaps (Phase 4): OpenLDAP on port 636
- **D-15:** Existing `quantum-chaos-enterprise-lab/CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md`
  stays as a historical artifact in the lab directory. New `docs/chaos-lab.md` is the
  authoritative reference going forward. Update chaos lab README.md to link to `docs/chaos-lab.md`.
- **D-16:** `docs/chaos-lab.md` includes `expected_results_v3.md` summary inline — port matrix
  for all profiles so an operator knows what findings to expect per scanner type.

### Configuration Reference (DOC-03)
- **D-17:** Document every top-level key in `config.yaml`: assessment, scan, targets, connectors,
  output, intelligence. Include: default values, valid range, what changes with each scan profile
  (quick/standard/deep), which fields are required vs optional.
- **D-18:** Include CLI flag reference from `run_scan.py` argparse: at minimum `--config`,
  `--profile`, `--targets`. `quirk serve` flags: `--port`, `--no-open`.

### Claude's Discretion
- Exact Markdown formatting, heading hierarchy, and code block style within each guide
- Whether connectors subdirectory uses individual files or a single `connectors.md`
- Ordering of topics within the configuration reference
- Specific IAM policy JSON (derive from what connectors actually call in quirk/connectors/)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scoring and intelligence (for report interpretation guide)
- `quirk/intelligence/scoring.py` — compute_readiness_score() — 4 subscore model, score fields, thresholds
- `quirk/intelligence/confidence.py` — compute_confidence() — confidence rating bands
- `quirk/intelligence/roadmap.py` — build_phased_roadmap() — migration roadmap structure
- `quirk/engine/` — risk rules and severity tiers (findings definitions)

### CBOM pipeline (for CBOM guide)
- `quirk/cbom/classifier.py` — classify_algorithm(), quantum_safety_label() — safety labels and NIST level
- `quirk/cbom/builder.py` — build_cbom() — how algorithms become CycloneDX components

### Connectors (for connector setup guides and IAM policy derivation)
- `quirk/connectors/aws.py` — scan_aws_targets() — exact boto3 API calls, determines least-privilege policy
- `quirk/connectors/azure.py` — scan_azure_targets() — exact azure-sdk calls, determines RBAC permissions
- `quirk/connectors/docker.py` — container scanner implementation (syft dependency)
- `quirk/connectors/git.py` — source code scanner implementation (semgrep dependency)

### Configuration (for config reference)
- `config.yaml` — current config file (all top-level keys, defaults)
- `quirk/config.py` — ConnectorsCfg dataclass and config structure
- `run_scan.py` — argparse definitions (CLI flags)

### Chaos lab (for operator guide)
- `quantum-chaos-enterprise-lab/docker-compose.yml` — all service definitions, profiles, ports
- `quantum-chaos-enterprise-lab/expected_results_v3.md` — per-port expected findings oracle
- `quantum-chaos-enterprise-lab/CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md` — existing narrative (historical context)

### Requirements
- `.planning/REQUIREMENTS.md` §DOC — DOC-01 through DOC-07 definitions and success criteria
- `.planning/ROADMAP.md` §Phase 6 — Success criteria (6 criteria to pass)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/cbom/classifier.py` — quantum_safety_label() returns Safe/At Risk/Vulnerable — use these labels verbatim in report interpretation guide
- `quirk/intelligence/scoring.py` — score band definitions (must be read to get exact thresholds for reference table)
- `quantum-chaos-enterprise-lab/expected_results_v3.md` — port matrix and finding tags — inline into chaos-lab.md

### Established Patterns
- Tool is Python-native, pip-installable, agentless-by-default
- Optional dependencies: `pip install 'quirk[dashboard]'` for web UI + PDF export
- `playwright install chromium` is a one-time step required after dashboard install
- Config via `config.yaml` in working directory (all knobs exposed there)
- `quirk serve` starts uvicorn on localhost:8512 with auto-browser-open

### Integration Points
- `README.md` at repo root — must be replaced (stale qcscan content)
- `quantum-chaos-enterprise-lab/README.md` — needs a link update to point to `docs/chaos-lab.md`
- `pyproject.toml` — `quirk = "run_scan:main"` entry point; `[dashboard]` optional group

</code_context>

<specifics>
## Specific Ideas

- Getting Started: < 10 min, macOS/Linux primary, 127.0.0.1 as default first-scan target
- Install guide: both paths — git clone + pip install -e . (primary, works today) AND pip install
  callout for PyPI (Phase 7, forward-looking note)
- Report interpretation: reference table + "Client Conversation" sidebox per section — format
  designed for use in a live client meeting, not just offline reading
- CBOM guide: three sections — what it is, how QU.I.R.K. produces it, how to cite it as
  compliance evidence (NIST SP 800-208, CNSA 2.0 audit language)
- Chaos lab: new `docs/chaos-lab.md` covering all profiles including Phase 4; existing
  CHAOS_LAB_BUILD_AND_OPERATIONS file stays as historical artifact

</specifics>

<deferred>
## Deferred Ideas

- **Full narrative onboarding guide** — User wants a prose walkthrough of a complete report from
  first scan to client delivery, designed as a training document for bringing new team members
  into the project. Not a quick reference — a story-format guide. Captured for backlog.
  Note from user: "would be a good training tool for bringing new team members into the project."

</deferred>

---

*Phase: 06-documentation*
*Context gathered: 2026-03-31*
