---
phase: audit-2026-05-08-scanners-protocol
reviewed: 2026-05-08T00:00:00Z
depth: deep
files_reviewed: 17
files_reviewed_list:
  - quirk/scanner/tls_scanner.py
  - quirk/scanner/tls_capabilities.py
  - quirk/scanner/ssh_scanner.py
  - quirk/scanner/dnssec_scanner.py
  - quirk/scanner/saml_scanner.py
  - quirk/scanner/kerberos_scanner.py
  - quirk/scanner/email_scanner.py
  - quirk/scanner/broker_scanner.py
  - quirk/scanner/jwt_scanner.py
  - quirk/scanner/source_scanner.py
  - quirk/scanner/container_scanner.py
  - quirk/scanner/fingerprint.py
  - quirk/scanner/target_expander.py
  - quirk/discovery/coverage.py
  - quirk/discovery/nmap_parser.py
  - quirk/discovery/nmap_provider.py
  - quirk/discovery/tls_scanner.py
findings:
  critical: 8
  warning: 14
  info: 6
  total: 28
status: issues_found
---

# Subsystem 1 — Network/Protocol Scanners — Code Review Report

**Reviewed:** 2026-05-08
**Depth:** deep
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Deep adversarial audit of the network/protocol scanner subsystem found multiple
correctness, security, and resilience defects. Highest-impact issues:

1. **`jwt_scanner.py` disables TLS verification (`verify=False`) on every JWKS fetch** —
   a network-positioned attacker can substitute forged JWKS keys into the inventory.
   The SAML scanner gets this right (`verify=True`); JWT got it wrong.
2. **Two scanners (`source_scanner`, `container_scanner`) execute external tools
   with user-controlled, *unvalidated* inputs as positional argv** — `repo_path`
   and `image_ref` flow straight into `subprocess.run([...])`. While `shell=False`
   prevents shell metacharacter injection, both inputs can begin with `-`/`--`,
   producing **argument injection** into `semgrep`/`syft` (e.g. `--config=...` to
   load a malicious ruleset, or syft flags that execute remote registry pulls).
3. **`saml_scanner._fetch_metadata` uses bare `httpx.get` — no SSRF or scheme
   guard.** Operators can be coerced into fetching `file://`, `http://169.254.169.254/...`,
   or arbitrary internal URLs from an attacker-supplied target list.
4. **`broker_scanner._enrich_rabbitmq_mgmt` ships hardcoded `guest:guest`
   credentials** into log output / Basic-auth header against arbitrary hosts —
   credential exposure if the URL ever points to a third-party host.
5. **`tls_scanner.scan_one` runs sslyze inside a worker thread inside a
   `ThreadPoolExecutor`** — sslyze internally spawns its own threads/processes.
   Each TLS target therefore creates a nested concurrency pool; this is both
   wasteful and an established source of socket exhaustion / hangs in sslyze 5.x.
6. **Off-by-one + wrong CSV in `nmap_provider`**: the default port-CSV fallback
   includes `5001` (random) but is missing `465/587/993/995/110/9092/9093/6379/6380/53/88/389`
   — the very ports the rest of this subsystem exists to scan. This is a
   silent coverage gap at the discovery boundary.
7. **`coverage.calculate_coverage`** divides by `target_count` but is called by
   `cli.py` with `tls_endpoints` that include both successful AND failed scans,
   producing `>100%` coverage in some sessions.
8. **`fingerprint._tcp_connect` leaks sockets on the SSH banner path** — the
   socket is opened, banner is read, but the function returns the *same* `s`
   for the caller's `with s:` context. If `_try_read_ssh_banner` raises, the
   socket is never closed because the `with` block hasn't been entered yet.

Several import-guard patterns are also incoherent across modules: some scanners
print to stderr (kerberos), some warn (dnssec), some silently return `[]` (jwt,
source, container) — Phase 45 Install-Day UX explicitly required uniform
graceful-degradation messaging.

## Critical Issues

### CR-01: JWT scanner disables TLS certificate verification on JWKS fetch (MITM)

**File:** `quirk/scanner/jwt_scanner.py:56,67`
**Issue:** Both `httpx.get` calls pass `verify=False`. JWKS keys are the
*authentication root* for downstream JWT verification; if QUIRK's "inventory"
records keys harvested over an unverified TLS channel, an on-path attacker can
inject keys that the consulting deliverable then attests to. Compare with
`saml_scanner.py:66` which correctly uses `verify=True` and even documents the
threat model in the docstring.
**Fix:**
```python
resp = httpx.get(url, timeout=timeout, follow_redirects=True, verify=True)
...
resp2 = httpx.get(jwks_uri, timeout=timeout, follow_redirects=True, verify=True)
```
Add a CLI/config flag (`--insecure-jwks`) for self-signed lab environments only.

---

### CR-02: Argument injection into semgrep via `repo_path`

**File:** `quirk/scanner/source_scanner.py:38-43`
**Issue:** `repo_path` is appended to the argv as the last positional. If a
caller provides `--config=https://evil.example/rules.yml` (or `-c`, `--metrics=on`,
`--baseline-commit`, etc.), semgrep parses it as a flag, not as a path. This is
exactly CWE-88 (argument injection). `shell=False` does NOT prevent this —
argv-level injection is independent of shell parsing.
**Fix:**
```python
# Reject paths that look like flags
if repo_path.startswith("-"):
    raise ValueError(f"Refusing source scan path beginning with '-': {repo_path!r}")
# Use POSIX argv terminator
proc = subprocess.run(
    [exe, "--json", "--config", "p/cryptography", "--", repo_path],
    capture_output=True, text=True, timeout=timeout,
)
```

---

### CR-03: Argument injection into syft via `image_ref`

**File:** `quirk/scanner/container_scanner.py:61-66`
**Issue:** Identical pattern: `image_ref` is the first positional after the
binary, with no validation. A target value like `--from oci-archive` or
`-q --output template=...` is parsed by syft as flags and can redirect output,
load arbitrary scanner configs, or pull from attacker registries. Syft also
follows scheme prefixes (`registry:`, `docker:`, `file:`, `dir:`); a value like
`file:/etc/shadow` is parseable but more importantly `dir:/` would scan the
whole host filesystem.
**Fix:**
```python
if image_ref.startswith("-"):
    raise ValueError(f"Refusing container ref beginning with '-': {image_ref!r}")
proc = subprocess.run([exe, "-o", "json", "--", image_ref], ...)
```
Also constrain accepted schemes to a known list (`docker:`, `registry:`,
`oci-archive:`) and reject `file:` / `dir:` unless explicitly opted in.

---

### CR-04: SSRF in SAML metadata fetcher — no scheme/host validation

**File:** `quirk/scanner/saml_scanner.py:57-75`
**Issue:** `_fetch_metadata` accepts arbitrary URLs and calls `httpx.get(url, ...)`.
There is no scheme allowlist (`file://`, `gopher://` blocked? — depends on httpx
version), no link-local / RFC1918 / metadata-IP guard. A target list reading
`http://169.254.169.254/latest/meta-data/iam/security-credentials/` (AWS IMDS)
would happily return cloud credentials into `saml_scan_json`. Per the audit
prompt's STRIDE focus, this is the canonical Information-Disclosure /
Server-Side-Request-Forgery vector.
**Fix:**
```python
from urllib.parse import urlparse
import ipaddress

def _validate_metadata_url(url: str) -> None:
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        raise ValueError(f"SAML: refusing scheme {p.scheme!r}")
    host = p.hostname or ""
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError(f"SAML: refusing internal IP {host}")
    except ValueError:
        # hostname — accept; consider DNS-resolution guard for paranoia mode
        pass
```
Call before `httpx.get`. Mirror this in `jwt_scanner._fetch_jwks`.

---

### CR-05: Hardcoded `guest:guest` credentials sent to arbitrary hosts

**File:** `quirk/scanner/broker_scanner.py:312-313,315`
**Issue:** `_enrich_rabbitmq_mgmt` is called once per host in
`scan_rabbitmq_targets` (line 547) **without checking that the host is in fact
a RabbitMQ deployment that the operator owns.** Sending `Authorization: Basic
Z3Vlc3Q6Z3Vlc3Q=` to a third-party endpoint discloses an attempt to authenticate
as `guest`, and the credential pair travels unencrypted (`http://`, port 15672).
A target list including a non-RabbitMQ host (e.g. honeypot, attacker-controlled)
captures the Basic-auth header. Worse, the `mgmt_auth: rejected_401` data point
is then persisted into `email_scan_json`/equivalents, leaking that QUIRK
attempts default credentials.
**Fix:** Make management API enrichment opt-in (CLI flag), require an explicit
allowlist of trusted RabbitMQ hosts, AND prefer HTTPS (port 15671) by default
with a fall-back rather than fall-forward to plaintext 15672.

---

### CR-06: `verify=False` on RabbitMQ mgmt API & nested-config patterns

**File:** `quirk/scanner/broker_scanner.py:312-316`
**Issue:** `urllib.request.urlopen` with an `http://` URL has no TLS at all —
this is plaintext over the network. Combined with CR-05, the `guest:guest`
header is shipped in the clear on every scan. Also note `_enrich_redis_config`
(`broker_scanner.py:639-642`) sets `ssl_cert_reqs="none"` — same MITM exposure
as CR-01 for any enrichment data captured.
**Fix:** Default to `https://{host}:15671/api/overview` and verify the chain.
Document that lab profiles should use TLS-fronted management.

---

### CR-07: Nested ThreadPoolExecutor + sslyze internal pool — concurrency
foot-gun and resource leak

**File:** `quirk/scanner/tls_scanner.py:527-535` (also `email_scanner.py:531`,
`broker_scanner.py:439,531,711`)
**Issue:** `scan_tls_targets` submits N futures to its own `ThreadPoolExecutor`,
and each future calls `_scan_one_sslyze`, which constructs its **own**
`SslyzeScanner` instance (line 153). sslyze 5.x's `Scanner` allocates its own
internal thread pool *and* (depending on version) `multiprocessing` workers.
With `tls_workers=cfg.scan.concurrency` (often 50), this fans out to
`50 × per_server_concurrent_connections_limit (=2)` plus sslyze's worker
overhead — observed in v4.5 lab runs as scans stalling at 100% CPU and
`ResourceWarning: unclosed <socket.socket>`. Additionally, `SslyzeScanner` is
**not closed** anywhere — `scanner.queue_scans` + `list(scanner.get_results())`
without a corresponding `.shutdown()`/`__exit__` leaks descriptors per call.
**Fix:** Either drop the outer `ThreadPoolExecutor` and submit ALL scan
requests to a single sslyze `Scanner` (sslyze is designed for batch use), or
keep the outer pool but instantiate `SslyzeScanner` once per `scan_tls_targets`
call with all `ServerScanRequest`s queued. Always close it (`with` /
explicit `del`).

---

### CR-08: `fingerprint._tcp_connect` socket leak on SSH banner branch

**File:** `quirk/scanner/fingerprint.py:144-157`
**Issue:** `s = _tcp_connect(...)` is called and the socket is bound to local `s`
*before* the `with s:` block. If `_try_read_ssh_banner` returns a banner, the
function enters the `with s:` and exits cleanly — fine. **But if** the `socket.recv`
in `_try_read_ssh_banner` raises a non-`Exception` (e.g. `KeyboardInterrupt`,
`SystemExit`), the inner `try/except` doesn't catch it, control jumps out, and
the freshly-opened socket leaks. More importantly, the broader pattern of
"open, then enter `with`" is fragile: a `signal` arriving between line 146 and
line 154 leaks the descriptor. Wrap the entire open+probe in a single context.
**Fix:**
```python
def fingerprint_service(host, port, timeout=3):
    try:
        with _tcp_connect(host, port, timeout) as s:
            banner = _try_read_ssh_banner(s)
            if banner:
                return Fingerprint(True, "SSH", banner)
    except socket.timeout:
        return Fingerprint(False, "CLOSED", "TIMEOUT")
    ...
```

## Warnings

### WR-01: `coverage.calculate_coverage` can return >100%

**File:** `quirk/discovery/coverage.py:1-6`
**Issue:** `tls_endpoints` is divided by `target_count`, but callers regularly
pass the length of the *result list* (which is one entry per scan attempt,
including failures) while `target_count` may be the count of unique hosts. With
a fan-out of 7 email ports per host, returned coverage exceeds 100%.
**Fix:** Clamp `min(coverage, 100.0)`, OR rename the parameters and document the
expected denominator semantics.

---

### WR-02: `quantum_readiness_score` produces non-monotonic scores; no clamp at 0 reached early

**File:** `quirk/discovery/coverage.py:9-25`
**Issue:** Penalties stack additively without bounds. A scan with 10 CRITICAL
findings drives `score = 100 - 250 = -150` then clamps to 0, losing all signal.
There is no mechanism to differentiate "100 critical findings" from "5 critical
findings" once the floor is hit. Also, `severity` is read by `f["severity"]` but
nowhere is it documented that severity must be uppercase string — passing
`Severity.CRITICAL` enum (used elsewhere in the codebase) silently scores 0.
**Fix:** Use a logarithmic or capped per-bucket penalty, and normalize severity
input before comparison.

---

### WR-03: Bare `except Exception` swallowing `subprocess` errors silently

**File:** `quirk/scanner/source_scanner.py:45`, `quirk/scanner/container_scanner.py:68`,
`quirk/scanner/ssh_scanner.py:28`
**Issue:** All three catch `(subprocess.TimeoutExpired, json.JSONDecodeError, Exception)`
and return None / `[]` with no logging. When `semgrep` exits non-zero (e.g.
ruleset not found, wrong path), the operator gets an empty result and no clue
why. This violates the Install-Day UX requirement of meaningful failure
messaging.
**Fix:** Catch specific exceptions, log at `WARNING` with the exception, and
distinguish "tool absent" from "tool failed". Also check `proc.returncode`
explicitly before parsing stdout.

---

### WR-04: `nmap_provider` default port CSV is incomplete and wrong

**File:** `quirk/discovery/nmap_provider.py:54`
**Issue:** Fallback `"22,80,443,8443,9443,10443,5001"` is the wrong scope for
this subsystem. Missing email (25/465/587/110/143/993/995), Kerberos (88/464),
DNS (53), LDAP (389/636), Kafka (9092-9094), Redis (6379-6380), AMQP
(5671-5672), RabbitMQ mgmt (15672/15671). Phase 45 lab profiles all run on
ports outside this default, so an operator who omits `--ports` gets near-zero
discovery coverage.
**Fix:** Move the canonical port list to a single module
(`quirk.scanner.ports`) and import it everywhere — TLS expander,
discovery default, lab oracle.

---

### WR-05: `nmap_provider.run_nmap_discovery` accepts unvalidated `extra_args`

**File:** `quirk/discovery/nmap_provider.py:39,58-60`
**Issue:** `extra_args: Optional[List[str]]` is appended to argv with no
filtering. If exposed via the wizard / API (Phase 47 multi-target wizard), an
operator can pass `["--script=external/exfil.nse"]` or `["--privileged"]`. Even
without web-facing exposure this is a privilege-escalation vector via NSE
scripts that read `/etc/shadow` or write files via `--datadir`.
**Fix:** Maintain an allowlist of safe flags (`-sS`, `-sT`, `-T2`, `-T3`, etc.)
and reject anything else. Document the allowlist.

---

### WR-06: `nmap_parser.parse_nmap_xml` uses stdlib `xml.etree.ElementTree` —
XXE / billion-laughs surface

**File:** `quirk/discovery/nmap_parser.py:5,21`
**Issue:** Stdlib `ET.parse` is documented as **not safe against malicious XML**
(XXE, billion-laughs, quadratic blowup). XML files are produced by `nmap`
locally so the immediate risk is low — BUT the same parser is reachable via
ingestion paths (e.g. uploaded nmap XML in a future API endpoint). Consistency
with `saml_scanner.py` (which uses `defusedxml`/lxml-with-flags) is required.
**Fix:** Use `defusedxml.ElementTree.parse` here, mirroring the SAML pattern.

---

### WR-07: `dnssec_scanner._parse_dnskeys` unbounded subscript on `key_bytes`

**File:** `quirk/scanner/dnssec_scanner.py:97-104`
**Issue:** RFC 3110 parsing reads `key_bytes[0]`, `key_bytes[1]`, `key_bytes[2]`,
then computes `modulus_start = 3 + exp_len`. If a hostile zone returns a
truncated DNSKEY (length 0/1/2) or `exp_len > len(key_bytes) - 3`, this raises
`IndexError`, and while the surrounding `try/except` catches it, the operator
loses all DNSKEY parsing data for the zone. Worse, `(len(key_bytes) - modulus_start) * 8`
yields a *negative* modulus length that is then stored unchallenged.
**Fix:** Validate `len(key_bytes) >= 3 + exp_len + 1` and clamp the computed
size to `>= 0`, otherwise set `key_size = None`.

---

### WR-08: `kerberos_scanner._probe_kdc_udp` silently swallows all decode errors

**File:** `quirk/scanner/kerberos_scanner.py:178-179`
**Issue:** `except Exception: return []` discards `pyasn1` decode failures,
malformed responses, and connection errors uniformly. A target that responds
with garbage bytes (port-scanning a non-KDC service on 88) leaves the operator
with "no etypes discovered" but no diagnostic. Combined with the broad TCP path
above (line 268-273) that also catches `Exception` and falls through to UDP,
real KDC misconfiguration is indistinguishable from "this isn't a KDC".
**Fix:** Categorize: `socket.timeout` → `kerberos-timeout`,
`pyasn1.error.PyAsn1Error` → `kerberos-malformed`, generic Exception →
`kerberos-error: <repr>`. Surface in `kerberos_scan_json.errors`.

---

### WR-09: `kerberos_scanner._build_as_req` uses non-cryptographic RNG for nonce

**File:** `quirk/scanner/kerberos_scanner.py:82`
**Issue:** `random.getrandbits(31)` uses Mersenne Twister, which is predictable
and unsuitable for protocol nonces. While this is an *unauthenticated* probe
where security impact is minimal, RFC 4120 §5.4.1 specifies the nonce should be
unguessable to mitigate replay. Several CI-grade scanners flag `random.*` in
crypto contexts.
**Fix:** Use `secrets.randbits(31)`.

---

### WR-10: `saml_scanner._classify_target` content-sniffs by parsing JSON of
arbitrary bytes — no size limit

**File:** `quirk/scanner/saml_scanner.py:78-90`
**Issue:** `json.loads(content)` over potentially-large response body with no
length cap. A hostile or misconfigured server returning multi-GB content
exhausts memory before classification fails. `_fetch_metadata` similarly has no
size cap on `response.content`.
**Fix:** Cap `httpx.get` body size (`response.read()` chunks with a limit),
e.g. 8 MB max for SAML metadata; reject larger payloads.

---

### WR-11: Inconsistent extras messaging across optional-dep scanners

**Files:**
- `quirk/scanner/jwt_scanner.py:93,143` — silent `return []`, no log
- `quirk/scanner/source_scanner.py:34` — `logger.v(...)`
- `quirk/scanner/container_scanner.py:57` — `logger.v(...)`
- `quirk/scanner/dnssec_scanner.py:313-315` — `logger.warning`
- `quirk/scanner/saml_scanner.py:384-386` — `logger.warning`
- `quirk/scanner/kerberos_scanner.py:246-256` — `print` to stderr + logger.warning
- `quirk/scanner/email_scanner.py` / `broker_scanner.py` — silent fall-through
**Issue:** Phase 45 Install-Day UX requires consistent messaging: which extras
group install which scanner. The current state is six different patterns
across one subsystem — operators see different output formats for "this scanner
needs an extra".
**Fix:** Centralize via a helper:
```python
def warn_missing_extra(scanner: str, extras_group: str, package: str, logger):
    msg = (f"[QUIRK] {scanner} requires the {extras_group} extras:\n"
           f"    pip install quirk[{extras_group}]\n"
           f"  (missing package: {package}). Scanner disabled.")
    if logger: logger.warning(msg)
    print(msg, file=sys.stderr)
```

---

### WR-12: `email_scanner` and `broker_scanner` ThreadPool workers hardcoded to 50

**Files:** `email_scanner.py:531`, `broker_scanner.py:439,531,711`
**Issue:** `min(len(tasks), 50)` ignores `cfg.scan.concurrency` /
`cfg.scan.email_concurrency`. The TLS scanner (line 523) reads
`cfg.scan.tls_concurrency`; email and broker do not — diverging from the
documented Phase 41 D-08 pattern of per-scanner concurrency in the
canonical config sub-table. Operators throttling scans for production safety
will find email/broker still bursting at 50 concurrent connections per host.
**Fix:** Accept `cfg` parameter or explicit `workers=` in
`scan_email_targets` / `scan_kafka_targets` / etc.

---

### WR-13: `discovery/tls_scanner.py` is dead-code duplicate of `scanner/tls_scanner.py`

**File:** `quirk/discovery/tls_scanner.py` (entire 112-line file)
**Issue:** This file duplicates `_pubkey_info`, `_extract_sans`, and a stripped
`scan_one`/`scan_tls_targets` from `quirk/scanner/tls_scanner.py`. No imports
in the codebase point here (`grep` confirms only the scanner module is used).
The duplicate has *none* of the post-Phase-46 fixes — chain verification,
sslyze primary path, error categorization, or the half-populated-row guard. If
any caller ever imports this by mistake, it silently regresses TLS scanning to
v3.5 quality.
**Fix:** Delete `quirk/discovery/tls_scanner.py`. If something inside
`quirk/discovery/` needs TLS scanning, import from `quirk.scanner.tls_scanner`.

---

### WR-14: `target_expander` does not deduplicate, can produce duplicate
(host, port) tuples; also no bound on CIDR expansion

**File:** `quirk/scanner/target_expander.py:4-30`
**Issue:**
1. A host listed in `fqdns` AND covered by a `cidrs` entry produces two
   entries. The downstream TLS scanner happily double-scans, doubling load.
2. `cfg.targets.cidrs` accepts arbitrary CIDRs; passing `0.0.0.0/0` causes
   `net.hosts()` to materialize ~4 billion IPs into the list (memory blow-up).
3. `cfg.targets.exclude_ips` is checked as a `set`, but include_ips entries
   may be CIDRs/hostnames mixed with IPs — type confusion.
**Fix:** Deduplicate via a set; reject CIDRs with prefix < 22 (configurable);
validate `include_ips` entries with `ipaddress.ip_address` and reject otherwise.

## Info

### IN-01: `tls_capabilities._try_handshake` constructs SSLContext with
`CERT_NONE` + `check_hostname=False` for every probe — acceptable for cipher
enumeration but warrants a comment noting the deliberate downgrade

**File:** `quirk/scanner/tls_capabilities.py:52-54`
**Fix:** Add a one-line comment: `# Cipher enumeration only — cert verification handled in scan_one's pre-pass`.

---

### IN-02: `dnssec_scanner.DNSSEC_ALG_MAP` has no entry for algorithms 9, 11
(reserved/historical) — unknown algorithms fall through to `("UNKNOWN-{n}", "HIGH")`

**File:** `quirk/scanner/dnssec_scanner.py:25-38`
**Fix:** Document the fall-through behavior in the module docstring, or add
explicit reserved markers.

---

### IN-03: `saml_scanner.SHA1_INDICATORS = ("sha1", "sha-1")` would also match
benign URIs like `http://example.com/sha-100/`

**File:** `quirk/scanner/saml_scanner.py:43-44`
**Fix:** Tighten to URI-fragment match: only flag if the substring appears
after the last `#` or `/` and is followed by `'\b'` boundary.

---

### IN-04: `fingerprint._http_probe_plain` sends `Host: localhost` — many vhost
configs reject or 421-redirect

**File:** `quirk/scanner/fingerprint.py:111`
**Fix:** Use the actual `host` parameter as the `Host:` header; `localhost`
also makes log analysis on the target side misleading.

---

### IN-05: `email_scanner` and `broker_scanner` repeatedly redefine `_is_pfs`
and `_is_weak`

**Files:** `email_scanner.py:102-109`, `broker_scanner.py:106-113`,
`tls_scanner.py:231-239` (inline)
**Issue:** Same logic, three implementations. Diverging cipher markers across
modules (the `weak_markers` tuple is identical today but easy to drift).
**Fix:** Extract to `quirk.scanner.tls_helpers` (or extend `tls_capabilities`).

---

### IN-06: `kerberos_scanner._derive_realm` IPv4 detection is fragile

**File:** `quirk/scanner/kerberos_scanner.py:55-56`
**Issue:** `len(parts) == 4 and all(p.isdigit())` accepts `1.2.3.99999` as an
IPv4 address. Use `ipaddress.ip_address(host)` for accurate detection — already
imported elsewhere in the codebase.

---

_Reviewed: 2026-05-08_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
