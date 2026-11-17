---
type: todo
created: 2026-11-08
title: SAML connector records any HTTP answer as 'ran'
source: Phase 235.4 (5.28.2 release walkthrough and go/no-go)
priority: high
area: quirk/scanner/saml_scanner.py:104 (also check jwt_scanner.py:358)
status: pending
resolves_phase: 238
owner: null
---

# SAML connector records any HTTP answer as 'ran'

Kind: product

Ledger note: .planning/LEDGER.md is not on this branch. This item belongs in LEDGER.md (id `261108-saml-non-metadata-answer-reads-ran`) when PR #70 lands.

## Observed

The SAML connector records any HTTP response as answered, so a metadata URL returning 404/401/403/500, an SSO login page or unparseable XML reads "ran, 0 results", log-only, not a scan error: the most likely production misconfiguration. Fix: non-200 or non-metadata content becomes failed with a reason (and counts as a scan error); add a lab or unit target that answers with junk; check JWT for the same pattern. Disclosed as announcement S8b. Locked today by `tests/test_saml_scanner.py::test_saml_outcome_non_200_is_answered` (235.3 D-05), which must be revisited. Next release.

## Evidence

operator at go/no-go 2026-11-08 (see 235.4-announcement-checks.md) (Phase 235.4 evidence directory, untracked).

## Feasibility & Effort

Medium (half a day to a day): change outcome classification, revisit the D-05 test, add a junk-answer fixture, audit JWT.

## Resolution (2026-11-17)

Fixed by Phase 238 (IDENT-07): a SAML target counts as answered only when it returned SAML 2.0 metadata or an OIDC discovery document; a 404, an HTML login page, other XML or unparseable content records `unexpected_response` with a named detail (for example "not SAML metadata (HTML page)"), and a connector with no qualifying target reads skipped with reason `unexpected-response` and counts as a scan error. The JWT connector had the same pattern and is fixed the same way (answered only on a JWKS; an uncredentialed 401/403 reads missing-credentials). Commits main 82ebe634 (PR #86 merge; be2e6ff8, cabe5589, b8708400, 55c550db, 7579c4ac). Tests: tests/test_saml_scanner.py::test_saml_outcome_non_200_is_unexpected_response (renamed from the 235.3 D-05 lock), tests/test_saml_scanner.py::test_saml_outcome_html_page_is_unexpected_response, tests/test_jwt_scanner.py::test_jwt_outcome_non_200_everywhere_is_unexpected_response, tests/test_connector_coverage_e2e.py::test_saml_html_target_skips_unexpected_response. Live: 238-evidence/live-identity-cert.txt (saml_scanning skipped, unexpected-response). Behaviour change: SAML/JWT targets that answered junk used to read ran with no results; they now read skipped and lower the score.
