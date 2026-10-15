---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-OPS (fork A4); ledger row DCL-OPS-A-1326 (docs/operators-guide.md §7.3 compliance CI gates)
priority: medium
area: quirk/compliance/__init__.py (COMPLIANCE_MAP / UNMAPPED_TITLES), tests/test_compliance_title_join.py
status: pending
resolves_phase: null
owner: "999.128"
---

# The compliance title-join gate is xfailed, and the orphan set has grown from 3 to 7

`tests/test_compliance_title_join.py::test_every_emitted_title_is_mapped_or_allowlisted` is the gate that should fail
when a finding title has no compliance mapping. It is decorated `@pytest.mark.xfail(..., strict=False)`
(`tests/test_compliance_title_join.py:23`, `:32`) with a TRIAGE-149 reason naming three code-signing titles. Because
the xfail is non-strict, any number of new orphans pass silently. A live run of the test body today:

```
collect_emitted_titles() - COMPLIANCE_MAP - UNMAPPED_TITLES ->
['Code-signing certificate expired: ', 'Code-signing certificate expiring within 90 days: ',
 'Code-signing certificate uses weak algorithm: ', 'OIDC RS-family algorithm: ',
 'SHA-1 algorithm URI detected in SAML metadata', 'Weak SAML encryption certificate: -',
 'Weak SAML signing certificate: -']
```

So four more titles (SAML x3, OIDC x1) went unmapped after the xfail was added, and none of these findings carry
compliance references in reports. The operators-guide previously said the gate "fails when an emitted finding title is
not in COMPLIANCE_MAP or UNMAPPED_TITLES"; it now says the check is xfailed and names the seven.

- [ ] Map each of the seven titles in `COMPLIANCE_MAP` (or add to `UNMAPPED_TITLES` with a reason).
- [ ] Remove the xfail so the gate blocks again; if an xfail must stay, make it `strict=True` against an exact set.
- [ ] Revert the operators-guide caveat in §7.3 once the gate is live.

## Feasibility & Effort

- **CONFIRMED** by running the test's own `collect_emitted_titles()` against `COMPLIANCE_MAP`/`UNMAPPED_TITLES`
  (output above) and reading `tests/test_compliance_title_join.py:23-45`.
- **LIKELY** effort **S-M**: the code is a data edit, but choosing correct PCI/HIPAA/FIPS/SOC 2/ISO controls for SAML and
  OIDC findings is a compliance-content decision that must be re-verified against sources (and re-dates
  `last_verified` only if actually re-read). **UNKNOWN**: whether SAML/OIDC titles were intentionally left unmapped.
  No spike needed.
