---
status: testing
phase: 13-interactive-mode-overhaul
source: [13-01-SUMMARY.md, 13-02-SUMMARY.md]
started: 2026-04-06T00:00:00Z
updated: 2026-04-06T00:00:00Z
---

## Current Test

number: 1
name: No timezone, SNI, or ADCS prompts
expected: |
  Run `python3 run_scan.py` and choose interactive mode.
  You should NOT be asked:
    - "Enter timezone" or any timezone question
    - "Include SNI?" or any SNI question
    - "Enable Windows ADCS?" or any ADCS question
  These values are now auto-detected or hardcoded — no prompt should appear.
awaiting: user response

## Tests

### 1. No timezone, SNI, or ADCS prompts
expected: Run `python3 run_scan.py` and choose interactive mode. You should NOT be asked for timezone (auto-detected from OS), SNI (hardcoded True), or Windows ADCS (removed entirely). None of these prompts should appear.
result: [pending]

### 2. Targets-first prompt order
expected: In interactive mode, the FIRST questions asked should be about scan targets (IP ranges, hosts, domains). Questions about metadata (org name, data classification, output format) should appear LATER, after scanner and connector options.
result: [pending]

### 3. Profile selection numbered menu
expected: During interactive mode, a numbered menu should appear for scan profile selection — something like: 1) Quick  2) Standard  3) Deep. Entering a number (e.g. "2") selects the profile without any free-text parsing.
result: [pending]

### 4. Data classification numbered menu
expected: A numbered menu should appear for data classification with at least 3-4 tiers (e.g. Public, Internal/Confidential, Regulated, Sensitive). Selecting a number maps to the correct classification — the selection should not require typing out the classification name.
result: [pending]

### 5. Connector labels — no stubs, credential warnings
expected: When enabling a cloud connector (e.g. AWS or Azure) in interactive mode, the option label should NOT contain "(stub)". After enabling, a credential warning message should appear (e.g. "Ensure AWS_ACCESS_KEY_ID is set" or similar) to remind the user to configure credentials.
result: [pending]

### 6. Consulting TLS port set applied
expected: After completing interactive mode setup, the scan configuration should use the consulting-grade 17-port TLS set — including non-standard ports like 636 (LDAPS), 6443 (Kubernetes), 8200 (Vault), and database ports (5432, 3306, 1433). A quick way to verify: print or inspect the config after interactive setup, or check any log output showing the port list.
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps

