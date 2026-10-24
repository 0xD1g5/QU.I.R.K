---
type: todo
created: 2026-10-24
source: Phase 230 review round R22 (WR-01, WR-02, IN-01, IN-02), the 230-REVIEW-R22.md findings; R22 reported BLOCKERS 0
priority: low
area: tests/test_kerberos_probe_principal_config.py (_kernel_peer, the generated sweep, test_ip_refusals_name_their_rule), quirk/scanner/kerberos_scanner.py (0.0.0.0/8 comment)
status: pending
resolves_phase: null
owner: "999.136"
---

# Kerberos target sweep: make the kernel check prove it ran, and correct one comment

Phase 230 closed at R22 with no blocker. These are test-strength and wording items. None of them changes scanner behaviour.

- [ ] **WR-01:** the kernel-peer check can pass without comparing anything.
  - `_kernel_peer` catches every `OSError` around `socket()`, so `EMFILE` or a sandbox `EACCES` would switch the check off silently.
  - The sweep's `checked > 1000` counts accepted targets, not kernel comparisons. R22 measured 259 comparisons on macOS and 3 on Linux with `--network none`.
  - Fix: count the comparisons and assert at least one (loopback is always routable). Skip only on `EAFNOSUPPORT` or `EPROTONOSUPPORT`, and re-raise anything else.
- [ ] **WR-02:** the `0.0.0.0/8` comment in `_invalid_target_reason` says "Linux refuses it". That is wrong.
  - The `ENETUNREACH` seen offline comes from having no route at all. With a route, Linux 5.3+ connects to `0.1.2.3` as unicast, as R22 measured with `route_lo.py`.
  - The refusal is still correct, because RFC 1122 makes `0/8` source-only.
  - Fix: reword the comment to "RFC 1122 source-only; macOS and current Linux both send it out the default route".
- [ ] **IN-01:** the disjunct `want.ipv4_mapped == kgot` never fires. A mapped target uses an AF_INET6 socket, which reports a mapped peer, so plain equality always holds.
  - Fix: assert `kgot == want`, and drop the comment that describes the clause R21 removed.
- [ ] **IN-02:** the message for a bare `0.0.0.0` is not pinned by any test.
  - Fix: add `("0.0.0.0", "unspecified")` and `("0.0.0.1", "this network")` to `test_ip_refusals_name_their_rule`.

## Feasibility & Effort

- **CONFIRMED.** R22 measured every item, with its scripts kept under `/Volumes/Digs-1TB/tmp-pytest-230/r22work/`.
- Effort: **XS**. It is test and comment edits only.
- Verify on macOS and on Linux 3.11 without impacket. The `python:3.11-slim` recipe is in `230-REVIEW-R17.md`'s resolution.
