---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-CONFIG-A-* (configuration.md Code-Signing Certificate Connector)
priority: low
area: quirk/scanner/codesign_scanner.py, quirk/util/safe_exc.py
status: pending
resolves_phase: null
---

# Code-signing scanner logs LDAP DNs through `safe_str()`, which does not strip control characters

`quirk/scanner/codesign_scanner.py` logs `safe_str(user_dn)` / `safe_str(base_dn)` (T-95-03 "information-disclosure
mitigation"). `quirk.util.safe_exc.safe_str` takes an *exception*, returns `"<ClassName>: <message>"`, and only
collapses to the class name when the message matches `_SENSITIVE_PATTERNS`. Given a string it prefixes `str: ` and
leaves control characters untouched. Reproduced 2026-10-12: `safe_str('CN=ev\nil\x1b[31m,DC=x')` returns
`'str: CN=ev\nil\x1b[31m,DC=x'`, so an LDAP DN containing a newline or an ANSI escape reaches the log line verbatim
(log forging / terminal-escape injection by whoever controls a directory entry). The old `docs/configuration.md` said
the DNs and CNs were "sanitized via safe_str() (control characters and newlines are removed)"; the doc now says only
what `safe_str` does.

- [ ] Run LDAP-derived strings through `quirk.util.sanitize.sanitize_scanner_text` or a small control-character
      stripper before logging, or pass `%r` of the value.
- [ ] Add a test that a DN containing `\n` and `\x1b` is escaped in the log record.
- [ ] Then restore the "control characters are removed" sentence in `docs/configuration.md`.

## Feasibility & Effort

**CONFIRMED** (live call above; call sites at `codesign_scanner.py` `safe_str(user_dn)` and `safe_str(base_dn)`).
Effort **S**: a helper plus two call-site edits and one test. Severity is low because the scanner logs to the
operator's own console and the DN comes from the operator's own directory. No spike needed.
