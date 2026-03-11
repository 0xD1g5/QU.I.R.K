# Phase JSON Schema

Each phase file (`phase_N.json`) defines all content for one attack phase across three persona tabs.

```json
{
  "phase": 1,
  "act": 1,
  "act_name": "THE NEW ATTACK SURFACE",
  "name": "Recon & AI Pipeline Enumeration",
  "atlas_technique": "AML-T0015",
  "target_service": "QL-Assist",
  "default_tab": "red",
  "delivery": "pre-recorded",

  "explainer": {
    "badge": "ATTACK EXPLAINER",
    "atlas_id": "AML-T0015",
    "title": "Recon & AI Pipeline Enumeration",
    "body": "Plain-English description of what this attack does and why.",
    "why_stack_misses": "Why existing EDR/SIEM/UEBA tools miss this attack."
  },

  "red": {
    "terminal_mode": "recording | static | live",
    "terminal_recording": "recordings/phase_1_recon.cast",
    "terminal_lines": ["line1", "line2"],
    "attack_context": {
      "name": "Attack name",
      "atlas_id": "AML-T0015",
      "target": "QL-Assist"
    },
    "payload_visual": {
      "enabled": false,
      "document_path": "attacks/phase3_injection/payload/kyc_review_malicious.pdf",
      "injection_offset": "Page 3, paragraph 4",
      "label": "HIDDEN INSTRUCTION"
    }
  },

  "blue": {
    "detection_status": "miss | partial | detected",
    "gap_analysis": "Why this attack is invisible to existing controls.",
    "log_events": [],
    "control_coverage": [
      { "control": "EDR", "status": "covered" },
      { "control": "SIEM Alerting", "status": "gap" },
      { "control": "LLM Semantic Monitor", "status": "blind" }
    ]
  },

  "grc": {
    "risk_score": 15,
    "risk_severity": "LOW",
    "control_failures": [
      {
        "status": "fail | warn | ok",
        "description": "Description of the control failure or gap.",
        "framework": "NIST AI RMF | FFIEC | SOX | GLBA | SR 11-7"
      }
    ],
    "regulatory_flags": [
      {
        "regulation": "NIST AI RMF",
        "status": "TRIGGERED | UNDER REVIEW | COMPLIANT | GAP IDENTIFIED",
        "status_class": "triggered | under-review | compliant | gap"
      }
    ]
  }
}
```

## detection_status Values

| Value | Blue Tab Behavior |
|---|---|
| `"miss"` | Tab dims to near-black. Log stream frozen on last entry. No label. No explanation. |
| `"partial"` | Log stream active. Some anomalies visible. No alert fires. Amber status. |
| `"detected"` | Alert fires. Log stream active and highlighted. Red alert banner. |
