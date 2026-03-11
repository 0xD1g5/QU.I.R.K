# ROADMAP.md — Operation Ghost Wait: Sovereign Edition
## Tier 1 Demo Track — Milestone Plan

---

> **This file is the source of truth for project progress.**
> Update milestone status as work completes.
> Claude Code reads this file at the start of every session to understand current state.

---

## Project Summary

| Item | Detail |
|---|---|
| **Demo Name** | Operation Ghost Wait: Sovereign Edition |
| **Track** | Tier 1 — Advanced / Mature Organization |
| **Total Demo Duration** | 60 minutes |
| **Target Audience** | CISO, Technical Directors, Sr. Security Engineers (financial sector) |
| **Delivery Format** | Live presenter + pre-recorded hybrid |
| **First Delivery Target** | Global financial institution workshop |
| **Build Team** | 3 people |
| **Build Timeline** | 3 weeks |

---

## Milestone Overview

```
Week 1: Foundation         Week 2: Attack Modules        Week 3: Polish & Rehearsal
─────────────────          ───────────────────────       ──────────────────────────
M1 Infrastructure     →    M4 Attack Phases 1-3     →    M7 Integration Testing
M2 QL Services        →    M5 Attack Phases 4-6     →    M8 Pre-recording Sessions
M3 Orchestrator UI    →    M6 SIEM Detection Layer  →    M9 Demo Rehearsal & Cutover
```

---

## MILESTONE 1 — Core Infrastructure
**Target**: End of Week 1, Day 2
**Status**: 🟡 CODE COMPLETE — runtime testing deferred to running environment

### Goals
- Docker Compose stack running cleanly on both Windows (AMD64) and Mac M4 (ARM64)
- Ollama serving llama3.2:3b on host, reachable from all containers
- Network topology established, all services able to communicate
- SIEM stack up and receiving test log events
- Environment reset and health check scripts functional

### Success Criteria
- [ ] `docker compose up -d` completes with 0 errors on Windows
- [ ] `docker compose up -d` completes with 0 errors on Mac M4 (ARM64 images only)
- [ ] `curl http://localhost:8001/health` returns 200 (QL-Assist)
- [ ] `curl http://localhost:8002/health` returns 200 (QL-DocuIntel)
- [ ] `curl http://localhost:8003/health` returns 200 (QL-FraudSentinel)
- [ ] OpenSearch healthy: `curl http://localhost:9200/_cluster/health` returns `green` or `yellow`
- [ ] OpenDashboards (SIEM UI) loads at http://localhost:5601
- [ ] Test log event POSTed to OpenSearch `qfl-events-*` index and retrievable via search API
- [ ] `scripts/health_check.sh` exits 0 with all-green output
- [ ] `scripts/demo_reset.sh` returns environment to clean baseline state

---

## MILESTONE 2 — QL Services (Attack Surfaces)
**Target**: End of Week 1
**Status**: 🟡 CODE COMPLETE — end-to-end injection verification deferred to running environment

### Goals
- Three AI services running with real Ollama LLM inference
- Each service generates structured SIEM-ready log events for all operations
- QL-DocuIntel has a functional RAG pipeline with vector storage
- QL-FraudSentinel has a functional persistent memory store (attack target)
- Services are intentionally vulnerable — injection points exist but are not obvious

### QL-Assist Requirements
- [ ] FastAPI with `/chat` endpoint — accepts user message, returns LLM response
- [ ] `/admin` endpoint visible (recon target)
- [ ] System prompt contains over-privileged instructions (visible via prompt leak)
- [ ] All requests logged to SIEM with: session_id, user_id, tokens_in, tokens_out, latency
- [ ] Vulnerable to direct prompt injection (Phase 1/2 attack surface)

### QL-DocuIntel Requirements
- [ ] `/ingest` endpoint — accepts PDF/TXT document upload
- [ ] RAG pipeline: document → chunking → embedding → vector store
- [ ] `/analyze` endpoint — retrieves context from vector store, calls LLM, returns analysis
- [ ] **Injection vulnerability**: document content placed directly into LLM context without sanitization
- [ ] All operations logged to SIEM with: document_id, chunk_count, retrieval_results, llm_action
- [ ] Visible risk score write capability (attack target for Phase 3)

### QL-FraudSentinel Requirements
- [ ] `/score` endpoint — accepts transaction data, returns risk score + recommendation
- [ ] `/memory` endpoint — agent memory store (read/write, persistent across sessions)
- [ ] `/alert` endpoint — generates fraud alert (can be suppressed by agent action)
- [ ] **Memory vulnerability**: memory store content trusted and injected into scoring context
- [ ] All scoring decisions logged to SIEM: transaction_id, score_before, score_after, agent_action
- [ ] Agent-to-agent communication channel with QL-DocuIntel (lateral movement path)

### Enterprise Environment Requirements
- [ ] QFL intranet page running at :8080 (internal portal, org chart, AI policy docs)
- [ ] Mail server running at :1025/:1143 (phishing simulation target)
- [ ] Virtual workstation accessible via VNC at :5901 (analyst simulation)

---

## MILESTONE 3 — Orchestrator UI (Presenter Interface)
**Target**: End of Week 1
**Status**: ✅ COMPLETE

### Goals
- Single unified intelligence briefing frame — no multi-window, no app switching
- Phase rail collapses during content, expands on transition
- Three persona tabs (Red / Blue / GRC) — one active at a time, presenter-controlled
- Attack explainer overlay works
- Keyboard controls functional including tab switching
- Runs in any modern browser (Chrome, Firefox, Safari)

### Success Criteria
- [ ] Phase rail: collapsed state is a thin progress bar (~8px); expanded state shows all 6 phases with ATLAS IDs
- [ ] Phase rail expands on phase transition, auto-collapses after 4 seconds
- [ ] Three persona tabs visible at top of content frame: RED TEAM | BLUE TEAM | GRC
- [ ] Only one tab active at a time — full-frame content, no split panes
- [ ] Act indicator (top-right) updates correctly per phase
- [ ] RED TEAM tab: attack context card + terminal (live or asciinema playback) + payload visualizer
- [ ] BLUE TEAM tab: SIEM log stream + detection status + gap analysis + control coverage
- [ ] GRC tab: risk meter + control failures (framework tags) + regulatory mapping
- [ ] Silent miss: Blue tab dims to near-black, log stream frozen on last normal entry, no label, no alert
- [ ] Attack explainer overlay: appears on phase entry, semi-transparent over active tab, dismissible
- [ ] Keyboard: Space/→ (advance phase), ← (prev phase), 1/2/3 (switch tabs), P (pause), E (explainer), R (reset), F (fullscreen)
- [ ] Status bar always visible: phase counter, target service, ATLAS technique, elapsed timer, nav controls
- [ ] CNXN brand palette applied correctly throughout
- [ ] Responsive at 1920×1080 and 2560×1440

---

## MILESTONE 4 — Attack Modules: Phases 1–3
**Target**: End of Week 2, Day 2
**Status**: 🟡 CODE COMPLETE — recordings deferred to M8, live verification in M7

### Phase 1 — Recon & AI Pipeline Enumeration (AML-T0015, AML-T0035)
- [ ] Attack script enumerates QL-Assist endpoints, extracts API schema
- [ ] Probes for model information, system prompt leakage
- [ ] Generates realistic attacker terminal output
- [ ] `atlas_mapping.json` complete with all required fields
- [ ] asciinema recording produced (120col × 40row)
- [ ] Phase JSON definition complete for orchestrator
- [ ] SIEM receives log events from targeted service during attack

### Phase 2 — Model Behavior Fingerprinting (AML-T0005)
- [ ] Attack script sends crafted probe queries to map model behavior boundaries
- [ ] Extracts system prompt fragments via prompt injection probes
- [ ] Documents behavioral profile (refusal patterns, injection receptivity)
- [ ] `atlas_mapping.json` complete
- [ ] asciinema recording produced
- [ ] Phase JSON definition complete

### Phase 3 — Indirect Prompt Injection via Document (AML-T0051.002)
- [ ] Attack script crafts malicious PDF with embedded instruction at non-obvious offset
- [ ] Document uploaded via legitimate QL-DocuIntel `/ingest` endpoint
- [ ] Agent retrieves document, instruction executes: risk_score written to 0, alert suppressed
- [ ] SIEM shows: valid session, valid API calls, zero anomaly flags (silent miss)
- [ ] Payload visualizer shows document with hidden instruction highlighted
- [ ] Interactive mode: presenter can trigger injection live with real LLM response
- [ ] `atlas_mapping.json` complete
- [ ] asciinema recording produced
- [ ] Phase JSON definition complete

---

## MILESTONE 5 — Attack Modules: Phases 4–6
**Target**: End of Week 2
**Status**: 🟡 CODE COMPLETE — recordings deferred to M8, Phase 6 live test in M7

### Phase 4 — Multi-Agent Trust Exploitation (AML-T0043)
- [ ] Demonstrates agent-to-agent lateral movement: QL-DocuIntel → QL-FraudSentinel
- [ ] Poisoned DocuIntel response carries malicious instruction in inter-service payload
- [ ] FraudSentinel receives and executes instruction from "trusted" internal agent
- [ ] Both agents show normal behavioral signatures in SIEM
- [ ] Lateral movement path visible in orchestrator Red pane
- [ ] `atlas_mapping.json` complete
- [ ] asciinema recording produced
- [ ] Phase JSON definition complete

### Phase 5 — Long-Term Memory Poisoning (AML-T0040)
- [ ] Attack plants adversarial embedding in QL-FraudSentinel memory store
- [ ] Poison embedding semantically proximate to legitimate fraud pattern records
- [ ] Trigger query causes poison to surface in retrieval → influences scoring
- [ ] Time-delayed: poison planted in Phase 3, surfaces in Phase 5 (multi-phase narrative)
- [ ] Memory store visualization in Red pane showing embedding space (simplified)
- [ ] `atlas_mapping.json` complete
- [ ] asciinema recording produced
- [ ] Phase JSON definition complete

### Phase 6 — Objective Hijacking & Impact (AML-T0048)
- [ ] Live interactive mode — real Ollama calls
- [ ] Demonstrates agent pursuing corrupted objective (minimize false positives → approve fraudulent txns)
- [ ] Shows real-time scoring impact: legitimate fraud cases getting low-risk scores
- [ ] GRC pane shows regulatory impact cascade (FFIEC, GLBA, SOX trigger)
- [ ] Closes loop: ties attack impact to board-level reporting framework
- [ ] Phase JSON definition complete

---

## MILESTONE 6 — SIEM Detection Layer (OpenSearch + OpenDashboards)
**Target**: End of Week 2
**Status**: 🟡 PARTIAL — bootstrap + monitors + pipeline rules done; dashboard ndjson + log validation pending running env

### Goals
- OpenSearch receiving and indexing all QL service log events
- OpenDashboards configured as the Blue Team SIEM view (embedded in orchestrator Blue tab)
- Detection rules implemented for what WOULD catch these attacks (surfaced in Act III)
- Detection gap analysis is accurate and technically honest — defensible to a mature SOC audience

### Success Criteria
- [ ] `siem/bootstrap_opensearch.py` configures index templates, alerting monitors, and dashboards via OpenSearch/OpenDashboards API on first run
- [ ] All 6 attack phases generate log events visible in OpenSearch `qfl-events-*` index
- [ ] Phases 1–5: zero alerting monitors fire (accurate silent miss — OpenSearch confirms no alerts)
- [ ] Act III defensive mode: semantic firewall alerting monitors DO fire when enabled via bootstrap flag
- [ ] OpenDashboards Blue Team dashboard exportable as JSON to `siem/dashboards/` (reproducible)
- [ ] Blue tab in orchestrator polls OpenSearch API for live log events — no hardcoded tool names in UI
- [ ] Control coverage matrix (Covered / Gap / Blind) is technically defensible to a mature SOC audience

---

## MILESTONE 7 — Integration Testing
**Target**: Week 3, Day 1–2
**Status**: ⬜ NOT STARTED

### Goals
- Full 60-minute run-through without presenter intervention
- All pre-recorded phases play back cleanly
- All live phases execute with real LLM calls
- SIEM events appear correctly timed in orchestrator
- No container crashes, no orphaned processes

### Success Criteria
- [ ] Full demo run completes in 55–65 minutes on Windows
- [ ] Full demo run completes in 55–65 minutes on Mac M4
- [ ] Zero container restarts during demo run
- [ ] asciinema recordings play back in sync with orchestrator phase state
- [ ] Phase 3 interactive injection executes in < 8 seconds
- [ ] Phase 6 live Ollama response received in < 12 seconds
- [ ] SIEM dashboard visible throughout without needing refresh
- [ ] `demo_reset.sh` fully restores baseline in < 60 seconds

---

## MILESTONE 8 — Pre-Recording Sessions
**Target**: Week 3, Day 2–3
**Status**: ⬜ NOT STARTED

### Goals
- Final asciinema recordings produced with real LLM responses
- Recordings reviewed for timing, authenticity, and pacing
- No "staged" feeling — real tool behavior visible

### Success Criteria
- [ ] Phase 1 recording: final, reviewed, committed
- [ ] Phase 2 recording: final, reviewed, committed
- [ ] Phase 3 recording: final, reviewed, committed (interactive mode also tested)
- [ ] Phase 4 recording: final, reviewed, committed
- [ ] Phase 5 recording: final, reviewed, committed
- [ ] All recordings play back at correct terminal dimensions (120×40)
- [ ] No visible artifacts, cursor glitches, or timing gaps > 3 seconds

---

## MILESTONE 9 — Rehearsal & Delivery Readiness
**Target**: Week 3, Day 4–5
**Status**: ⬜ NOT STARTED

### Goals
- Presenter team rehearsal with full 60-minute run
- Build guide and demo execution guide documented
- Environment verified on both Windows and Mac
- Backup plan documented if live Phase 6 fails

### Deliverables
- [ ] `BUILD_GUIDE.md` — complete environment setup from zero
- [ ] `DEMO_EXECUTION_GUIDE.md` — presenter script, timing cues, talking points per phase
- [ ] `CONTINGENCY_PLAN.md` — fallback procedures if live elements fail
- [ ] Rehearsal completed and timing confirmed
- [ ] CNXN team sign-off on demo quality

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Ollama response latency in Phase 6 | Medium | High | Pre-warm model, set 15-second timeout, fallback to recorded response |
| ARM64 container compatibility failure | Medium | Medium | Test every new image on M4 before committing to compose |
| SIEM bootstrap takes too long on game day | Low | High | Pre-bootstrap before client arrives, include healthcheck in startup script |
| Audience asks to "try it themselves" | Medium | Low | Phase 3 interactive mode satisfies this — scope-limited injection |
| asciinema playback sync issues | Low | Medium | All recordings tested at final terminal dimensions before M8 sign-off |
| Live LLM produces unexpected output in Phase 6 | Medium | Medium | Real-time output is a feature — brief it as authenticity. Brief presenter team. |

---

## Definition of Done

The project is complete when:
1. All 9 milestones show ✅ complete
2. Full demo run verified on both target machines
3. BUILD_GUIDE.md tested by a team member who didn't build the environment
4. DEMO_EXECUTION_GUIDE.md reviewed and approved by lead presenter
5. All code committed and pushed to project repository
