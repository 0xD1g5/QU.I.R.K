---
phase: 103-siem-export
reviewed: 2026-05-25T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - quirk/siem/formatter.py
findings:
  critical: 0
  warning: 1
  info: 1
  total: 2
status: issues_found
---

# Phase 103: Code Review Report (Iteration 3 — Final)

**Reviewed:** 2026-05-25
**Depth:** standard
**Files Reviewed:** 1 (`quirk/siem/formatter.py`)
**Status:** issues_found

## Summary

This iteration audits `quirk/siem/formatter.py` only — the scope directed by the
auto-loop prompt. The iteration-2 Critical (CR-01: port-field CEF extension injection)
has been correctly remediated. A full field-by-field audit of every value that reaches
the assembled CEF line is performed below. No Critical issues remain.

### Port-injection fix verification (CR-01 from iteration 2)

`to_cef_finding` now coerces `port` in two steps (lines 144-148):

```python
try:
    _port_int = int(finding.get("port"))
    safe_port = _port_int if 0 < _port_int <= 65535 else ""
except (TypeError, ValueError):
    safe_port = ""
```

`safe_port` is therefore either a Python `int` in [1, 65535] or the empty string `""`.
`str()` of a bounded int produces only ASCII digits. `str("")` produces `""`. Neither
can carry `=`, `\`, newline, or space. The fix is **correct and complete** — no residual
injection path exists through `dpt`.

### Full field-by-field audit

| CEF position | Variable | Source / escape path | Verdict |
|---|---|---|---|
| Header: device vendor | literal `QUIRK` | static string | Safe |
| Header: device product | literal `scanner` | static string | Safe |
| Header: version | `escaped_version` | caller `version` arg → `_cef_escape_header` | Safe |
| Header: SignatureID | `signature` | `safe["category"]` → `_cef_escape_header` | Safe |
| Header: Name | `name` | `safe["title"]` → `_cef_escape_header` | Safe |
| Header: Severity | `cef_sev` | `_CEF_SEVERITY` dict lookup → `int` | Safe |
| Extension: `dhost` | `dhost` | `safe["host"]` → `_cef_escape_extension` | Safe |
| Extension: `dpt` | `dpt` | `safe["port"]` (validated int or `""`) → `str()` | Safe |
| Extension: `cs1` | `cs1` | `safe["category"]` → `_cef_escape_extension` | Safe |
| Extension: `cs1Label` | literal `Category` | static string | Safe |
| Extension: `cs2` | `cs2` | `safe["description"]` (truncated 256) → `_cef_escape_extension` | Safe |
| Extension: `cs2Label` | literal `EvidenceSummary` | static string | Safe |
| Extension: `msg` | `msg` | `safe["recommendation"]` or `safe["description"]` (both truncated 256) → `_cef_escape_extension` | Safe |

Both escape helpers apply backslash escaping before pipe/equals escaping (correct ordering,
avoids double-escape). `_cef_escape_header` processes `\r\n` before `\r` before `\n`
(correct). `_cef_escape_extension` processes `\r\n` before `\r` before `\n` (correct).
`=` is correctly NOT escaped in header fields and IS escaped in extension values (per
ArcSight CEF Implementation Standard, section 5).

One Warning and one Info item remain.

---

## Warnings

### WR-01: Empty `dpt=` Extension Value When Port Is Absent or Out-of-Range

**File:** `quirk/siem/formatter.py:193,203`

**Issue:** When `safe_port` is `""` (port absent, non-numeric, or outside [1, 65535]),
`dpt` is emitted as the empty string, producing the extension fragment:

```
dhost=10.0.0.1 dpt= cs1=...
```

A `key=` pair with an empty value is not a defined case in the ArcSight CEF
Implementation Standard. Compliant parsers handle it without error, but a significant
fraction of real-world SIEM ingest pipelines — including the Splunk `cef` sourcetype,
QRadar DSM auto-detect, and some syslog-ng CEF parsers — either drop the event, emit
a parse warning, or misattribute subsequent fields. Because QUIRK generates many
finding types that have no associated port (source-code findings, KMS findings,
compliance findings), a large proportion of events will trigger this condition.

**Fix:** Omit `dpt` from the extension entirely when the port is not known:

```python
# In build_cef_event, replace the monolithic ext f-string (lines 201-207):
ext_parts = [f"dhost={dhost}"]
if safe["port"] != "":
    ext_parts.append(f"dpt={dpt}")
ext_parts += [
    f"cs1={cs1}",
    "cs1Label=Category",
    f"cs2={cs2}",
    "cs2Label=EvidenceSummary",
    f"msg={msg}",
]
ext = " ".join(ext_parts)
```

This produces well-formed, unambiguous CEF for portless findings while preserving
correct behaviour for findings with a valid port.

---

## Info

### IN-01: Spaces in Extension String Values Are Not Escaped — Known CEF Ambiguity

**File:** `quirk/siem/formatter.py:64-82` (`_cef_escape_extension`)

**Issue:** The CEF Implementation Standard does not require spaces to be escaped in
extension values. `_cef_escape_extension` correctly omits space escaping per spec.
However, CEF extension parsing relies on the `key=value key=value` pattern, where the
boundary between a value and the next key is inferred by recognising the next `word=`
token. A description or recommendation that contains a substring resembling a CEF
key-value pair — e.g., `"set dpt=443 for this host"` — will cause naive parsers to
misparse the value boundary. Compliant ArcSight/LEEF parsers are immune; this is a
known, documented CEF ambiguity rather than a bug in this code.

**Fix:** No change required for spec compliance. If interoperability issues are
reported against a specific SIEM, the remediation is to HTML-percent-encode spaces in
extension values or switch to the quoted-value extension format. Adding a note to the
module docstring or `_cef_escape_extension` docstring would alert future maintainers:

```python
# NOTE: Spaces are intentionally NOT escaped — CEF spec does not require it.
# Compliant parsers use the next key= token as the boundary. If a target SIEM
# misbehaves, consider percent-encoding spaces (%20) in extension values.
```

---

## Prior Findings Summary

| Iteration | Finding | Status |
|---|---|---|
| 1 | CR-01: header newline injection | FIXED (iter 1) |
| 1 | CR-02: TCP framing missing LF | FIXED (iter 1) |
| 1 | WR-01: protocol validation missing | FIXED (iter 1) |
| 1 | WR-02: isinstance guard in hook | FIXED (iter 1) |
| 1 | WR-03: redundant safe_str | FIXED (iter 1) |
| 1 | WR-04: exit codes 2/3 | FIXED (iter 1) |
| 2 | CR-01 (renumbered): port extension injection | FIXED (iter 3) |
| 3 | WR-01: empty dpt= value | OPEN |
| 3 | IN-01: space ambiguity in extension values | OPEN |

---

_Reviewed: 2026-05-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 3 (final)_
