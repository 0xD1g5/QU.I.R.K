# Phase 6: Documentation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-03-31
**Phase:** 06-documentation
**Mode:** discuss
**Areas discussed:** Doc Home & Navigation, Getting Started Install Path, Report Interpretation Depth, Chaos Lab Guide Strategy

## Gray Areas Presented

| Area | Options Offered |
|------|----------------|
| Doc home & navigation | `docs/` + README hub (rec.), MkDocs/Material site, README-centric |
| Getting Started install path | Repo clone + pip install -e . (rec.), PyPI forward-looking stub, Both paths with callout |
| Report interpretation depth | Reference card + client talking points (rec.), Pure reference card, Full narrative guide |
| Chaos lab guide strategy | Regenerate as `docs/chaos-lab.md` (rec.), Update existing in place, Lab-local + Phase 4 appendix |

## Decisions Made

### Doc Home & Navigation
- **Chosen:** `docs/` folder + updated README
- **Rationale:** Plain Markdown, no build step, works offline, GitHub-browseable, Phase 7 can layer MkDocs skin
- **Structure:** `docs/getting-started.md`, `docs/installation.md`, `docs/configuration.md`, `docs/connectors/aws.md|azure.md|docker.md|git.md`, `docs/report-interpretation.md`, `docs/cbom-guide.md`, `docs/chaos-lab.md`
- **README overhaul:** Confirmed — current README is stale (qcscan branding). Replace with product intro + Quick Start + links to docs/

### Getting Started Install Path
- **Chosen:** Both paths with a callout
- **Primary path:** git clone + pip install -e '.[dashboard]' (works today)
- **Callout:** "Coming in v4.0 (Phase 7): pip install 'quirk[dashboard]'"
- **Rationale:** Documents current reality AND sets expectation for pip install

### Report Interpretation Depth
- **Chosen:** Reference card + client talking points
- **Format:** Quick reference table (score bands, severity tiers, finding types) + "Client Conversation" sideboxes per section
- **Designed for:** Active use in a live client meeting, not just offline reading
- **User note:** Wants a full narrative onboarding guide added to backlog ("good training tool for new team members") → captured in deferred

### Chaos Lab Guide Strategy
- **Chosen:** Regenerate as `docs/chaos-lab.md`
- **Coverage:** All profiles — core, phaseA/cloud/identity/pki (original) + jwt/registry/source/storage/ssh-weak/ldaps (Phase 4)
- **Existing file:** `CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md` stays as historical artifact
- **Update:** chaos lab README.md gets a link to `docs/chaos-lab.md`

## Deferred Ideas

- **Full narrative onboarding guide** — Prose walkthrough of complete report from first scan to client delivery. Team onboarding / training tool for new members. User explicitly requested backlog capture.
