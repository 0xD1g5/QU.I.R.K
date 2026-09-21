# The email scanner derives its hosts from surviving TLS candidates, which no documentation says

**Filed:** 2026-09-17 (demo-prep, multihost connector coverage)
**Priority:** P2 — silent empty results, and the operator-visible symptom points at the wrong thing
**Status:** open (the multihost config is worked around; the general trap is unfixed)

## The trap

`run_scan.py:3893` derives the email scanner's host list from the **post-fingerprint TLS
candidates**:

```python
email_hosts = list(dict.fromkeys(h for h, _ in tls_targets))
```

So a host that serves *only* mail ports never survives fingerprinting (none of its ports are in
`scan.ports_tls`), never becomes a TLS candidate, and is therefore invisible to the email scanner
— even though it is listed in `targets.cidrs` and `enable_email: true` is set.

Doing everything the connector documentation asks for is not sufficient. A host must first earn a
TLS candidacy.

## How it presented

Two dedicated mail servers were added to the multihost profile. The scan logged:

```
Starting email TLS scans: 147 tasks (21 hosts x 7 ports)
Email scans complete: 0/147 successful
```

`21 hosts` was the tell — the scanner was probing the nginx/httpd estate while the two real mail
servers were absent. Adding 465/993/995 to `ports_tls` fixed it (0/147 -> 7/161), and that fix is
committed with the reasoning in the config, but it is a per-config workaround.

## Why P2 rather than P3

The failure is completely silent: exit 0, a full set of report artifacts, an empty Motion tab, and
no advisory. The only signal is a host count in a log line that an operator has no reason to read
as suspicious.

## Candidate fixes

- Union the derived hosts with any host in `targets` that has a mail port in `ports_tls`, rather
  than depending on TLS candidacy alone.
- Or emit an advisory when `enable_email` is true and the derived host set contains none of the
  configured targets' mail-bearing hosts.
- At minimum, document the derivation in `docs/connector-field-reference.md` under Email — it is
  currently the one connector whose "no detail fields needed" note is true but misleading.
