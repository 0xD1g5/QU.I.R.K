---
type: todo
created: 2026-10-12
source: Phase 224 gap closure A (docs/report-interpretation.md section 6, CBOM quantum safety labels)
priority: medium
area: quirk/cbom/classifier.py
status: pending
resolves_phase: null
---

# DNSSEC ECDSA algorithms are rated NIST level 1 and 3, so the CBOM labels them quantum-safe

`quirk/cbom/classifier.py:190-191` classifies the DNSSEC algorithm names:

    "ecdsap256sha256": (CryptoPrimitive.SIGNATURE, 1, 128),      # DNSSEC alg 13
    "ecdsap384sha384": (CryptoPrimitive.SIGNATURE, 3, 192),      # DNSSEC alg 14

Run live 2026-10-12:

    classify_algorithm("ecdsap256sha256")[1] -> 1   quantum_safety_label(1) -> 'quantum-safe'
    classify_algorithm("ecdsap384sha384")[1] -> 3   quantum_safety_label(3) -> 'quantum-safe'
    classify_algorithm("ecdsa")[1]           -> 0   'quantum-vulnerable'

ECDSA is broken by Shor's algorithm exactly like the plain `ecdsa` / `ecdsa-sha2-nistp256` table entries (level 0), so a
DNSSEC zone signed with algorithm 13 or 14 appears in the CBOM as a quantum-safe algorithm. The sibling RSA DNSSEC names
(`rsasha256`, `rsasha512`) are `None` (unknown), and the guide's section 6 rule is "level 0 = quantum-vulnerable".

- [ ] Set the two ECDSA DNSSEC entries to level 0 (and re-check `ed25519`/`ed448`, which are already 0).
- [ ] Decide whether `rsasha256`/`rsasha512` (level `None`) should also be 0.
- [ ] Regenerate the CBOM golden fixtures (`REGEN_CBOM_FIXTURES=1 ... -m slow`) and update any DNSSEC expected results
      under `labs/`.

## Feasibility & Effort

**CONFIRMED** by calling `classify_algorithm` and `quantum_safety_label` directly (output above) and reading
`classifier.py:176-192`. Effort **S**: two table values plus fixture regeneration. Unknown: whether the levels were an
intentional mapping of RFC 8624 "recommended" status onto NIST levels (the code comment cites RFC 8624 / 9905), which
would be a different quantity from quantum security. **Spike**: not needed.
