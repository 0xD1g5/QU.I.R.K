# Phase 20: Kerberos Scanner - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-04-09
**Phase:** 20-kerberos-scanner
**Mode:** discuss
**Areas analyzed:** impacket API approach, kerberos_targets format, AES-128 classification, Samba DC chaos lab image

## Gray Areas Presented

| Area | Options | Recommendation |
|------|---------|---------------|
| impacket API | `sendReceive()` + raw ASN.1 vs `getKerberosTGT()` wrapper | `sendReceive()` + ASN.1 |
| kerberos_targets format | Plain hostnames vs `host:realm` pairs vs dict | Plain hostnames |
| AES-128 (etype 17) classification | SAFE vs HIGH | HIGH |
| Samba DC image | Community image vs custom Dockerfile | Custom Dockerfile |

## Assumptions Presented

### impacket API Approach
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Use `sendReceive()` + raw ASN.1, not `getKerberosTGT()` | Confident | impacket's own `GetNPUsers.py` uses this pattern; DNSSEC scanner analogously crafts raw DNS queries |

### kerberos_targets Format
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Plain hostnames, realm auto-derived from KDC response `crealm` | Confident | `dnssec_targets` uses plain domain names; realm is embedded in KDC error response |

### AES-128 Classification
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| AES-128 (etype 17) → HIGH (not SAFE) | Likely | Grover's algorithm halves effective security to ~64 bits; KERB-02 silent on etype 17; QUIRK's quantum-readiness mission favors conservative classification |

### Samba DC Chaos Lab
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| Custom Dockerfile (`debian:bookworm-slim` + samba) over community image | Confident | Requires `ntlm auth = ntlmv1-permitted` + `kerberos encryption types = all` in smb.conf; community images don't reliably expose these flags; matches BIND9/SimpleSAMLphp chaos lab pattern |

## Corrections Made

No corrections — all 4 recommendations confirmed by user.

## External Research

None required — codebase provided sufficient evidence for all decisions.
