# SIEM Alerting Monitors — Design Intent

## The Intentional Gap (Phases 1–5)

No alerting monitors fire for Phases 1–5 **by design**.

This is not a bug. It represents the real-world state of a mature SOC that has excellent
traditional security tooling but zero instrumentation on their AI pipeline layer.

The audience will see:
- Valid API calls hitting QL-Assist, QL-DocuIntel, QL-FraudSentinel
- Normal HTTP status codes (200 OK)
- Standard tokens_in / tokens_out metrics
- Nothing suspicious by any behavioral or signature-based detection

The SIEM is working perfectly. It sees everything it was designed to see.
It just wasn't designed to see prompt injection in LLM completions,
inter-agent trust exploitation, or memory poisoning.

## Monitor Files

| File | Status | Fires On | Phase |
|---|---|---|---|
| `monitor_02_semantic_firewall.json` | DISABLED (Act III) | Injection signature in `llm_completion` field | Phase 3+ |
| `monitor_03_agent_identity.json` | DISABLED (Act III) | `agent_id` null on agent action events | Phase 4+ |
| `monitor_04_trust_chain.json` | DISABLED (Act III) | Inter-agent message missing `trust_token` | Phase 4+ |
| `monitor_05_score_anomaly.json` | ENABLED | `risk_score_delta` drop > 50 in single event | Phase 3+ |

## Monitor 05 Note

`monitor_05_score_anomaly.json` is the **one thing a mature SOC might catch** —
a sudden, large drop in risk score. But only if they're watching the right metric.
This fires in Phase 3 when the injection forces a risk_score to 0.

In Act III, monitors 02–04 are enabled via:
```
python3 siem/pipeline_rules/enable_act3_monitors.py
```
