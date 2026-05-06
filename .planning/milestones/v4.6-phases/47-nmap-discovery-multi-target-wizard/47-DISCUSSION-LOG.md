# Phase 47: Nmap Discovery + Multi-Target Wizard — Discussion Log

**Date:** 2026-05-03
**Mode:** discuss (default)

## Areas Selected
- Target ingestion semantics
- Nmap UX & defaults
- 10k probe-budget warning
- CBOM JSON validation rollout

## Q&A

### Target ingestion semantics

**Q1: How should the wizard accept multi-target input — one prompt or several?**
- One smart prompt, syntax-routed (Recommended) ← chosen
- Three separate optional prompts
- One prompt, no mixing

**Q2: When --targets-file (CLI) and config-file targets.fqdns/cidrs are both set, what happens?**
- CLI replaces config (Recommended) ← chosen
- Merge (union, dedup)
- Hard error if both set

**Q3: What should be allowed inside a targets file?**
- Permissive: hosts, IPs, CIDRs, # comments, blank lines (Recommended) ← chosen
- Strict: hostnames/IPs only

### Nmap UX & defaults

**Q4: How should the wizard prompt for nmap discovery?**
- One global yes/no (Recommended) ← chosen
- Per-target prompt
- Auto-on if target count > N

**Q5: When nmap binary is absent, how should QUIRK behave?**
- Phase 45-style coverage_gap INFO + fall back to CONSULTING_TLS_PORTS (Recommended) ← chosen
- Plain stderr warning + same fallback
- Hard error if explicitly requested, soft warn if defaulted

**Q6: How should --max-parallelism be configured?**
- Hard-coded 100 (Recommended) ← chosen
- Config-tunable with 100 default

### 10k probe-budget warning

**Q7: How should the >10k probe-budget warning behave?**
- Soft warn + interactive y/N confirm; auto-proceed in non-TTY (Recommended) ← chosen
- Soft warn + always proceed
- Hard block; require --yes flag

**Q8: What counts as 'ports' in the budget calculation?**
- Resolved post-config port list (Recommended) ← chosen
- Wizard's explicitly-entered ports only

**Q9: Is 10,000 the right threshold?**
- Keep 10,000 — locked by success criterion (Recommended) ← chosen
- Make it configurable, default 10k

### CBOM JSON validation rollout (user-added scope)

**Q10: How should the cyclonedx extras change be applied?**
- Replace [validation] with [json-validation] (Recommended) ← chosen
- Keep [validation], add [json-validation] alongside
- Move to [validation,json-validation] explicitly

**Q11: Where does CBOM JSON validation run, and how does it fail?**
- After write in cbom/writer.py; soft-fail with WARN finding (Recommended) ← chosen
- After write; hard-fail (raise + nonzero exit)
- Pre-write (validate in-memory before serializing)

**Q12: What if the json-validation extra is uninstalled at runtime?**
- Phase 45 coverage_gap INFO finding + skip validation (Recommended) ← chosen
- Treat as required — keep as hard pyproject dep

## Deferred Ideas
None raised.

## Claude's Discretion (deferred to research/planning)
- Exact name and shape of binary-probe helper in `optional_extra.py`
- Exact wording of all advisory finding messages
- Where in the scan orchestrator the probe-budget guard is invoked
- Whether to introduce `quirk/util/targets.py` for the parser or co-locate in `interactive.py`
- Exact CycloneDX JSON schema version to validate against
