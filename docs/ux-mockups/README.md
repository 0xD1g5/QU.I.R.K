# QU.I.R.K — Browser UX Mockups

Exploratory, non-production UX mockups for the dashboard (`src/dashboard`). These are
self-contained static HTML files (no build step, no dependencies) plus pre-rendered PNGs.
Open any `.html` directly in a browser, or view the PNGs in `renders/`.

**Status:** design exploration only — not wired to the app, not a commitment to ship.

## Purpose

Stress-test how *impactful* the browser interface is, using best-in-class security /
observability consoles as reference points (Wiz, CrowdStrike Falcon, SentinelOne,
Palo Cortex, Portkey). The recurring theme across those tools:

> Opinionated prioritization, narrative over tables, evidence one click away, and a
> clear "so what do I do" at every altitude.

The QU.I.R.K redesigns reuse the **existing pages and the existing `useScanData`
payload** — they add a judgment/prioritization layer on top rather than introducing new
data or rebuilding the surface.

## The set

### Baseline — QU.I.R.K as it is today
| File | Screen |
|------|--------|
| `01-current-executive.html` | Executive: score gauges + severity bars + scanner coverage grid |
| `02-current-findings.html` | Findings: filterable table |

### Redesigns — same data, same theme, re-prioritized
| File | Idea | Inspired by |
|------|------|-------------|
| `03-redesign-verdict.html` | Executive "verdict layer": one headline judgment + top-3 do-this-first (score-lift + cost-of-inaction); gauges demoted to a supporting strip | Wiz / Falcon |
| `04-redesign-roadmap.html` | Roadmap with consequence framing per node + a "58 → 79" progress ribbon | SentinelOne / Wiz |
| `05-redesign-storyline.html` | Finding "Storyline" drawer linking finding → CBOM → roadmap without losing your place | SentinelOne Storyline |
| `09-redesign-exposure-map.html` | **Exposure Map** (a tab inside Roadmap): quantum exposure chains Internet → service → crown-jewel data, with shared-key blast-radius and a highest-leverage "quick win" fix | Wiz attack-path / toxic combination |

### Reference patterns — generic, illustrate the pattern (not QU.I.R.K)
| File | Pattern |
|------|---------|
| `06-ref-wiz.html` | Wiz-style "toxic combination" / attack-path — fix the chain, not the list |
| `07-ref-crowdstrike.html` | Falcon-style severity-first triage queue + one-screen what/how-bad/what-now |
| `08-ref-portkey.html` | Portkey-style observability — KPI row + trend + live feed |

### Built — live render of the implemented component
| File | What it is |
|------|------------|
| `renders/10-verdict-live.png` | Screenshot of the **real** `ExecutiveVerdict` React component (not a mockup), rendered with `VITE_VERDICT_LAYER=1` against the a11y scan fixture. Shows the verdict layer composed above the existing regression chip, gauges, and severity chart. Implemented in `src/dashboard/src/components/ExecutiveVerdict.tsx` (flag-gated; default dashboard unchanged). |

To reproduce the live render:

```sh
cd src/dashboard
VITE_VERDICT_LAYER=1 VITE_A11Y_FIXTURE=1 npm run dev   # then screenshot http://localhost:5173/
```

## Re-rendering the PNGs

The PNGs were captured with headless Chrome at 2x scale:

```sh
chrome --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
  --window-size=1360,884 --screenshot=renders/<name>.png "file://$PWD/<name>.html"
```

## Suggested next steps

1. **Run a usability test** before building: 5-second test on the Executive screen
   ("what's the one thing to do, and how bad is it?") + a short task-based session with
   3–5 people, scored with SUS.
2. **Spike the verdict layer** (`03`) against the real `useScanData` payload behind a
   flag — highest leverage, pure presentation logic.
3. **Prototype the Exposure Map** (`09`) — the chain/blast-radius model is the biggest
   differentiator and the strongest justification for roadmap sequencing.
