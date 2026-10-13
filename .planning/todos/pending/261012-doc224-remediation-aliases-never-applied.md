---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-CONFIG-A-* (configuration.md Remediation Aliases)
priority: medium
area: quirk/config.py, quirk/intelligence/closure.py, quirk/intelligence/burndown.py
status: pending
resolves_phase: null
---

# `remediation_aliases` is parsed into `AppConfig` but no code reads it

`config_from_dict` builds `AppConfig.remediation_aliases` (`quirk/config.py`), and `tests/test_remediation_aliases_config.py`
checks the parsing rules, but `grep -rn "remediation_aliases\|\.aliases" quirk run_scan.py --include='*.py'` finds no
consumer outside `quirk/config.py`: the re-scan burndown/closure code (`quirk/intelligence/burndown.py`,
`closure.py`) never applies the mapping, so a finding that moved between identities is still reported as two
unrelated findings whatever the operator wrote. The old `docs/configuration.md` described the key as the mechanism
that lets "re-scan burndown match findings that moved"; the doc now says it is parsed and validated only.

- [ ] Decide: wire the alias map into the burndown/closure identity matching (the original Phase 179 intent), or
      mark the key reserved.
- [ ] If wired, add a burndown test where an aliased host's finding is matched across two scans.
- [ ] Then restore the behaviour description in `docs/configuration.md` (Remediation Aliases) and add it to the
      operators guide's burndown section.

## Feasibility & Effort

**CONFIRMED** by the negative grep above (re-run it before starting). Effort **M**: the identity-matching code needs
an alias-normalising step on both scan sides plus tests. Unknown: whether a consumer exists in a branch not merged
here; check `git log --all -S"remediation_aliases"` first. A short spike reading `closure.py` is worthwhile.
