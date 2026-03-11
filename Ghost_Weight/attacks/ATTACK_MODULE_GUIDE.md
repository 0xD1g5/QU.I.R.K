# Attack Module Guide — Operation Ghost Wait

Every attack phase is a self-contained module under `attacks/phaseN_*/`.
This guide defines the required files, schemas, and conventions for all attack modules.

---

## Required Files Per Module

```
attacks/phaseN_name/
├── attack.py              ← Attack execution script
├── atlas_mapping.json     ← MITRE ATLAS metadata (required)
├── payload/               ← Attack payloads, documents
│   └── .gitkeep
└── recording.cast         ← asciinema recording (produced in M8, gitignored)
```

Phases with live interactive mode also include:
```
└── interactive_mode.py    ← Live demo variant (Phase 3, Phase 6)
```

---

## atlas_mapping.json Schema

```json
{
  "technique_id": "AML-T0051.002",
  "technique_name": "LLM Prompt Injection — Indirect via External Data",
  "sub_technique": "",
  "tactic": "Initial Access",
  "target_service": "QL-DocuIntel",
  "delivery": "pre-recorded-with-interactive",
  "phase_duration_seconds": 420,
  "act": 2,
  "pause_after_line": 15,
  "payload_visual_field": "attacks/phase3_injection/payload/kyc_review_malicious.pdf",
  "recording_file": "recordings/phase_3_injection.cast",
  "terminal_dimensions": { "cols": 120, "rows": 40 }
}
```

### Required Fields

| Field | Type | Description |
|---|---|---|
| `technique_id` | string | MITRE ATLAS technique ID |
| `technique_name` | string | Full technique name |
| `tactic` | string | ATLAS tactic |
| `target_service` | string | Which QL service is targeted |
| `delivery` | string | `pre-recorded`, `live`, `pre-recorded-with-interactive` |
| `act` | int | 1, 2, or 3 |

### Optional Fields

| Field | Description |
|---|---|
| `sub_technique` | Sub-technique ID if applicable |
| `phase_duration_seconds` | Target duration for this phase |
| `pause_after_line` | Line number in recording where presenter should pause |
| `payload_visual_field` | Path to document for payload visualizer |
| `recording_file` | Path to asciinema .cast file |

---

## SIEM Log Event Contract

All attack scripts that generate SIEM activity must emit events with these fields:

### Required Fields

| Field | Type | Description |
|---|---|---|
| `@timestamp` | ISO 8601 | Event timestamp (UTC) |
| `service` | string | Originating service name (e.g., `ql-docuintel`) |
| `atlas_phase` | int | Phase number (1–6) |
| `event_type` | string | Event classification |
| `severity` | string | `INFO`, `LOW`, `MED`, `HIGH`, `CRIT` |
| `message` | string | Human-readable event description |

### Optional Fields (include when relevant)

| Field | Description |
|---|---|
| `session_id` | Analyst session ID |
| `agent_id` | AI agent identity |
| `document_id` | Document being processed |
| `transaction_id` | Transaction being scored |
| `risk_score` | Numeric risk score |
| `risk_score_delta` | Change in risk score |
| `llm_action_taken` | Action taken by LLM |
| `llm_completion` | LLM output (truncated to 500 chars) |
| `memory_keys_used` | Memory entries that influenced scoring |
| `trust_token` | Agent trust token (may be empty for attack phases) |

---

## asciinema Recording Spec

- **Dimensions**: 120 columns × 40 rows — set before recording:
  ```bash
  printf '\033[8;40;120t'   # resize terminal (Linux/Mac)
  # Or: stty cols 120 rows 40
  ```
- **Tool**: `asciinema rec recordings/phase_N_name.cast`
- **Content**: Real tool output — do NOT stage or fake AI responses
- **Pacing**: Realistic attacker pacing — methodical, not rushed
- **LLM responses**: Must be genuine Ollama inference output
- **Output path**: `recordings/phase_N_name.cast`

---

## Contribution Checklist

Before marking a phase module complete:

- [ ] `attack.py` runs without errors from project root
- [ ] `atlas_mapping.json` present with all required fields
- [ ] SIEM receives expected log events during attack execution
- [ ] Blue Team pane shows correct detection_status (no false alerts for Phases 1–5)
- [ ] Phase JSON (`orchestrator/phases/phase_N.json`) populated with accurate content
- [ ] asciinema recording produced at 120×40 (M8 task)
- [ ] Recording reviewed for authenticity and pacing
