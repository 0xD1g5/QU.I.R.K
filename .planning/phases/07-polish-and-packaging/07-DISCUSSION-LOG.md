# Phase 7: Polish and Packaging - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 07-polish-and-packaging
**Areas discussed:** Visual Identity, CLI UX, Report HTML/PDF scope, Distribution, Dashboard Branding, Versioning, Report Data Model

---

## Visual Identity

| Option | Description | Selected |
|--------|-------------|----------|
| Styled wordmark only | Typography-based treatment, no illustrative icon | ✓ |
| Icon + wordmark | Geometric/abstract icon alongside wordmark | |
| You decide | Claude picks treatment | |

**User's choice:** Styled wordmark only
**Notes:** QU.I.R.K. in monospace/tech font with electric-blue accent

---

## Color Palette

| Option | Description | Selected |
|--------|-------------|----------|
| Dark + cyber-amber | Dark backgrounds with amber/gold accent | |
| Dark + electric blue | Navy/slate base with bright blue accent | ✓ |
| You decide | Claude picks palette | |

**User's choice:** Dark + electric blue
**Notes:** "Classic enterprise security look (Splunk, Elastic vibes)"

---

## Branding Surfaces

| Option | Description | Selected |
|--------|-------------|----------|
| Report headers (HTML/PDF) | Wordmark + color accent at top of reports | ✓ |
| Dashboard navbar/favicon | Replace generic title in React dashboard | ✓ |
| CLI startup banner | ASCII/styled banner on quirk scan/serve | ✓ |
| All of the above | Consistent identity across all surfaces | ✓ |

**User's choice:** All surfaces
**Notes:** Full surface coverage — consistent identity across CLI, reports, and dashboard

---

## CLI UX — Progress Indicators

| Option | Description | Selected |
|--------|-------------|----------|
| Add `rich` library | Full rich treatment: progress bars, colored output, styled tables | ✓ |
| Stick with tqdm + ANSI | Keep tqdm, add colorama. No new heavy deps | |
| Rich but optional | Rich in optional extra only | |

**User's choice:** Add `rich` library as core dependency

---

## CLI UX — Output Formatting

| Option | Description | Selected |
|--------|-------------|----------|
| Structured scan summary table | Final summary table after every scan | |
| Rich logging throughout | Replace all Logger calls with rich-formatted output | |
| Both | Rich throughout + final summary table | ✓ |

**User's choice:** Both — rich throughout + final summary table

---

## Report HTML/PDF Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone HTML report | New Jinja2 template in write_reports(), offline-capable | ✓ |
| Brand dashboard PDF only | Apply branding to existing dashboard Playwright path | |
| Both | Standalone HTML + branded dashboard PDF | |

**User's choice:** Standalone HTML report
**Preview confirmed:** scan → report.md (keep) + report.html (new) + report.pdf (new) + cbom.cdx.json (keep)

---

## Report Sections

| Option | Description | Selected |
|--------|-------------|----------|
| Executive summary only | Score gauges, severity, findings, roadmap, CBOM summary | |
| Full technical + executive | Executive + full technical appendix (endpoints, cert inventory) | ✓ |
| You decide | Claude picks structure | |

**User's choice:** Full technical + executive — single scrollable file

---

## Distribution Target

| Option | Description | Selected |
|--------|-------------|----------|
| GitHub-based install | pip install git+... — no PyPI, no name conflict | ✓ |
| Public PyPI | Publish to PyPI as 'quirk' | |
| Private / local install only | git clone + pip install -e . stays as-is | |

**User's choice:** GitHub-based install for now

---

## Sample Config

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — ship default config.yaml | `quirk init` generates config.yaml from bundled template | ✓ |
| No — docs are enough | Phase 6 getting-started covers config setup | |

**User's choice:** Yes — `quirk init` subcommand generates config.yaml

---

## Dashboard Branding

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal — navbar + favicon only | Update navbar title, favicon, apply accent to theme tokens | |
| Full theme pass | Audit every shadcn/ui component color, update palette | ✓ |
| Skip — dashboard branding is Phase 8 | Standalone report is primary consulting deliverable | |

**User's choice:** Full theme pass

---

## Versioning

| Option | Description | Selected |
|--------|-------------|----------|
| Manual version bump + git tag | Edit pyproject.toml + __init__.py, commit, tag v4.0.0 | ✓ |
| bump2version | Automate version file updates via bump2version | |
| No change needed | Stay at 3.9.0 through Phase 7 | |

**User's choice:** Manual version bump + git tag v4.0.0

---

## Report Data Model

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse existing builders | executive.py + technical.py data dicts feed Jinja2 renderer | ✓ |
| Refactor to shared data model | Extract clean dataclass for both Markdown and HTML renderers | |
| You decide | Claude picks minimum-churn approach | |

**User's choice:** Reuse existing builders — no refactor of data assembly

---

## Claude's Discretion

- Jinja2 template layout details (section ordering, table styling, fonts)
- Rich theme/style specifics (exact colors, spinner style)
- ASCII banner art style and dimensions
- Playwright PDF page size and margins

## Deferred Ideas

- MkDocs/Material skin — out of scope, plain Markdown stays
- PyPI publication — post-Phase 7
- CHANGELOG / semantic-release tooling — manual version bump only
