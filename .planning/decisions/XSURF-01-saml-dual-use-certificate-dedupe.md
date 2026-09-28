# XSURF-01 — SAML dual-`use` certificate dedupes on (host, port, cert serial)

**Status: DECIDED, 2026-09-27.**

---

## The decision

A SAML IdP that publishes a `KeyDescriptor` per `use` (`signing` and `encryption`) for the same
underlying key currently produces **two** CRITICAL findings for **one** weak certificate, from
`quirk/dashboard/api/routes/scan.py::_derive_identity_findings` (defined at `:419`, with
`_saml_key_use` at `:398`). XSURF-01 dedupes on the tuple **`(host, port, cert serial)`**. One
certificate is one asset; two findings for one asset is double-counting, not two distinct pieces of
evidence.

The serial is already available with no scanner change: `quirk/scanner/saml_scanner.py` embeds it
as a `serial=` token in the pipe-delimited `CryptoEndpoint.service_detail` string, at the same two
construction sites that embed `use=`:

```
quirk/scanner/saml_scanner.py:277  service_detail=f"{entity_id}|use=signing|serial={cert_info['serial']}"
quirk/scanner/saml_scanner.py:308  service_detail=f"{entity_id}|use=encryption|serial={cert_info['serial']}"
```

`serial=` can be parsed out of `service_detail` exactly the way `_saml_key_use` already parses
`use=` out of the same string — no new field, no schema change, no scanner change.

### The rejected alternative

ROADMAP Phase 210 Success Criterion 1 offered a second option: keep both rows, but give each an
accurate, distinct title so the reader is not misled about what `use` the row describes. This is
**rejected**. Two rows for one weak key still inflates the CRITICAL-count input to
`_consequence_ceiling()` (`quirk/intelligence/scoring.py:272`, consumed at `:674`) regardless of how
accurately each row is titled — the cap function counts findings, not distinct assets. The roadmap
names this exact inflation as the entire 19-vs-15 headline-score gap between the dashboard and
report pipelines for the reproducing scan. Fixing the titles without fixing the count would leave
the headline numbers just as divergent as before, only with more truthful labels on the divergence.
Accurate-but-duplicated evidence is still duplicated evidence.

### Safety argument — dedupe cannot suppress a genuine distinct finding

Because the dedupe key includes the certificate **serial**, not just `(host, port)`, two SAML
KeyDescriptors on the same host:port that carry genuinely **different** certificates (different
serials) still produce two separate findings. Collision requires the same host, same port, and the
same certificate serial — which is definitionally the same certificate. The only way this dedupe
key could ever suppress a real, distinct finding is if two administratively different weak
certificates on the same endpoint happened to share a serial number, which would itself be a
certificate-issuance collision far outside SAML scanning's threat model, not a false negative
introduced by this decision. Read against the actual construction code above: `serial=` is sourced
directly from `cert_info['serial']`, one value per parsed certificate object, so two distinct
certificate objects can never collapse to the same key.

## Where the dedupe lives

Per CONTEXT D-02, the dedupe is implemented in the shared evaluator,
`quirk/engine/findings_evaluator.py::evaluate_identity_endpoints()` (the D-05 extraction target),
which `quirk/dashboard/api/routes/scan.py::_derive_identity_findings()` becomes a **caller** of,
rather than in the dashboard route directly. That module already exports four sibling evaluators
(`evaluate_endpoints`, `evaluate_email_endpoints`, `evaluate_broker_endpoints`,
`evaluate_codesign_endpoints`), composed once in `run_scan.py:4077-4094`; a fifth sibling for
identity findings is the pattern this codebase already uses, and it is what lets the CLI pipeline
and the dashboard pipeline share one answer instead of two.

The rejected alternative here is implementing the dedupe inside the dashboard route only, and
adding a parity test to keep a second, hand-written CLI-side implementation honest against it. That
is explicitly rejected (CONTEXT D-06): **two implementations of the same synthesis logic is the
defect this phase exists to close**, not something to compensate for with an additional test. The
dashboard route currently has this logic and the CLI pipeline does not — a parity test bolted onto
two divergent implementations papers over the actual bug (XSURF-02) instead of fixing it.

## The second counter — this will not self-heal

`quirk/intelligence/evidence.py`'s `saml_weak_signing_count` is an **independent** counter from
finding emission. It is initialized at `:128`, and incremented at two separate `+= 1` sites:

```
quirk/intelligence/evidence.py:240   saml_weak_signing_count += 1
quirk/intelligence/evidence.py:242   saml_weak_signing_count += 1
```

Both increments happen while iterating raw `CryptoEndpoint` rows directly — this counter never
reads `finding_list` at all. It is surfaced at `:498` and consumed at `:508` to compute
`identity_saml_weak_signing_ratio = saml_weak_signing_count / total_endpoints`, which feeds the
score (`quirk/intelligence/scoring.py:98`, weight `8.0`).

Because this counter iterates endpoint rows independently of finding emission, **deduping the
finding-emission path (the section above) changes `identity_saml_weak_signing_ratio` by exactly
zero.** A dedupe that only touches `evaluate_identity_endpoints()` and stops there will produce a
findings list with the double-count removed, while the score computed from `evidence.py` still
reflects two weak-key rows for one certificate. Per CONTEXT D-03, this is explicitly in scope for
this phase: `evidence.py`'s counter must dedupe on the **same** `(host, port, cert serial)` tuple.
This is not this plan's implementation work — it is owned by **plan 210-03** in this phase's wave
sequence, and is named here so that plan does not have to rediscover it.

## Success Criterion 1's title clause is already satisfied on main

ROADMAP Success Criterion 1 ends: "...whichever is chosen, the `use=encryption` row no longer says
'signing'." This clause is **already true on `main`**, verified before any code in this phase was
touched:

```
$ grep -n "def _derive_identity_findings\|def _saml_key_use\|Weak SAML encryption certificate\|Weak SAML signing certificate" quirk/dashboard/api/routes/scan.py
398:def _saml_key_use(service_detail: str) -> Optional[str]:
419:def _derive_identity_findings(endpoints: list[CryptoEndpoint]) -> list[IdentityFinding]:
539:                        title=f"Weak SAML encryption certificate: {alg}-{size}",
551:                        title=f"Weak SAML signing certificate: {alg}-{size}",
```

Line `539` already emits `Weak SAML encryption certificate: {alg}-{size}` for the `use=encryption`
branch, and line `551` emits the distinct `Weak SAML signing certificate: {alg}-{size}` for the
`use=signing` branch. No title confusion exists on `main` today. This fact is **recorded, not
re-fixed** — no title text changes ship in this phase for this clause. When the dedupe above
collapses the two rows into one, the surviving row keeps the title of the `use` it actually
describes (the extraction preserves the literal f-string `title=` at each call site per D-07; see
that decision's own scope for the parity-gate reason this must not be "cleaned up" into a shared
variable).

## Scope boundary

This decision does **not** change `totals.endpoints` semantics, `total_endpoints` denominators, or
any ratio denominator definition. Deduping the SAML dual-`use` certificate reduces the numerator
(finding/counter occurrences) for one weak key, not what any ratio divides by. The denominator
rewrite is out of scope for this phase and is tracked separately as Phase 211 (`DENOM-*`). Do not
conflate the two: a future reader tempted to "also fix the denominator while touching this code"
should stop and route that work to Phase 211 instead.
