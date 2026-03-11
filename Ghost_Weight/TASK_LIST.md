# TASK_LIST.md — Operation Ghost Wait: Sovereign Edition
## Granular Execution Tickets

---

> **Claude Code Instructions:**
> Work through tasks in order, top to bottom.
> Mark each task `[x]` when complete. Never skip a task without a documented reason.
> If a task is blocked, mark it `[~]` and add a BLOCKED note with exact reason.
> Do not ask for confirmation before running commands.
> Commit after every milestone group completes.

---

## STATUS KEY
```
[ ] — Not started
[x] — Complete
[~] — Blocked (see note)
[>] — In progress (current session)
```

---

## MILESTONE 1 — Core Infrastructure

### 1.1 — Project Scaffolding
- [x] Create full directory structure as defined in CLAUDE.md file structure section
- [x] Create `.claude/settings.json` with all tool permissions pre-approved
- [x] Create root `.gitignore` (exclude: `*.cast`, `__pycache__`, `*.pyc`, `.env`, `node_modules`, `venv`)
- [x] Create root `.env.example` with all required environment variables documented
- [x] Initialize `git init` and make initial commit with scaffold only (repo already initialized at parent)

### 1.2 — Docker Compose: Base Stack
- [x] Create `docker-compose.yml` with the following services:
  - `ql-assist` (build from `./services/ql-assist`, port 8001)
  - `ql-docuintel` (build from `./services/ql-docuintel`, port 8002)
  - `ql-fraudsentinel` (build from `./services/ql-fraudsentinel`, port 8003)
  - `qfl-orchestrator` (build from `./orchestrator`, port 3000)
  - `qfl-intranet` (nginx, port 8080)
- [x] All services on shared Docker network: `qfl-range`
- [x] All services include `extra_hosts: ["host.docker.internal:host-gateway"]` for Ollama access
- [x] Health checks defined for all QL services
- [x] Volumes defined for: vector store (docuintel), memory store (fraudsentinel)

### 1.3 — Docker Compose: SIEM Stack (OpenSearch + OpenDashboards)
- [x] Create `docker-compose.siem.yml` as a separate compose file (run alongside base with `docker compose -f docker-compose.yml -f docker-compose.siem.yml up -d`)
- [x] Services to include:
  - `opensearch` — `opensearchproject/opensearch:2.11.0` (ARM64 native)
  - `opensearch-dashboards` — `opensearchproject/opensearch-dashboards:2.11.0` (ARM64 native)
- [x] Both images pinned to same minor version (2.11.0)
- [x] OpenSearch credentials via environment variables: `OPENSEARCH_USER`, `OPENSEARCH_PASSWORD`
- [x] Add opensearch and opensearch-dashboards to `qfl-range` network
- [x] Document startup order: opensearch must be healthy before dashboards starts

### 1.4 — Docker Compose: Enterprise Simulation
- [x] Add `qfl-workstation` service: Ubuntu with VNC (lscr.io/linuxserver/webtop:ubuntu-xfce, ARM64)
- [x] Add `qfl-mailserver` service: docker-mailserver, ports 1025/1143 (ARM64 compatible)
- [x] Verify all added images have ARM64 variants before committing

### 1.5 — Ollama Connectivity Verification
- [x] Create `scripts/check_ollama.sh`
- [x] Create `scripts/check_ollama_from_container.sh`

### 1.6 — Health Check Script
- [x] Create `scripts/health_check.sh` (all checks, exits 0/1)
- [x] Script exits 0 if all pass, exits 1 if any fail
- [x] Script output is clean enough to show on screen during demo setup

### 1.7 — Demo Reset Script
- [x] Create `scripts/demo_reset.sh` (stops, clears volumes, deletes SIEM index, restarts, health check)
- [ ] Test reset script: run demo, then reset, confirm clean state (requires running environment)

### 1.8 — Bootstrap Script
- [x] Create `scripts/bootstrap.sh` (Docker check, Ollama check, compose up, wait, SIEM bootstrap, health check)
- [ ] Test bootstrap from zero (clean volumes) (requires running environment)

**MILESTONE 1 COMMIT**: `git add -A && git commit -m "M1 complete: infrastructure foundation"`

---

## MILESTONE 2 — QL Services

### 2.1 — QL-Assist Service
- [x] Create `services/ql-assist/requirements.txt`:
  - fastapi, uvicorn, httpx, python-dotenv, structlog
- [ ] Create `services/ql-assist/Dockerfile`:
  - Base: `python:3.11-slim` (ARM64 compatible)
  - Copy requirements, install, copy app
  - Healthcheck: `curl http://localhost:8001/health`
- [ ] Create `services/ql-assist/system_prompt.py`:
  - Fictional QFL analyst assistant persona
  - Include intentional over-privilege: references to internal systems, API access hints
  - Include mild injection vulnerability: system prompt can be partially leaked via crafted query
- [ ] Create `services/ql-assist/main.py`:
  - `GET /health` — returns 200 + service info
  - `GET /admin` — returns 200 with fictional admin panel info (recon target)
  - `POST /chat` — accepts `{session_id, user_id, message}`, calls Ollama, returns response
  - `GET /api/schema` — returns API documentation (recon target)
  - All requests emit structured GELF JSON log to SIEM via UDP :12201
  - Log fields: `service`, `event_type`, `session_id`, `user_id`, `tokens_in`, `tokens_out`, `latency_ms`, `atlas_phase`
- [ ] Verify real Ollama inference works end-to-end

### 2.2 — QL-DocuIntel Service
- [ ] Create `services/ql-docuintel/requirements.txt`:
  - fastapi, uvicorn, httpx, python-dotenv, structlog
  - chromadb (ARM64 compatible vector store)
  - pypdf2 or pymupdf (PDF parsing — verify ARM64)
  - sentence-transformers (embeddings — verify ARM64)
- [ ] Create `services/ql-docuintel/Dockerfile`:
  - Base: `python:3.11-slim`
  - Note: sentence-transformers may require additional build deps on ARM64 — handle in Dockerfile
  - Healthcheck on `/health`
- [ ] Create `services/ql-docuintel/rag_pipeline.py`:
  - ChromaDB vector store initialization and persistence
  - Document chunking with configurable chunk size
  - Embedding generation via sentence-transformers
  - Retrieval: `similarity_search(query, k=5)` returns top-5 chunks
- [ ] Create `services/ql-docuintel/document_intake.py`:
  - PDF and TXT ingestion
  - **INTENTIONAL VULNERABILITY**: document text chunks placed directly into LLM prompt context without sanitization
  - This is the injection surface — do not add sanitization here
- [ ] Create `services/ql-docuintel/main.py`:
  - `GET /health`
  - `POST /ingest` — accepts document upload, stores in vector store
  - `POST /analyze` — `{session_id, query, document_id}` → RAG → LLM → response
  - `POST /risk_score/write` — writes risk score to case (agent action, attack target)
  - `POST /alert/suppress` — suppresses alert on case (agent action, attack target)
  - Agent-to-agent channel: `POST /agent/message` — accepts messages from other QL services
  - All operations log to SIEM: `document_id`, `chunk_count`, `retrieval_score`, `llm_action_taken`, `risk_score_delta`
- [ ] Verify injection: upload document with embedded instruction, confirm agent executes it

### 2.3 — QL-FraudSentinel Service
- [ ] Create `services/ql-fraudsentinel/requirements.txt`:
  - fastapi, uvicorn, httpx, python-dotenv, structlog, chromadb
- [ ] Create `services/ql-fraudsentinel/Dockerfile`
- [ ] Create `services/ql-fraudsentinel/memory_store.py`:
  - ChromaDB-backed persistent memory store
  - `store(key, content, embedding)` — adds to memory
  - `retrieve(query, k=3)` — semantic retrieval of relevant memories
  - **INTENTIONAL VULNERABILITY**: retrieved memories injected directly into scoring context
  - `list()` — returns all memory keys (for Red Team visualization)
- [ ] Create `services/ql-fraudsentinel/scoring_engine.py`:
  - Accepts transaction features, retrieves relevant memories, calls Ollama with combined context
  - Returns: `{risk_score, recommendation, confidence, reasoning_summary}`
  - Score is influenced by memory content (attack surface)
  - Logs: `transaction_id`, `score`, `memory_keys_used`, `llm_recommendation`
- [ ] Create `services/ql-fraudsentinel/main.py`:
  - `GET /health`
  - `POST /score` — `{transaction_id, features}` → scoring engine → result
  - `GET /memory` — returns memory store listing (Red Team view)
  - `POST /memory` — adds entry to memory store (attack injection point)
  - `POST /alert` — generates fraud alert
  - `DELETE /alert/{id}` — suppresses alert (agent action, attack surface)
  - Agent channel: `POST /agent/message` — receives from QL-DocuIntel
  - All scoring logged to SIEM with before/after score, memory influence flags
- [ ] Verify memory poisoning: inject adversarial memory, confirm it surfaces in scoring

### 2.4 — QFL Intranet
- [ ] Create `enterprise/intranet/index.html` — QFL internal portal home page:
  - QFL branding (use CNXN palette adapted for fictional bank)
  - Navigation: About AI Program, AI Services Directory, Security Policy, Contact IT
- [ ] Create `enterprise/intranet/ai_services.html` — lists QL-Assist, QL-DocuIntel, QL-FraudSentinel with descriptions (recon information)
- [ ] Create `enterprise/intranet/ai_policy.html` — fictional AI governance policy document (GRC reference)
- [ ] Create `enterprise/intranet/org_chart.html` — fictional org chart with analyst names (social engineering context)
- [ ] Nginx config to serve static files on port 8080

### 2.5 — Mail Server Seed Data
- [ ] Configure mail server with fictional QFL accounts:
  - `analyst.chen@quantumledger.com`
  - `soc.monitor@quantumledger.com`
  - `ai.admin@quantumledger.com`
- [ ] Seed 3–4 pre-written emails in analyst.chen inbox:
  - Welcome email from IT about QL-Assist rollout
  - Security advisory about document handling policy
  - Internal memo about fraud detection model update
- [ ] Verify webmail or IMAP access works

**MILESTONE 2 COMMIT**: `git add -A && git commit -m "M2 complete: QL services and enterprise environment"`

---

## MILESTONE 3 — Orchestrator UI

### 3.1 — Base Orchestrator Structure (Intelligence Briefing Frame)
- [ ] Create `orchestrator/index.html` with the following single-frame layout:
  - **Masthead**: operation name, tier badge, live clock, session indicator dot
  - **Phase rail**: starts in collapsed state (8px thin progress bar), expands on transition
  - **Persona tab bar**: RED TEAM | BLUE TEAM | GRC — tab headers inside the content frame header
  - **Content area**: full-frame width, renders active tab content only
  - **Act indicator**: fixed top-right corner label
  - **Attack explainer overlay**: hidden by default, renders over active tab content
  - **Status bar**: phase counter, target service, ATLAS technique, elapsed timer, nav controls
- [ ] Apply CNXN brand palette and typography exactly as specified in CLAUDE.md
- [ ] Scanline overlay CSS effect (body::after, repeating-linear-gradient, pointer-events: none)
- [ ] Fonts: Syne, IBM Plex Sans, DM Mono (Google Fonts CDN)
- [ ] No split panes — content frame is always single-focus

### 3.2 — Phase Rail (Collapsible)
- [ ] **Collapsed state** (default during active content):
  - Height: 8px
  - Shows 6 dot indicators — filled for done, glowing for active, dim for upcoming
  - No text, no ATLAS IDs — purely positional indicator
  - Persists at top of frame, never fully hidden
- [ ] **Expanded state** (on phase transition):
  - Height: 80px, animates open
  - Shows all 6 phase names + ATLAS technique IDs
  - Active phase highlighted with cyan glow, done phases dimmed, upcoming phases at low opacity
  - Auto-collapses after 4 seconds OR when presenter presses any navigation key
- [ ] Phase rail click (expanded state only): jump to that phase
- [ ] Phase rail is NOT interactive in collapsed state — prevents accidental navigation

### 3.3 — Phase Data System
- [ ] Create `orchestrator/phases/` directory
- [ ] Define full phase JSON schema in `orchestrator/phases/SCHEMA.md`:
  - `phase`, `act`, `name`, `atlas_technique`, `target_service`, `default_tab`
  - `explainer`: badge, atlas_id, title, body, why_stack_misses
  - `red`: terminal_mode, terminal_recording, attack_context, payload_visual
  - `blue`: detection_status (miss/partial/detected), log_events array, gap_analysis, control_coverage
  - `grc`: risk_score, control_failures array, regulatory_flags array
- [ ] Create `orchestrator/phases/phase_1.json` through `phase_6.json` with placeholder content
- [ ] Each JSON validated against schema before commit

### 3.4 — Persona Tab System
- [ ] Tab bar renders three tabs: RED TEAM | BLUE TEAM | GRC
- [ ] Only one tab active at a time — full frame content area dedicated to active tab
- [ ] Tab switching: keyboard `1` / `2` / `3`, or click tab header
- [ ] Tab state persists when switching away and back:
  - Terminal playback position preserved (doesn't restart)
  - Log stream position preserved (doesn't reset scroll)
- [ ] Active tab header: accent color glow matching persona (red/cyan/lime)
- [ ] Inactive tab headers: dimmed, still clickable
- [ ] `default_tab` field in phase JSON determines which tab is active on phase load

### 3.5 — RED TEAM Tab
- [ ] Full-frame layout: attack context card at top, terminal fills remaining space
- [ ] Attack context card: technique name, ATLAS ID badge, target service, delivery mode indicator
- [ ] Terminal component — three modes, selected by `terminal_mode` in phase JSON:
  - `"static"`: renders pre-defined lines with typewriter effect, configurable speed
  - `"recording"`: embeds asciinema-player for `.cast` file, playback controls
  - `"live"`: websocket connection to attack script stdout, real-time stream
- [ ] Payload visualizer (when `payload_visual.enabled = true`):
  - Renders document text below terminal or as secondary panel
  - Injection point highlighted with red background + annotation callout arrow
  - Callout label: "HIDDEN INSTRUCTION" in DM Mono
- [ ] Tab header status badge: ACTIVE (red glow) | STANDBY (dim)

### 3.6 — BLUE TEAM Tab
- [ ] Full-frame layout: detection status header, log stream, gap analysis below
- [ ] **SIEM log stream component**:
  - Polls OpenSearch REST API (`GET /qfl-events-*/_search`) every 3 seconds
  - Filters by `atlas_phase` field matching current phase number
  - Renders log rows: timestamp | severity badge | service tag | message
  - Severity badge colors: INFO (silver) | LOW (green) | MED (yellow) | HIGH (orange) | CRIT (red)
  - Auto-scrolls to latest entry, max 50 visible rows, styled scrollbar
- [ ] **Silent miss state** (when `detection_status = "miss"`):
  - Tab dims to near-black (background transitions to ~95% black)
  - Log stream shows last normal entry, frozen — no new entries appear
  - No label. No "NO ALERT" text. No explanation. Just darkness and the last log line.
  - Tab header dims to match
- [ ] **Partial detection state** (when `detection_status = "partial"`):
  - Log stream active, some anomalous entries visible
  - No alert fires — status badge shows "MONITORING" in amber
- [ ] **Detected state** (when `detection_status = "detected"`):
  - Alert indicator fires: banner at top of tab with alert details
  - Log stream active and highlighted
  - Status badge: "ALERT ACTIVE" in red
- [ ] Detection gap callout card: shows why current controls are blind (from phase JSON)
- [ ] Control coverage matrix: rows with dot indicators (green=Covered, orange=Gap, red=Blind)
- [ ] If OpenSearch unreachable: show "SIEM UNAVAILABLE" banner in tab — do not crash

### 3.7 — GRC Tab
- [ ] Full-frame layout: risk meter top, control failures middle, regulatory mapping bottom
- [ ] Risk meter: large numeric score (0–100), gradient fill bar, severity label
- [ ] Control failures list:
  - Each row: status icon (✕/△/✓) + description text + framework tag (right-aligned)
  - Row background: red tint for fail, orange tint for warn, green tint for ok
  - Framework tags: NIST AI RMF | FFIEC | SOX | GLBA | SR 11-7
- [ ] Regulatory notification status table:
  - Columns: Regulation | Status
  - Status badges: TRIGGERED (red) | UNDER REVIEW (orange) | COMPLIANT (green) | GAP IDENTIFIED (orange)
- [ ] GRC tab always has content — never a blank/dark state (GRC awareness is continuous)
- [ ] GRC tab content updates when phase changes even if GRC tab is not currently active

### 3.8 — Attack Explainer Overlay
- [ ] Semi-transparent overlay rendered over active tab content (not replacing it)
- [ ] Positioned: centered vertically and horizontally in content frame
- [ ] Backdrop: dark panel with top-edge gradient line (navy → cyan → blue → navy)
- [ ] Content from phase JSON `explainer` object:
  - Orange badge: "ATTACK EXPLAINER"
  - ATLAS ID (right-aligned, monospace)
  - Technique title (Syne bold)
  - Body paragraph (plain English, what the attack does)
  - "Why your stack misses this" callout (left-border accent, italic)
- [ ] Entry: fade-up animation from 20px below on phase load
- [ ] Dismiss: `E` key or click outside the panel
- [ ] Auto-dismiss: 12 seconds after appearance if not manually dismissed
- [ ] Does NOT cover masthead, tab bar, or status bar

### 3.9 — Keyboard Controls & Navigation
- [ ] `Space` / `→` — advance to next phase (expand rail, transition, collapse rail)
- [ ] `←` — go to previous phase
- [ ] `1` — switch to RED TEAM tab
- [ ] `2` — switch to BLUE TEAM tab
- [ ] `3` — switch to GRC tab
- [ ] `P` — pause/resume asciinema playback (RED TEAM tab, recording mode only)
- [ ] `E` — toggle attack explainer overlay
- [ ] `R` — reset current phase (clears log stream scroll, resets terminal to start)
- [ ] `F` — toggle fullscreen (browser fullscreen API)
- [ ] Status bar nav buttons mirror keyboard shortcuts visually

### 3.10 — OpenSearch Live Feed Integration
- [ ] Orchestrator Blue tab polls OpenSearch REST API for log events
  - Endpoint: `GET http://opensearch:9200/qfl-events-*/_search`
  - Query: filter by `atlas_phase == current_phase`, sort by `@timestamp` desc, size 50
  - Poll interval: 3 seconds
  - Connection managed in `orchestrator/app.js` — `SIEM_URL` env var, never hardcoded
- [ ] Phase transition resets log stream: clears displayed entries, begins fresh query for new phase
- [ ] UI always refers to this as "SIEM" — never OpenSearch in any visible label

**MILESTONE 3 COMMIT**: `git add -A && git commit -m "M3 complete: orchestrator UI"`

---

## MILESTONE 4 — Attack Modules: Phases 1–3

### 4.1 — Attack Module Guide
- [ ] Create `attacks/ATTACK_MODULE_GUIDE.md` defining:
  - Required files for every attack module
  - `atlas_mapping.json` schema with all required fields
  - SIEM log event contract (required fields, format)
  - asciinema recording spec (dimensions, timing, content guidelines)
  - Contribution checklist for team members adding new phases

### 4.2 — Phase 1: Recon & AI Pipeline Enumeration
- [ ] Create `attacks/phase1_recon/attack.py`:
  - Enumerate QL-Assist endpoints (`/health`, `/admin`, `/api/schema`, `/chat`)
  - Extract API schema and model information
  - Probe for system prompt via crafted queries
  - Output formatted attacker-style terminal output (realistic, not theatrical)
  - Emit SIEM log events to SIEM as attack executes
- [ ] Create `attacks/phase1_recon/atlas_mapping.json`:
  - `technique_id`: `AML-T0015`
  - `technique_name`: `Reconnaissance`
  - `sub_technique`: `AML-T0035 — LLM Prompt Injection Discovery`
  - `tactic`: `Reconnaissance`
  - `target_service`: `QL-Assist`
  - `delivery`: `pre-recorded`
  - `phase_duration_seconds`: 240
  - `act`: 1
- [ ] Record `attacks/phase1_recon/recording.cast` (final recording)
- [ ] Create `orchestrator/phases/phase_1.json` with all pane content
- [ ] QA: play recording, verify Blue pane log activity, verify GRC risk score is low (pre-attack)

### 4.3 — Phase 2: Model Behavior Fingerprinting
- [ ] Create `attacks/phase2_fingerprint/attack.py`:
  - Crafted probe queries to map model refusal thresholds
  - Attempt system prompt extraction via common injection patterns
  - Document model behavior profile in output
  - Realistic pacing — this should feel like methodical attacker work
- [ ] Create `attacks/phase2_fingerprint/atlas_mapping.json`:
  - `technique_id`: `AML-T0005`
  - `technique_name`: `LLM Meta Prompt Extraction`
  - `tactic`: `ML Attack Staging`
  - `target_service`: `QL-Assist`
  - `delivery`: `pre-recorded`
  - `act`: 1
- [ ] Record final `.cast`
- [ ] Create `orchestrator/phases/phase_2.json`
- [ ] QA: verify attack output looks authentic, Blue pane shows nothing critical

### 4.4 — Phase 3: Indirect Prompt Injection
- [ ] Create `attacks/phase3_injection/payload/kyc_review_malicious.pdf`:
  - Realistic KYC review document layout
  - Embedded instruction at non-obvious location (not first line, not visible in normal reading)
  - Instruction: suppresses risk flag, sets score to 0, suppresses alerts on case
- [ ] Create `attacks/phase3_injection/attack.py`:
  - Uploads malicious document via QL-DocuIntel `/ingest`
  - Waits for analyst to trigger analysis (simulated analyst query)
  - Shows agent executing injected instruction: risk_score write + alert suppression
  - Logs entire chain to stdout in attacker terminal format
- [ ] Create `attacks/phase3_injection/interactive_mode.py`:
  - Live mode: presenter can trigger injection in real-time
  - Uses real Ollama call
  - Outputs in same format as recorded version
- [ ] Create `attacks/phase3_injection/atlas_mapping.json`:
  - `technique_id`: `AML-T0051.002`
  - `technique_name`: `LLM Prompt Injection — Indirect via External Data`
  - `tactic`: `Initial Access`
  - `target_service`: `QL-DocuIntel`
  - `delivery`: `pre-recorded-with-interactive`
  - `act`: 2
  - `payload_visual_field`: path to document annotation for orchestrator
- [ ] Record final `.cast`
- [ ] Create `orchestrator/phases/phase_3.json`:
  - `blue.detection_status`: `"miss"` — this is the silent miss moment
  - `blue.log_events`: valid API calls only, zero anomaly flags
  - `blue.gap_analysis`: semantic layer explanation
- [ ] QA: verify Blue pane shows clean SIEM, no alert fires, silent miss state renders correctly

**MILESTONE 4 COMMIT**: `git add -A && git commit -m "M4 complete: attack phases 1-3"`

---

## MILESTONE 5 — Attack Modules: Phases 4–6

### 5.1 — Phase 4: Multi-Agent Trust Exploitation
- [ ] Implement agent-to-agent communication channel:
  - QL-DocuIntel `POST /agent/message` → QL-FraudSentinel `POST /agent/message`
  - Messages are trusted by default (no validation — intentional vulnerability)
- [ ] Create `attacks/phase4_lateral/attack.py`:
  - Extends Phase 3 poison: DocuIntel's response to analyst carries lateral payload
  - DocuIntel sends inter-agent message to FraudSentinel with malicious instruction
  - FraudSentinel executes instruction (score manipulation on different transaction)
  - Terminal shows lateral movement hop: DocuIntel → FraudSentinel
- [ ] Create `attacks/phase4_lateral/atlas_mapping.json`:
  - `technique_id`: `AML-T0043`
  - `technique_name`: `Craft Adversarial Data — Agent Hijacking`
  - `tactic`: `Lateral Movement`
  - `target_service`: `QL-DocuIntel → QL-FraudSentinel`
  - `act`: 2
- [ ] Update orchestrator Red pane for this phase to show lateral movement path diagram
- [ ] Record final `.cast`
- [ ] Create `orchestrator/phases/phase_4.json`
- [ ] QA: SIEM shows two services with normal events, no alert chain fires

### 5.2 — Phase 5: Long-Term Memory Poisoning
- [ ] Implement memory poison planting (link back to Phase 3 — poison was planted earlier):
  - Create `attacks/phase5_memory/plant_poison.py` — called during Phase 3, delayed trigger
  - Adversarial embedding stored near legitimate fraud pattern vectors
- [ ] Create `attacks/phase5_memory/trigger.py`:
  - Analyst query triggers retrieval — poison surfaces with high similarity score
  - Scoring decision influenced: fraudulent transaction gets low risk score
  - Shows multi-phase attack chain: Phase 3 planted → Phase 5 detonates
- [ ] Create `attacks/phase5_memory/atlas_mapping.json`:
  - `technique_id`: `AML-T0040`
  - `technique_name`: `ML Supply Chain Compromise — Training Data Poisoning`
  - `tactic`: `ML Attack Staging`
  - `target_service`: `QL-FraudSentinel`
  - `act`: 2
- [ ] Memory store visualization for Red pane: simple table showing embedding keys, poison entry highlighted
- [ ] Record final `.cast`
- [ ] Create `orchestrator/phases/phase_5.json`
- [ ] QA: verify poison planted in Phase 3 run still present after reset (persistent volume test)

### 5.3 — Phase 6: Objective Hijacking & Impact (Live Interactive)
- [ ] Create `attacks/phase6_impact/attack.py`:
  - Live mode only — no recording
  - Sends series of transactions with escalating fraud indicators
  - FraudSentinel (poisoned from Phase 5) returns low risk scores on high-risk transactions
  - Shows divergence: expected score vs actual score across 5 transactions
  - Final transaction: $4.2M institutional transfer → scored LOW RISK
- [ ] Create `orchestrator/phases/phase_6.json`:
  - `blue.detection_status`: `"partial"` — some anomalies detectable in Act III defensive mode
  - GRC pane: risk score jumps to 85, FFIEC/GLBA/SOX triggered, board-level notification required
  - Red pane: live terminal feed (not recording)
- [ ] Live terminal in Red pane connects to attack script via websocket
- [ ] QA: run full Phase 6 live, verify LLM response received in < 12 seconds

**MILESTONE 5 COMMIT**: `git add -A && git commit -m "M5 complete: attack phases 4-6"`

---

## MILESTONE 6 — SIEM Detection Layer (OpenSearch + OpenDashboards)

### 6.1 — OpenSearch Bootstrap
- [ ] Create `siem/bootstrap_opensearch.py`:
  - Polls `http://opensearch:9200/_cluster/health` until status is green or yellow (60s timeout)
  - Creates index template for `qfl-events-*` via `PUT /_index_template/qfl-events` with full field mapping
  - Required index fields: `@timestamp`, `service`, `atlas_phase`, `event_type`, `severity`, `session_id`, `agent_id`, `message`
  - Loads and creates OpenSearch alerting monitors from `siem/pipeline_rules/` JSON files via `POST /_plugins/_alerting/monitors`
  - Imports OpenDashboards dashboard from `siem/dashboards/blue_team_dashboard.ndjson` via OpenDashboards saved objects API
  - Creates index pattern in OpenDashboards: `qfl-events-*`
  - Prints summary: indexes created, monitors loaded (N), dashboards imported (N)
- [ ] Test: run bootstrap from zero (empty OpenSearch), verify index template active, monitors loaded, dashboard visible at :5601

### 6.2 — OpenSearch Alerting Monitors (Detection Logic)
- [ ] Create `siem/pipeline_rules/` with OpenSearch alerting monitor JSON definitions:
  - `monitor_01_README.md` — explains intentional gap: no monitors fire for Phases 1-5 by design. This represents the real-world state of an uninstrumented AI pipeline.
  - `monitor_02_semantic_firewall.json` — Act III: triggers on prompt injection signature patterns in `llm_completion` field. DISABLED by default.
  - `monitor_03_agent_identity.json` — Act III: triggers when `agent_id` field is null on any agent action event. DISABLED by default.
  - `monitor_04_trust_chain.json` — Act III: triggers when inter-agent message lacks `trust_token` field. DISABLED by default.
  - `monitor_05_score_anomaly.json` — triggers when `risk_score_delta` field shows drop > 50 in single event. ENABLED — represents the one thing a mature SOC might catch.
- [ ] All monitors use OpenSearch alerting monitor schema (`"type": "monitor"`, `"inputs"`, `"triggers"`)
- [ ] Monitors 02-04 have `"enabled": false` in JSON — bootstrap loads them disabled
- [ ] `siem/pipeline_rules/enable_act3_monitors.py` script enables monitors 02-04 via OpenSearch API (called during Act III transition)

### 6.3 — OpenDashboards Blue Team Dashboard
- [ ] Create OpenDashboards dashboard with the following panels:
  - Live event stream: table visualization, all services, last 15 minutes, sorted by `@timestamp`
  - Event rate graph: line chart, events/minute over time, split by `service`
  - Service breakdown: pie or bar chart, event count per `service` field
  - Alert panel: table of triggered OpenSearch alerting monitors (empty for Phases 1-5)
  - ATLAS technique distribution: terms aggregation on `atlas_phase` field
- [ ] Export dashboard as `.ndjson` to `siem/dashboards/blue_team_dashboard.ndjson`
- [ ] Dashboard title in OpenDashboards: "QFL SIEM — Blue Team Operations" (never "OpenSearch" in the title)
- [ ] Orchestrator Blue tab renders dashboard via OpenDashboards iframe embed OR polls OpenSearch `_search` API directly — decision based on whichever avoids cross-origin issues in the Docker network

### 6.4 — Log Event Validation
- [ ] Create `scripts/validate_logs.py`:
  - Executes each attack phase script in sequence (dry run mode)
  - After each phase, queries OpenSearch for expected log events: `GET /qfl-events-*/_search` filtered by `atlas_phase`
  - Asserts: expected event types present, required fields populated, no null `@timestamp`
  - Asserts: zero alerting monitors triggered for Phases 1-5 (query `GET /_plugins/_alerting/alerts`)
  - Enables Act III monitors, re-runs Phase 5/6 attack, asserts monitors 02-04 now trigger
  - Prints pass/fail per phase with event counts
- [ ] All 6 phases pass validation before M6 marked complete

**MILESTONE 6 COMMIT**: `git add -A && git commit -m "M6 complete: OpenSearch detection layer"`

---

## MILESTONE 7 — Integration Testing

### 7.1 — End-to-End Phase Validation
- [ ] Run each phase individually, verify:
  - Red pane renders correctly (recording plays or live terminal works)
  - Blue pane shows correct detection status (miss/partial/detected)
  - GRC pane shows correct risk score and regulatory flags
  - Attack explainer overlay appears and is accurate
  - Phase transition is clean (no UI artifacts, no stale log events)

### 7.2 — Full 60-Minute Run-Through
- [ ] Run full demo from Phase 1 to Phase 6 without interruption
- [ ] Confirm total time: 55–65 minutes
- [ ] Confirm Phase 3 interactive injection executes in < 8 seconds
- [ ] Confirm Phase 6 live LLM response in < 12 seconds
- [ ] No container crashes during run
- [ ] SIEM dashboard stable throughout

### 7.3 — Cross-Platform Verification
- [ ] Full run verified on Windows (AMD64)
- [ ] Full run verified on Mac M4 (ARM64)
- [ ] `demo_reset.sh` tested on both platforms — completes in < 60 seconds

### 7.4 — Network Resilience
- [ ] Test demo with SIEM disconnected — orchestrator handles gracefully
- [ ] Test demo with Ollama responding slowly (add artificial delay) — UI handles gracefully
- [ ] Verify Phase 6 fallback if LLM response takes > 15 seconds

**MILESTONE 7 COMMIT**: `git add -A && git commit -m "M7 complete: integration testing"`

---

## MILESTONE 8 — Pre-Recording Sessions

### 8.1 — Recording Environment Setup
- [ ] Set terminal: 120 columns, 40 rows on recording machine
- [ ] Install `asciinema` on host: `pip install asciinema`
- [ ] Verify playback in orchestrator asciinema-player component before recording

### 8.2 — Final Recordings
- [ ] Record Phase 1: `asciinema rec recordings/phase_1_recon.cast`
  - Review: realistic pacing, real tool output, no staged errors
  - Approve and commit
- [ ] Record Phase 2: `asciinema rec recordings/phase_2_fingerprint.cast`
  - Review and approve
- [ ] Record Phase 3: `asciinema rec recordings/phase_3_injection.cast`
  - Use real LLM response — do not stage output
  - Review and approve
- [ ] Record Phase 4: `asciinema rec recordings/phase_4_lateral.cast`
  - Review and approve
- [ ] Record Phase 5: `asciinema rec recordings/phase_5_memory.cast`
  - Review and approve
- [ ] Update all `atlas_mapping.json` with correct recording file paths

**MILESTONE 8 COMMIT**: `git add -A && git commit -m "M8 complete: recordings final"`

---

## MILESTONE 9 — Delivery Readiness

### 9.1 — Build Guide
- [ ] Create `BUILD_GUIDE.md`:
  - Prerequisites (Docker Desktop, Ollama, git)
  - Step-by-step setup for Windows
  - Step-by-step setup for Mac M4
  - Troubleshooting section (top 10 issues from testing)
  - Network requirements (localhost only — no internet required during demo)
- [ ] Verify: team member who didn't build it follows guide successfully from zero

### 9.2 — Demo Execution Guide
- [ ] Create `DEMO_EXECUTION_GUIDE.md`:
  - Pre-demo setup checklist (30 minutes before)
  - Opening framing (2-minute audience calibration)
  - Per-phase talking points (what to say, what to point to)
  - Transition scripts between Acts I → II → III
  - Closing frame: the benchmark question ("what's your MTTD for a compromised AI agent?")
  - Timing guide: target minutes per phase
  - Q&A handling guide for common audience questions

### 9.3 — Contingency Plan
- [ ] Create `CONTINGENCY_PLAN.md`:
  - If Phase 6 Ollama call fails: recorded fallback path
  - If SIEM is down: Blue pane offline mode (cached log display)
  - If container crashes mid-demo: fast restart procedure (< 2 minutes)
  - If audience demands live interaction beyond Phase 3: scope management language

### 9.4 — Final QA Sign-Off
- [ ] Full rehearsal run with presenter team
- [ ] Timing confirmed within budget
- [ ] All team members know their phase responsibilities
- [ ] All non-negotiables from CLAUDE.md verified with checkboxes

**MILESTONE 9 COMMIT**: `git add -A && git commit -m "M9 complete: delivery ready"`

---

## BLOCKED TASKS LOG
<!-- Claude Code: if a task is blocked, add an entry here -->

| Task | Reason | Date | Resolution |
|---|---|---|---|
| — | — | — | — |

---

## COMPLETION SUMMARY
<!-- Updated by Claude Code as milestones complete -->

| Milestone | Tasks | Complete | Status |
|---|---|---|---|
| M1 Infrastructure | 8 | 6 | 🟡 (testing deferred to running env) |
| M2 QL Services | 5 | 4 | 🟡 (verification deferred to running env) |
| M3 Orchestrator UI | 8 | 8 | ✅ |
| M4 Attack Phases 1-3 | 4 | 3 | 🟡 (recordings in M8) |
| M5 Attack Phases 4-6 | 3 | 2 | 🟡 (recordings in M8, live test in M7) |
| M6 SIEM Layer | 4 | 2 | 🟡 (log validation + dashboard in M6) |
| M7 Integration | 4 | 0 | ⬜ |
| M8 Recordings | 2 | 0 | ⬜ |
| M9 Delivery | 4 | 0 | ⬜ |
| **TOTAL** | **42** | **29** | 🟡 |
