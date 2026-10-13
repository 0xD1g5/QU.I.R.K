---
type: todo
created: 2026-10-13
source: Phase 224 gap closure round 2 (ARCH), docs/cbom-guide.md Step 5 protocol components; ledger rows DCL-CBOM-0116
priority: low
area: quirk/cbom/builder.py
status: pending
resolves_phase: null
---

# The PQC probe's ADVISORY row produces a phantom, empty `protocol:tls` CBOM component

`run_scan.py:2849` (`_run_pqc_phase`) writes a `CryptoEndpoint(protocol="ADVISORY", ...)` for every TLS target when
X25519MLKEM768 was not detected and the scanning host's `openssl` does not list ML-KEM. Those rows are part of the
`endpoints` list (`run_scan.py:4054` `+ pqc_endpoints`) that `write_reports` passes to `build_cbom`
(`quirk/reports/writer.py:962`).

`build_cbom` Pass 3 has no skip for `ADVISORY`, so the row falls into the TLS default branch
(`quirk/cbom/builder.py:1041` `# TLS (default)`) and is emitted as `protocol:tls:<host>:<port>`
(`builder.py:1066`) with no version and no cipher suites. When a real TLS endpoint exists for the same host and port, the
CBOM then holds two components with the same name; the library replaces the colliding bom-ref with a random one.

Reproduced in-process 2026-10-13:

    build_cbom([CryptoEndpoint(host="10.0.0.9", port=443, protocol="TLS", tls_version="TLSv1.3",
                               cipher_suite="TLS_AES_256_GCM_SHA384"),
                CryptoEndpoint(host="10.0.0.9", port=443, protocol="ADVISORY",
                               service_detail="pqc-hybrid-detected|advisory=openssl-too-old")])
    -> components: AES-256-GCM, SHA-384,
       ('protocol:tls:10.0.0.9:443', 'crypto/protocol/tls/10.0.0.9:443'),
       ('protocol:tls:10.0.0.9:443', 'BomRef.0202713...')

The same default-branch fall-through applies to any other non-skipped, non-TLS protocol value that reaches `build_cbom`
(for example `HTTP`, `UNKNOWN`, `CLOSED`, `ERROR` if such rows are in `endpoints`). Related but separate: the scoring side
of the same advisory row is tracked in `261012-doc224-pqc-probe-old-openssl-advisory-counted-as-hybrid.md`.

- [ ] Add `ADVISORY` (and audit the other non-transport protocol literals) to the Pass 2 / Pass 3 skip tuples, or switch
      Pass 3 to an allow-list of transport protocols.
- [ ] Add a builder test: TLS + ADVISORY on the same host:port yields exactly one protocol component.
- [ ] Regenerate the CBOM golden fixtures if any change (`REGEN_CBOM_FIXTURES=1 ... -m slow`).
- [ ] Drop the caveat sentence from `docs/cbom-guide.md` Step 5 once fixed.

## Feasibility & Effort

**CONFIRMED** by the in-process run above and by reading `quirk/cbom/builder.py:1022-1040` (the Pass 3 skip tuple, which
lists `REST_FUZZ`/`OPENAPI` but not `ADVISORY`) and `run_scan.py:2840-2860`. Effort **S**: one literal in two skip tuples
plus a test; **M** if switching to an allow-list surfaces other protocols that relied on the default branch (the email and
broker TLS literals such as `REDIS-TLS`/`KAFKA-TLS` would need listing). Unknown: whether any consumer relies on the
empty component. **Spike**: not needed.
