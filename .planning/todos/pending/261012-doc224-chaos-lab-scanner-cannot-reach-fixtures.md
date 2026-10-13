# Chaos-lab fixtures the scanner cannot reach from the host: hwcompat-http (20222), ldaps code-signing (389), email, fuzz-target (20100), root-config DNSSEC zones

**Filed:** 2026-10-12 (Phase 224 plan 06, docs/chaos-lab.md audit)
**Priority:** P2 — two documented lab expectations cannot occur in a normal host-side scan
**Status:** open

## What happens

Two lab services publish a host port the scanner never probes:

1. **`hwcompat-http`** publishes `20222:80`. `quirk/scanner/hardware_scanner.py:34` hardcodes
   `_HTTP_MGMT_PORTS = (443, 8443, 8080, 80)`. An offline run of `fingerprint_one` against a listener
   serving the lab's iLO5 headers returned `HPE / iLO5 / http_mgmt / high / partial` on port 8080 and
   `Unknown` on an ephemeral port, so a lab scan never fingerprints this service. The SNMP sibling
   (`hwcompat-snmp`) was already worked around by adding a second `161:161/udp` mapping
   (`docker-compose.yml`, 139-08 comment); `hwcompat-http` has no equivalent.
2. **`ldaps`** (Phase 95 code-signing fixture) publishes only `636:636`. The code-signing scanner
   (`quirk/scanner/codesign_scanner.py::_bind_and_search_codesign`) opens a plaintext, anonymous
   `ldap3.Server(host, port)` connection and never sets `use_ssl`, so it cannot talk to 636, and host
   port 389 is published only by the unrelated `kerberos` profile. The oracle's own example target
   (`ldap://localhost:636`) cannot work either.

3. **`email`** (found in the gap-closure pass, 2026-10-12). The profile publishes Postfix/Dovecot on 30025/30465/30587/30143/30993/30110/30995, but `quirk/scanner/email_scanner.py` (`EMAIL_PORTS`, line 81, expanded per host by `scan_email_targets`) probes only the fixed ports 25/465/587/143/993/110/995 and the config has no port-override key, so a scan of `127.0.0.1` never reaches the lab. The oracle's four findings exist only after the harness rewrites host ports back to the standard ports (`labs/email/expected_results.md`, "Expected Findings"). The `multihost` profile (`mh-postfix`, `mh-dovecot`) is the only end-to-end path. Fix options: a `connectors.email_ports`-style override (M), or publish the standard ports on a second loopback alias (S, collides with host mail daemons).

4. **`fuzz-target`** (added 2026-10-13, Phase 224-17; found by GC-B2). The fixture serves plain HTTP on
   `localhost:20100` (`docker-compose.yml` `ports: "20100:8000"`), but the CLI never fuzzes it:
   `run_scan.py:3260` builds the fuzz base URL as `https://<first configured fqdn>` or
   `https://localhost` (no scheme or port override), and `--targets-file` rejects
   `http://localhost:20100` (`apply_targets_file_override` raises `ValueError: Invalid target`; a token
   with `/` is parsed as a CIDR and `localhost:20100` is not a valid hostname). `--openapi-spec` only
   chooses the spec, not the base URL. So every UAT-96 command against the lab, and the former
   chaos-lab "Validation scan" block, cannot reach the fixture; only a direct `run_fuzz_scan(...,
   base_url="http://localhost:20100")` call can. `docs/chaos-lab.md` and the oracle state the limit
   (GC-B2), and `docs/UAT-SERIES.md` UAT-96-05 was re-dispositioned from SKIP ("live service not
   available") to `GAP` in 224-17. Fix options: a `--fuzz-base-url` flag or a config key (S-M, needs
   the scope gate to accept an explicit http:// loopback target under `--allow-internal-targets`), or
   serve the fixture over TLS on 443 behind a second loopback alias (S, collides with host 443).
5. **Root `config.yaml` DNSSEC targets** (added 2026-10-13, 224-17). `config.yaml:73-75` sets
   `dnssec_targets` to `weak.example.com` / `unsigned.example.com`, but the lab's bind9 serves only
   `weak.chaos.local`, `safe.chaos.local`, `broken.chaos.local` and `unsigned.chaos.local`
   (`quantum-chaos-enterprise-lab/bind9/zones.conf`). With `dnssec_resolver: 127.0.0.1:15353` the
   scanner asks the lab for zones it is not authoritative for. `tests/test_phase89_lab_config_identity.py`
   only checks the list is non-empty, so it stays green. Fix: point the targets at the `*.chaos.local`
   zones (S; the oracle's dnssec section now lists them).

`docs/chaos-lab.md` now states all three limits instead of promising the findings (the email limit is the "Reachability note" in section 3.18).

## Fix

Pick one per item. For `hwcompat-http`: add a published mapping onto a probed port (`8080:80` is the
smallest change) or give the HTTP management probe a per-host port override. For `ldaps`: publish the
plaintext listener on a non-colliding host port (for example `38989:389`) and point the doc example at it,
or let the code-signing scanner use TLS for `ldaps://` targets. Whichever is chosen must update `lab.sh`'s
README/oracle rows per the CLAUDE.md chaos-lab rule.

## Feasibility & Effort

- Feasibility: CONFIRMED. Both root causes were reproduced from source (`hardware_scanner.py:34`,
  `codesign_scanner.py` `_bind_and_search_codesign`, `docker-compose.yml` `ports:` blocks) and the HTTP
  half by an offline `fingerprint_one` experiment.
- Effort: S for each compose-side fix (one `ports:` line plus README/oracle rows); M if the scanner side
  is chosen (needs a config surface and tests). fuzz-target: S-M (a base-URL override plus a scope-gate
  test). Root config.yaml DNSSEC targets: S (two list entries).
- Unknowns: whether 8080 on the host is free on operator machines (the 161/udp precedent assumed it was
  checked with `lsof`); whether the plaintext LDAP listener has anonymous bind enabled in the bitnami image
  (the adcs service sets `LDAP_ALLOW_ANON_BINDING`, ldaps does not).
- Spike needed: no, except one live `docker compose up` to confirm anonymous bind on the ldaps image.
