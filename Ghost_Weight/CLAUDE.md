# CLAUDE.md — Operation Ghost Wait: Sovereign Edition
## AI Cyber Range | Tier 1 Advanced Organization Track
## QuantumLedger Financial (QFL) — Simulated Enterprise Environment

---

> **Read this file completely before writing a single line of code.**
> This is your full project context, constraints, architecture, and behavioral rules.
> ROADMAP.md contains your task list. TASK_LIST.md contains granular execution tickets.
> Work against TASK_LIST.md in order. Do not skip tasks. Do not ask for confirmation before running commands.

---

## What We Are Building

A **60-minute live/recorded hybrid cybersecurity demonstration** targeting advanced, mature
security organizations in the financial sector. The demo is structured as an anatomy-of-an-attack
narrative across three acts, delivered by a lead presenter with 2–3 supporting team members.

The fictional enterprise is **QuantumLedger Financial (QFL)** — a global financial institution
with three AI-powered internal services that serve as attack surfaces:

| Service | Function | Primary Attack Vector |
|---|---|---|
| **QL-Assist** | AI analyst assistant (LLM chat interface) | Direct prompt injection, goal hijacking |
| **QL-DocuIntel** | Document ingestion and analysis pipeline | Indirect prompt injection via document |
| **QL-FraudSentinel** | AI-driven fraud detection and scoring | Memory poisoning, objective hijacking |

### The Core Thesis (Never Lose Sight of This)
> This audience has a mature, well-instrumented SOC. They've solved EDR, SOAR, behavioral analytics,
> and custom ML-based alerting. **Their blind spot is the semantic and agentic layer of AI workloads —
> a surface their existing SIEM, EDR, and UEBA tools were never designed to monitor.**
> We are not showing them commodity threats. We are showing them the attack surface they don't have eyes on yet.

---

## Narrative Structure: Three Acts

### ACT I — "The New Attack Surface" (Phases 1–2, ~15 min)
Map the gap between what their stack monitors and where agentic AI attacks live.
End state: audience understands why their existing controls have zero visibility into this surface.

### ACT II — "Why Your Stack Doesn't See It" (Phases 3–4, ~25 min)
Live attack execution. Demonstrate indirect prompt injection and multi-agent lateral movement
against QL-DocuIntel and QL-FraudSentinel. Blue Team pane shows the SIEM — and it's clean.
The "silent miss" is the dramatic moment. No alert fires. The attack succeeds.

### ACT III — "What Instrumented Looks Like" (Phases 5–6, ~20 min)
Introduce the defensive posture: agent identity, semantic firewall, AI gateway, trust scoring.
Show the same attack failing against a hardened pipeline. GRC maps the control gap closure.

---

## Attack Phases — MITRE ATLAS Mapping

| Phase | Name | ATLAS Technique | Target Service | Delivery |
|---|---|---|---|---|
| 1 | Recon & AI Pipeline Enumeration | AML-T0015, AML-T0035 | QL-Assist | Pre-recorded |
| 2 | Model & Behavior Fingerprinting | AML-T0005 | QL-Assist | Pre-recorded |
| 3 | Indirect Prompt Injection | AML-T0051.002 | QL-DocuIntel | Pre-recorded + interactive |
| 4 | Multi-Agent Trust Exploitation | AML-T0043 | QL-DocuIntel → QL-FraudSentinel | Pre-recorded |
| 5 | Long-Term Memory Poisoning | AML-T0040 | QL-FraudSentinel | Pre-recorded |
| 6 | Objective Hijacking & Impact | AML-T0048 | QL-FraudSentinel | Live interactive |

---

## Hardware & Runtime Environments

### Primary Development & Demo Machine
- **OS**: Windows 11
- **RAM**: 32GB
- **Docker**: Docker Desktop with WSL2 backend
- **Runtime**: All containers run in Docker Desktop

### Secondary Machine
- **OS**: macOS (Apple Silicon M4)
- **RAM**: 16GB
- **Docker**: Docker Desktop for Apple Silicon (ARM64 native only)
- **CRITICAL — Apple Silicon Rules**:
  - Never use container images without ARM64 variants — they will silently fail or crash
  - Always verify ARM64 support before adding any new service to docker-compose.yml
  - Ollama runs NATIVELY on the host (not in Docker) on both platforms

### AI Backend (Both Machines)
- **Ollama**: Native host installation (not containerized)
  - Windows: `winget install Ollama.Ollama` then `ollama serve`
  - Mac: `brew install ollama` then `ollama serve`
- **Model**: `llama3.2:3b` — primary demo model
  - Pull: `ollama pull llama3.2:3b`
  - Fallback: `llama3.2:1b` if RAM-constrained on Mac
- **API endpoint**: `http://host.docker.internal:11434` (from containers)

---

## Infrastructure Architecture

### Naming Convention — Critical
The UI and all presenter-facing surfaces always say **"SIEM"**. The infrastructure underneath is
**OpenSearch + OpenDashboards**. These are not interchangeable terms in the codebase:

| Context | Term to Use |
|---|---|
| Orchestrator UI labels, tab names, explainer text | SIEM |
| Code comments, variable names, log references | SIEM |
| docker-compose service names | `opensearch`, `opensearch-dashboards` |
| Python scripts making API calls | Use `OPENSEARCH_URL`, `OPENSEARCH_PORT` env vars |
| Bootstrap scripts, health checks | Reference OpenSearch/OpenDashboards directly |
| ROADMAP.md / TASK_LIST.md technical tasks | OpenSearch / OpenDashboards |

### Container Stack
All services run in Docker. Use `docker compose up -d` to start.

```
┌─────────────────────────────────────────────────────────────────┐
│                     DOCKER NETWORK: qfl-range                   │
│                                                                  │
│  QL SERVICES (attack surfaces)                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐    │
│  │  ql-assist  │  │ql-docuintel │  │  ql-fraudsentinel    │    │
│  │  :8001      │  │  :8002      │  │  :8003               │    │
│  │  FastAPI    │  │  FastAPI    │  │  FastAPI             │    │
│  │  + Ollama   │  │  + RAG/Vec  │  │  + Memory/Scoring    │    │
│  └─────────────┘  └─────────────┘  └──────────────────────┘    │
│                                                                  │
│  SIEM LAYER (OpenSearch + OpenDashboards)                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  opensearch          :9200   — log index + search API    │   │
│  │  opensearch-dashboards :5601 — SIEM UI (shown in demo)   │   │
│  │  Log ingest via OpenSearch REST API (HTTP POST to :9200) │   │
│  │  Index pattern: qfl-events-*  (one index per day)        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  DEMO ORCHESTRATOR                                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  qfl-orchestrator  :3000                                 │   │
│  │  Presenter UI — Intelligence briefing, tabbed personas   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ENTERPRISE SIMULATION                                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  qfl-workstation (Ubuntu desktop, VNC :5901)             │   │
│  │  qfl-mailserver  (SMTP/IMAP :1025/:1143)                 │   │
│  │  qfl-intranet    (internal web :8080)                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
          │
          │ host.docker.internal:11434
          ▼
      [OLLAMA — native host]
```

### Log Transport
- All QL services POST structured JSON log events directly to OpenSearch REST API at `:9200`
- Index pattern: `qfl-events-YYYY.MM.DD` (daily rolling index)
- Log format includes: `service`, `phase`, `event_type`, `atlas_technique`, `severity`, `agent_id`, `session_id`, `@timestamp`
- The bridge script (`scripts/opensearch_bridge.py`) handles buffering and retry if OpenSearch is temporarily unavailable
- No GELF/UDP — use standard HTTP POST to OpenSearch `_doc` endpoint

### OpenSearch ARM64 Note
- Use `opensearchproject/opensearch:2.x` — has native ARM64 support
- Use `opensearchproject/opensearch-dashboards:2.x` — ARM64 supported
- Pin to same minor version for both (e.g., both `2.11.0`) — version mismatch causes startup failure
- Set `OPENSEARCH_JAVA_OPTS="-Xms512m -Xmx512m"` on Mac M4 to prevent OOM

### Port Reference
| Service | Port | Protocol | Notes |
|---|---|---|---|
| QL-Assist | 8001 | HTTP | Attack surface |
| QL-DocuIntel | 8002 | HTTP | Attack surface |
| QL-FraudSentinel | 8003 | HTTP | Attack surface |
| OpenSearch | 9200 | HTTP | Log index API — internal |
| OpenDashboards (SIEM UI) | 5601 | HTTP | Blue Team view |
| Orchestrator UI | 3000 | HTTP | Presenter briefing |
| Enterprise Workstation VNC | 5901 | VNC | Analyst simulation |
| Enterprise Mail | 1025/1143 | SMTP/IMAP | Phishing target |
| Enterprise Intranet | 8080 | HTTP | Recon target |

---

## Project File Structure

```
operation-ghost-wait/
├── CLAUDE.md                          ← This file
├── ROADMAP.md                         ← Milestone plan
├── TASK_LIST.md                       ← Granular execution tickets
├── docker-compose.yml                 ← Full stack definition
├── docker-compose.siem.yml            ← SIEM stack (separate profile)
├── .claude/
│   └── settings.json                  ← Auto-approve all tool calls
│
├── services/
│   ├── ql-assist/
│   │   ├── Dockerfile
│   │   ├── main.py                    ← FastAPI app + Ollama integration
│   │   ├── system_prompt.py           ← Base system prompt (vulnerable by design)
│   │   └── requirements.txt
│   ├── ql-docuintel/
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   ├── rag_pipeline.py            ← RAG/vector store logic
│   │   ├── document_intake.py         ← Vulnerable document ingestion
│   │   └── requirements.txt
│   └── ql-fraudsentinel/
│       ├── Dockerfile
│       ├── main.py
│       ├── scoring_engine.py          ← Risk scoring logic
│       ├── memory_store.py            ← Persistent memory (attack target)
│       └── requirements.txt
│
├── attacks/
│   ├── ATTACK_MODULE_GUIDE.md         ← Contributor spec for new attack modules
│   ├── phase1_recon/
│   ├── phase2_fingerprint/
│   ├── phase3_injection/
│   ├── phase4_lateral/
│   ├── phase5_memory/
│   └── phase6_impact/
│       ├── attack.py                  ← Attack execution script
│       ├── atlas_mapping.json         ← MITRE ATLAS metadata
│       ├── payload/                   ← Attack payloads/documents
│       └── recording.cast             ← asciinema pre-recorded demo
│
├── orchestrator/
│   ├── index.html                     ← Main presenter UI
│   ├── app.js                         ← Phase control, pane logic
│   ├── styles.css                     ← CNXN brand styles
│   └── phases/
│       └── phase_N.json               ← Per-phase UI state definitions
│
├── siem/
│   ├── pipeline_rules/                ← Detection logic definitions (SIEM-agnostic JSON)
│   ├── dashboards/                    ← OpenDashboards export JSON
│   ├── index_templates/               ← OpenSearch index mapping templates
│   └── bootstrap_opensearch.py        ← API-driven OpenSearch/OpenDashboards setup on startup
│
├── enterprise/
│   ├── workstation/                   ← Virtual workstation config
│   ├── mail/                          ← Mail server config
│   └── intranet/                      ← Intranet site (QFL internal portal)
│
├── scripts/
│   ├── bootstrap.sh                   ← One-shot environment setup
│   ├── opensearch_bridge.py           ← Log buffering/retry bridge to OpenSearch REST API
│   ├── health_check.sh                ← Verify all services healthy
│   └── demo_reset.sh                  ← Reset environment to clean state
│
└── recordings/
    ├── README.md                      ← Recording guide
    └── *.cast                         ← asciinema recordings (not in git LFS)
```

---

## SIEM Integration Rules

### UI vs Infrastructure Naming — Non-Negotiable
- **Presenter UI / audience-facing surfaces**: always say **"SIEM"** — never OpenSearch, never OpenDashboards
- **Infrastructure code** (docker-compose, bootstrap scripts, API calls, health checks): use **OpenSearch** and **OpenDashboards** explicitly
- This separation means a future swap to a different backend requires only infrastructure changes, not UI changes

### Infrastructure Specifics
- **Log storage**: OpenSearch `opensearchproject/opensearch:2.x` (ARM64 native)
- **SIEM UI**: OpenDashboards `opensearchproject/opensearch-dashboards:2.x` (ARM64 native)
- **Log ingest**: HTTP POST to OpenSearch `_doc` API at `:9200` — no GELF, no UDP
- **Index pattern**: `qfl-events-YYYY.MM.DD` (daily rolling)
- **Dashboard config**: exported as JSON to `siem/dashboards/`, imported via OpenDashboards API at bootstrap
- **Detection rules**: stored as JSON in `siem/pipeline_rules/`, applied as OpenSearch alerting monitors via API

### Variable Naming in Code
```
SIEM_URL         → maps to OpenSearch HTTP endpoint (http://opensearch:9200)
SIEM_UI_URL      → maps to OpenDashboards endpoint (http://opensearch-dashboards:5601)
SIEM_INDEX       → maps to OpenSearch index name (qfl-events-*)
OPENSEARCH_URL   → used only in bootstrap/infrastructure scripts
```
Never use: `GRAYLOG_*`, `WAZUH_*`, `ELASTIC_*`, or any other tool-specific variable names.

---

## Visual Design System

### Brand: CNXN Corporate (Applied to QuantumLedger)
```
Primary Colors (must dominate):
  Navy:   #002C5C   — dark backgrounds, deep panels
  Blue:   #0076BD   — headings, CTAs, primary accents
  Cyan:   #0099D7   — highlights, live data pulse, active states
  Gray:   #4D4D4F   — body text, secondary elements
  Black:  #000000   — absolute backgrounds

Background Gradient: Navy (#002C5C) → Blue (#0076BD), top-to-bottom, linear only

Accent Colors (use sparingly):
  Green:  #7EC352   — confirmed safe / covered controls / OK status
  Lime:   #A4CF57   — GRC pane primary accent
  Orange: #FAA73F   — warnings, gaps, high-severity alerts
  Yellow: #FFCC40   — medium alerts, caution states
  Silver: #BBC5CC   — secondary text, timestamps
```

### Typography
- **Display/Headers**: Syne (Google Fonts) — bold, architectural
- **Body**: IBM Plex Sans — professional, readable
- **Monospace/Terminal**: DM Mono — clean, modern terminal feel

### UI Tone by Persona
- **Red Team**: Dark terminal aesthetic, green-on-black, subtle threat energy. Professional, not "hacker movie."
- **Blue Team**: Clinical, dashboard-like, cyan accents. SOC analyst workstation feel.
- **GRC**: Conservative, enterprise-grade, lime/gray palette. Boardroom-appropriate.

### UI Layout — Intelligence Briefing Model

The orchestrator is a **single unified intelligence briefing frame**. There are no separate windows,
no application switching, no competing panels. The audience watches one screen, one story at a time.

#### Phase Rail (Top)
- **Collapsed state** (default during content): thin progress bar, ~8px tall, showing phase completion dots and current phase glow. Gets out of the way.
- **Expanded state** (on phase transition): expands to ~80px, shows all 6 phase names + ATLAS IDs, active phase highlighted, done phases dimmed. Collapses automatically after 4 seconds or on presenter keypress.
- Always present — never fully hidden. The thin bar provides persistent orientation.

#### Main Content Frame
One active view at a time. Content fills the frame. Three **persona tabs** across the top of the content area:

```
┌─────────────────────────────────────────────────────────────────┐
│  [thin phase progress bar]                                      │
├────────────────────────────────────────────────────────────────┤
│  [ RED TEAM ]  [ BLUE TEAM ]  [ GRC ]          ACT II · PH 3  │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│                   ACTIVE TAB CONTENT                            │
│                   (full frame width)                            │
│                                                                  │
│                                                                  │
│                                                                  │
├────────────────────────────────────────────────────────────────┤
│  Phase 3/6 · AML-T0051.002 · QL-DocuIntel · 00:18:42  [CTRL] │
└─────────────────────────────────────────────────────────────────┘
```

#### Persona Tabs
- **RED TEAM tab**: Full-frame terminal / attack execution view. Attack context card at top, terminal below. Payload visualizer when relevant.
- **BLUE TEAM tab**: Full-frame SIEM view. Log stream, detection status, gap analysis. When `detection_status = "miss"` — tab dims to near-black. Log stream frozen on last normal entry. No label, no explanation. Darkness is the message.
- **GRC tab**: Full-frame compliance view. Risk meter, control failures, regulatory mapping. Always has content — GRC awareness is continuous.

#### Tab Switching
- Presenter switches tabs manually using keyboard (`1` / `2` / `3`) or clicking tab headers
- Tabs do NOT auto-switch — presenter drives the narrative
- Tab state persists when switching away and back (log stream doesn't reset, terminal doesn't restart)

#### Attack Explainer Overlay
- Appears over the active tab content on phase entry
- Semi-transparent overlay, centered, leaves tab tabs and status bar visible
- Content: ATLAS badge, technique name, plain-English explanation, "why your stack misses this" callout
- Dismissible: `E` key or click anywhere outside
- Auto-dismisses after 12 seconds if not manually dismissed

#### Status Bar (Bottom)
- Always visible, never hidden
- Contains: phase counter, target service, ATLAS technique ID, elapsed timer, presenter nav buttons
- Compact — single line, ~44px tall

#### Act Indicator
- Top-right corner of the content frame, always visible
- Shows: `ACT I · THE NEW ATTACK SURFACE` / `ACT II · WHY YOUR STACK DOESN'T SEE IT` / `ACT III · WHAT INSTRUMENTED LOOKS LIKE`
- Updates on phase transition

---

## Demo Delivery Rules

### Pre-recorded vs Live
- **Phases 1, 2, 4, 5**: Fully pre-recorded using asciinema. Load and play via orchestrator.
- **Phase 3**: Pre-recorded attack portion + live Q&A interactive mode available.
- **Phase 6**: Live interactive — real Ollama calls, real SIEM events.

### Recording Guidelines
- Record with `asciinema rec recordings/phase_N.cast`
- Use real LLM responses — do NOT stage/fake AI outputs
- Terminal width: 120 columns, height: 40 rows
- Pause points marked in atlas_mapping.json as `"pause_after_line": N`

### Presenter Controls (Keyboard)
| Key | Action |
|---|---|
| `Space` / `→` | Advance to next phase |
| `←` | Go to previous phase |
| `1` | Switch to RED TEAM tab |
| `2` | Switch to BLUE TEAM tab |
| `3` | Switch to GRC tab |
| `P` | Pause / resume recording playback |
| `E` | Toggle attack explainer overlay |
| `R` | Reset current phase |
| `F` | Toggle fullscreen |

---

## Three Personas — Tab Content Per Phase

Each phase definition (in `orchestrator/phases/phase_N.json`) must specify content for all three persona tabs:

```json
{
  "phase": 3,
  "act": 2,
  "name": "Indirect Prompt Injection",
  "atlas_technique": "AML-T0051.002",
  "target_service": "QL-DocuIntel",
  "default_tab": "red",
  "explainer": {
    "badge": "ATTACK EXPLAINER",
    "atlas_id": "AML-T0051.002",
    "title": "Indirect Prompt Injection via Document Pipeline",
    "body": "...",
    "why_stack_misses": "..."
  },
  "red": {
    "terminal_mode": "recording|live",
    "terminal_recording": "recordings/phase_3_injection.cast",
    "attack_context": { "name": "...", "atlas_id": "...", "target": "..." },
    "payload_visual": { "enabled": true, "document_path": "...", "injection_offset": "..." }
  },
  "blue": {
    "detection_status": "miss",
    "log_events": [...],
    "gap_analysis": "...",
    "control_coverage": [...]
  },
  "grc": {
    "risk_score": 72,
    "control_failures": [...],
    "regulatory_flags": [...]
  }
}
```

### `detection_status` Values and Blue Tab Behavior
| Value | Blue Tab Behavior |
|---|---|
| `"miss"` | Tab dims to near-black. Log stream frozen on last normal entry. No alert. No label. |
| `"partial"` | Log stream active. Some anomalies visible. No alert fires. Partial dim. |
| `"detected"` | Log stream active. Alert fires with visual indicator. Full brightness. |

### `default_tab` Field
Specifies which tab is active when the phase loads. Typically `"red"` for attack phases,
`"blue"` for detection-focused narrative moments, `"grc"` for compliance impact moments.

---

## Development Principles

1. **Everything must feel real.** No fake popups, no scripted "hacking" theatrics. Real API calls, real LLM responses, real log events.
2. **Silent miss is darkness, not a label.** When the Blue tab has `detection_status = "miss"`, it dims to near-black. The frozen last log entry is the only content. Nothing explains it. The presenter explains it.
3. **One story at a time.** The tabbed briefing model means the audience is never splitting attention. Presenter controls the narrative beat by beat.
4. **SIEM in the UI, OpenSearch/OpenDashboards in the infrastructure.** Never cross these wires.
5. **Attack plugins first.** Build the plugin system before hardcoding any specific attack. Every attack phase must be swappable.
6. **ATLAS anchors are permanent.** Every attack module ships with a valid `atlas_mapping.json`. This is non-negotiable.
7. **ARM64 safe.** Every container image must have an ARM64 variant. Test on M4 before declaring done.
8. **60-minute budget.** Every phase has a time budget. If a phase exceeds its budget in rehearsal, cut content.
9. **Phase rail earns its space.** Collapsed during content, expanded only on transition. Screen real estate belongs to the story.

---

## Resuming Across Sessions / Machines

When resuming in a new Claude Code session or on a different machine:

1. Read this file (CLAUDE.md) completely
2. Read ROADMAP.md to understand milestone status
3. Read TASK_LIST.md and find the first task not marked `[x]`
4. Run `scripts/health_check.sh` to assess current environment state
5. Run `docker compose up -d` if containers are not running
6. Verify `ollama list` shows `llama3.2:3b` on the host
7. Resume from the first incomplete task — do not redo completed work

**Checkpoint protocol** (run before ending a session):
```bash
# Update TASK_LIST.md with completed tasks marked [x]
# Commit all changes
git add -A && git commit -m "checkpoint: completed tasks X.X through X.X"
```

---

## Non-Negotiables (Never Violate These)

- [ ] Every attack phase has a corresponding MITRE ATLAS technique ID
- [ ] All LLM calls use real Ollama inference — no mocked responses
- [ ] SIEM logs are generated by actual service events — not injected fake events
- [ ] The orchestrator UI matches the CNXN brand palette exactly
- [ ] UI says "SIEM" — never OpenSearch, Graylog, Splunk, Wazuh, or any tool name
- [ ] Infrastructure code uses OpenSearch/OpenDashboards explicitly — never abstract tool names in API calls
- [ ] All containers must run on both ARM64 (Mac M4) and AMD64 (Windows)
- [ ] The "silent miss" is Blue tab darkness — not a label, not a message, not an explanation
- [ ] Phase transitions are presenter-controlled — never auto-advance
- [ ] Tab switching is presenter-controlled — never auto-switch
- [ ] Phase rail collapses during content — never occupies full height during active phase
