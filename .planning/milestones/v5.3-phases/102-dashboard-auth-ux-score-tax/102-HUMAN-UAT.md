---
status: partial
phase: 102-dashboard-auth-ux-score-tax
source: [102-VERIFICATION.md]
started: 2026-05-24T00:00:00Z
updated: 2026-05-24T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Login form renders on unauthenticated browser visit
expected: Centered Card with "Dashboard Login" heading, "API Token" password field, and "Unlock Dashboard" button — no silent 401, no dashboard content.
result: [pending]

### 2. Wrong token shows inline error
expected: Inline error "Invalid token. Check your token and try again." appears below the input; input cleared and refocused; dashboard not loaded.
result: [pending]

### 3. Correct token loads the full dashboard
expected: Sidebar and main content render; no login form remains.
result: [pending]

### 4. Sign out clears token and returns to login form
expected: localStorage quirk_api_token removed (DevTools Application tab); login form re-displayed.
result: [pending]

### 5. Mid-session 401 bounces to login form
expected: After rotating the token server-side, the next API call triggers a 401 which clears localStorage and returns to the login page automatically.
result: [pending]

### 6. Auth-disabled passthrough skips login form
expected: With empty security.api_token and no QUIRK_API_TOKEN env var, dashboard loads directly without the login form.
result: [pending]

### 7. quirk token generate / rotate live round-trip
expected: Token written to config.yaml security.api_token; old token stops working after rotate; config.yaml other keys preserved; QUIRK_API_TOKEN env-var precedence note printed when set.
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0
blocked: 0

## Gaps
