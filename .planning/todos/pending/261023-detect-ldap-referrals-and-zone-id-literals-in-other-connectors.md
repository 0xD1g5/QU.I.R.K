---
type: todo
created: 2026-10-23
source: Phase 230 review round R16 (WR-03; the gate half of CR-01), the 230-REVIEW-R16.md findings
priority: high
area: quirk/scanner/adcs_scanner.py, quirk/scanner/smime_scanner.py, quirk/scanner/codesign_scanner.py, quirk/util/target_trust.py (is_target_trusted)
status: pending
resolves_phase: null
owner: "999.136"
---

# Other connectors follow LDAP referrals to unchecked hosts, and the trust gate takes a non-ASCII zone id as an IP literal

Phase 230 closed both defects for the Kerberos scanner only.

## 1. LDAP referrals: AD CS would re-bind with its credentials to an unchecked host

ldap3's defaults are `auto_referrals=True` and `allowed_referral_hosts=[('*', True)]`, so a directory's referral is followed to any host. Phase 230 R15 CR-03 measured this on loopback for the Kerberos LDAP leg and turned referrals off there.

Three scanners still use the defaults:
- `adcs_scanner.py:246`, with `Connection` at `:248` and `:253`;
- `smime_scanner.py:132`;
- `codesign_scanner.py:268`.

R16 read ldap3 2.9.1 (`strategy/base.py:774-778`): on a referral, the AD CS scanner would re-bind with `adcs_user`/`adcs_password` to the referred host. That host was never checked by `enforce_trusted_targets`, so the configured credential would be sent to it.

- [ ] Pass `allowed_referral_hosts=[]` to `ldap3.Server` and `auto_referrals=False` to `ldap3.Connection` in all three.
- [ ] Add a loopback test per scanner: a directory that refers elsewhere causes zero connections to the referred port, and for AD CS no bind there. The template is R15's `ldap_referral.py`, kept under `/Volumes/Digs-1TB/tmp-pytest-230/r15work/`.
- [ ] Replace the hand list above with a run-time scan: every `ldap3.Server(` and `ldap3.Connection(` in `quirk/` passes both arguments.

## 2. The trust gate takes a non-ASCII IPv6 zone id as an IP literal

- **The defect:** `ipaddress` accepts any zone id. `is_target_trusted` therefore treats `fe80::1%ı.attacker.example` as an IP inside `fe80::/10` and resolves nothing.
- **Why it matters:** `getaddrinfo` IDNA-encodes the non-ASCII string into a host-name lookup (`xn--fe80::1%-0kb.attacker.example`). So any connector that passes the string to the resolver contacts a host the gate never resolved.
- **Already fixed:** the Kerberos scanner now refuses a non-ASCII IP literal (Phase 230 R16).

- [ ] In `is_target_trusted`, treat an IP literal as an IP only if it is ASCII. Otherwise fail closed.
- [ ] Add a gate test covering the R16 cases (`fe80::1%ı.attacker.example`, `fe80::1%enı`, `::ffff:1.2.3.4%é`).

## Feasibility & Effort

- **Item 1:** the risk is CONFIRMED for the Kerberos leg (loopback measurement). For AD CS it is LIKELY, from an ldap3 source read; it was not measured. Effort is **S** per scanner, plus one loopback test helper.
- **Item 2:** CONFIRMED by R16's end-to-end run through `enforce_trusted_targets`. Effort is **S**. Fail-closed for every connector, so the dashboard is unaffected.
