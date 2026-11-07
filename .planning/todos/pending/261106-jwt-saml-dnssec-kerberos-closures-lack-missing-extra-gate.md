---
type: todo
created: 2026-11-06
title: JWT/SAML/DNSSEC/Kerberos closures lack a missing-extra pre-gate
source: Phase 235.3 research (closure-level extra-gate gaps)
priority: low
area: run_scan.py, quirk/scanner/jwt_scanner.py, saml_scanner.py, dnssec, kerberos
status: pending
resolves_phase: null
owner: null
---

# JWT/SAML/DNSSEC/Kerberos closures lack a missing-extra pre-gate

## Observed

The JWT, SAML, DNSSEC and Kerberos phase closures have no missing-extra pre-gate. When httpx / lxml / dnspython /
impacket are absent the scanner returns early. After 235.3 the fail-closed classifier records the phase as
skipped/failed with "no outcome recorded": honest, but it names the wrong reason (it should say the optional extra
is not installed and give the install hint).

Related findings from 235.3 execution: plan 06 found the K8s SDK-missing paths also record no outcome; plan 05
found Azure `_scan_blob_encryption` is called nowhere in quirk/ (pre-existing dead code, so blob encryption is
never scanned).

## Fix sketch

Add an `optional_extra.REGISTRY`-driven pre-gate per closure that records a skipped outcome with the extra's
install hint; same for the K8s SDK-missing paths. Decide whether to wire or delete Azure `_scan_blob_encryption`.

## Feasibility & Effort

Small to medium. Pattern already exists for other connectors. About 1 plan; the Azure item needs a separate
wire-or-delete decision.
