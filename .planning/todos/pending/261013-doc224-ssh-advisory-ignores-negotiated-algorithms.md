---
type: todo
created: 2026-10-13
source: Phase 224 GC2 re-audit (part 05, docs/report-interpretation.md §5 "SSH quantum planning advisory" row)
priority: medium
area: quirk/engine/findings_evaluator.py (evaluate_endpoints SSH branch)
status: pending
resolves_phase: null
owner: "999.132"
---

# "SSH quantum planning advisory" fires for every SSH service, whatever algorithms it offers

The finding's own description states "This SSH host key or key-exchange algorithm relies on RSA or classical
ECDH", but the evaluator never looks at the algorithms. `evaluate_endpoints` emits it for every endpoint whose
protocol is `SSH` (and no scan error):

- `quirk/engine/findings_evaluator.py:756` `if proto == "SSH":` -> `:757` `findings.append(_build_finding(` with
  `severity="INFO"`, `title="SSH quantum planning advisory"`, and the fixed RSA/ECDH description at `:762-765`.
- The SSH endpoint record carries no algorithm data to check: `quirk/scanner/ssh_scanner.py:57-59` builds it with
  `protocol="SSH"` and `cipher_suite="SSH",  # D-06: SSH marker field`.
- Probe (isolated HOME/XDG, `QUIRK_*` unset): `evaluate_endpoints(cfg, [CryptoEndpoint(host="10.0.0.5", port=22,
  protocol="SSH", cipher_suite="SSH")])` -> `[('INFO', 'SSH quantum planning advisory')]`.

So a server that already negotiates the hybrid post-quantum `mlkem768x25519-sha256` key exchange still gets an
advisory telling the client its key exchange is RSA/ECDH. The recommendation text (`:768-771`) also says to adopt
ML-KEM "when OpenSSH support lands", which is stale: OpenSSH 9.9 added `mlkem768x25519-sha256`
(https://www.openssh.com/txt/release-9.9 -> "This algorithm \"mlkem768x25519-sha256\" is available by default.") and
OpenSSH 10.0 made it the default key agreement (https://www.openssh.com/txt/release-10.0 -> "the hybrid post-quantum
algorithm mlkem768x25519-sha256 is now used by default for key agreement").

docs/report-interpretation.md §5 was narrowed (Phase 224 GC2) to say the advisory is per SSH service and does not
check algorithms; if this todo is fixed, update that row.

## Feasibility & Effort

- **Verdict: LIKELY, effort M.** The evaluator has no algorithm input today (CONFIRMED: `ssh_scanner.py:59` stores
  only the marker). Algorithm data does exist elsewhere: `quirk/scanner/ssh_scanner.py:75` counts
  `audit_data.get("kex", [])`, so ssh-audit output reaches the scanner, but it is not on the `CryptoEndpoint` row the
  evaluator reads. A fix has to carry the negotiated/offered KEX and host-key algorithms to the evaluator (a new
  endpoint field or a lookup), then gate the advisory on a classical-only KEX.
- **Quick partial fix, effort S:** update the recommendation text at `findings_evaluator.py:768-771` to drop "when
  OpenSSH support lands" and name OpenSSH 9.9+/10.0. CONFIRMED by the two release-note quotes above.
- **Unknowns:** whether ssh-audit output is persisted anywhere the evaluator can reach at evaluation time; whether
  CBOM/scoring code also assumes every SSH endpoint is classical (check `quirk/intelligence/evidence.py` SSH counters
  before changing the finding).
- **Spike:** not needed for the text fix; a short spike (read `ssh_scanner.py` end to end) before the gating fix.
