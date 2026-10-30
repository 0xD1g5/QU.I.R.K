---
type: todo
created: 2026-10-15
source: Phase 228 code review (.planning/phases/228-cross-surface-score-parity/228-REVIEW.md), WR-06
priority: medium
area: quirk/scanner/email_scanner.py:459-468, quirk/intelligence/evidence.py:50-65 (_is_unanswered_email_probe)
status: pending
resolves_phase: null
owner: "999.131"
---

# Unreachable mail ports (no route, DNS failure) still count as plaintext

XSURF-08 as written ("a mail port that refused the connection") is met, and timeouts were added. But the scanner maps only errno 111/113 to `CONNECTION_REFUSED`; `ENETUNREACH` (101 Linux / 51 macOS), macOS `EHOSTUNREACH` (65) and `socket.gaierror` set `scan_error` with an empty blocker, so the row reaches the SMTPS/IMAPS/POP3S branch with empty `tls_version` and ticks `motion_email_plaintext_count` and the STARTTLS-missing counter. The service never spoke, which is the D-14 class. Fix: classify on no bytes received (a `NO_RESPONSE` blocker), with an `ENETUNREACH`-shaped test row.

Deferred by the operator at Phase 228 close (2026-10-15): CR-01, WR-07 fixed in-phase (dab89ffc, 3b1d286c);
this item was triaged out of Phase 228's scope. Full evidence and the suggested fix are in the review section named
in `source`.
