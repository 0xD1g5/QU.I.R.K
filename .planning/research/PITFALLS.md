# Pitfalls Research

**Domain:** Enterprise readiness additions to an existing Python cryptographic scanner (QU.I.R.K. v4.6)
**Researched:** 2026-05-03
**Confidence:** HIGH (code-verified for integration pitfalls; MEDIUM for PCI-DSS 4.0 / FIPS mapping details)

---

## Critical Pitfalls

### Pitfall 1: Extras-by-default silently resurrects pyOpenSSL transitive conflicts

**What goes wrong:**
Moving `[identity]` (impacket) or `[motion]` (broker/kafka) into the default install via a `[default]` or `all` meta-extra pulls impacket into every pip install of QUIRK. impacket has a known transitive conflict with pyOpenSSL versions that sslyze and the cryptography library expect. The conflict does not always surface as a hard error — sometimes it silently downgrades `cryptography` to a version that removes `not_valid_before_utc` / `not_valid_after_utc`, causing the TLS scanner to fall through to the deprecated `.not_valid_before` path and emit deprecation warnings in CI.

**Why it happens:**
The PROJECT.md Key Decisions record explicitly states "impacket>=0.13.0,<0.14 in [identity] extras only — pyOpenSSL transitive conflict risk prevents placing impacket in core deps." Adding it to a default group recreates the same conflict without any code change.

**How to avoid:**
Do not add impacket to any default or `all` meta-extra. The correct BACK-76 implementation is graceful ImportError degradation inside each optional scanner — not promoting extras to required. Implement the `try: import ...; HAS_X = True` + `except ImportError: HAS_X = False` pattern at module level (not function level) so the flag is evaluated once. Call `_emit_missing_extra_advisory()` (already in run_scan.py) rather than crashing. Keep identity, cloud, db, motion as explicit opt-in extras.

**Warning signs:**
- `pip install quirk[all]` succeeds but `python -c "import sslyze"` prints a version conflict warning
- `not_valid_before_utc` AttributeError appears in pytest output on a fresh venv
- test_version.py surface-count test fails because a transitive dependency bumped a minor version

**Phase to address:**
BACK-76 phase — verify in a clean venv with only core deps installed, and separately with each extras group installed, that no import-time conflict occurs.

---

### Pitfall 2: sslyze `verified_certificate_chain is None` conflated with self-signed detection

**What goes wrong:**
The risk engine (risk_engine.py line 358) already handles `chain_verified == False` as a self-signed signal, reading from `tls_capabilities_json`. However, sslyze returns `verified_certificate_chain = None` for ANY chain that fails validation against its bundled trust stores — not just self-signed certs. A corporate-issued internal CA cert that is not in Mozilla/Apple/Windows trust stores will fire the self-signed finding when it should not. Conversely, a cert signed by a publicly trusted CA that has expired will have `verified_certificate_chain = None` AND `cert_not_after` in the past, producing a duplicate finding flood (both expiry HIGH and self-signed MEDIUM on the same endpoint).

**Why it happens:**
sslyze bundles five trust stores (Android, Apple, Java, Mozilla, Windows). An internal enterprise CA not in any of those stores produces `verified_certificate_chain = None` — identical to an actual self-signed cert. The current `issuer == subject` check is the only classical self-signed guard. When sslyze is the active path, `chain_verified` in `tls_capabilities_json` is populated from `deployment.verified_certificate_chain is not None`, so internal CA certs will always set it `False`.

**How to avoid:**
For BACK-74, distinguish the three cases explicitly:
1. `issuer == subject` — definitely self-signed (keep existing check)
2. `chain_verified == False` AND `issuer != subject` — internally issued / untrusted CA (softer "untrusted CA" finding, not "self-signed")
3. Chain failed AND cert is expired — suppress the "untrusted chain" finding; the expiry finding is sufficient

Add a `_is_self_signed(ep)` helper that returns True only when issuer == subject. Separately emit "Untrusted certificate chain" (MEDIUM) when chain is not verified but cert is not self-signed. Deduplicate expiry + chain-failure on the same endpoint.

**Warning signs:**
- Chaos lab TLS profile produces both "Self-signed" and "Expired" findings on the same endpoint
- Internal CA targets produce "self-signed" in reports delivered to clients using private PKI
- sslyze path emits 2x the findings count of the fallback path for the same target

**Phase to address:**
BACK-74 phase — add chaos lab targets with (a) self-signed, (b) expired, (c) internal CA certs and verify each produces exactly one finding with the correct title.

---

### Pitfall 3: `cert_not_after` is NULL in the SQLite row when sslyze's CERTIFICATE_INFO command fails

**What goes wrong:**
When sslyze returns `COMPLETED` status for the server scan but the `CERTIFICATE_INFO` scan command attempt itself has status `ERROR`, the sslyze path sets `chain_depth = 0` and `chain_verified = False` but skips populating `cert_not_after`, `cert_pubkey_size`, and `cert_issuer`. The endpoint is returned from `_scan_one_sslyze()` rather than triggering the fallback. The risk engine then has `cert_not_after = None` and skips the expiry check entirely. The self-signed check also silently passes because both `cert_issuer` and `cert_subject` are empty strings, so `issuer == subject` evaluates `False`.

**Why it happens:**
`_scan_one_sslyze()` returns a partially-populated `CryptoEndpoint` when the server scan completes but the CERTIFICATE_INFO command fails (e.g., mTLS-required endpoint, or a cert that triggers an OpenSSL parsing error). The caller in `scan_one()` sees a non-None return and never calls `_scan_one_fallback()`.

**How to avoid:**
In `_scan_one_sslyze()`, when `cert_attempt.status != ScanCommandAttemptStatusEnum.COMPLETED`, return `None` to trigger the fallback rather than returning a half-populated endpoint. Add a guard: if `ep.cert_not_after is None` after the sslyze block, return `None`. Add a test with an mTLS-required chaos lab target that verifies the fallback path populates cert fields.

**Warning signs:**
- BACK-74 test for "expired cert" passes with sslyze installed but produces zero findings when sslyze is uninstalled and fallback runs
- SQLite rows with `cert_not_after IS NULL` but `tls_version` populated (indicates sslyze partial success)
- `scan_error_category` is NULL but all cert columns are NULL on a successfully connected endpoint

**Phase to address:**
BACK-74 phase — the fix is a guard in `_scan_one_sslyze()`. Requires a chaos lab cert that exercises the CERTIFICATE_INFO ERROR path.

---

### Pitfall 4: FIPS 203/204 remediation text mixing draft submission names with final standard names

**What goes wrong:**
The risk engine currently uses mixed terminology in remediation strings: "ML-KEM / CRYSTALS-Kyber for key exchange, ML-DSA / Dilithium for signatures" (risk_engine.py line 395). FIPS 203 (ML-KEM) and FIPS 204 (ML-DSA) were finalized in August 2024. The original competition submission names "Kyber" and "Dilithium" are no longer normative. Procurement documents or compliance reports containing both names cause confusion when clients or auditors search for the standard. More critically, remediation text that says "when NIST PQC standards are adopted upstream" (risk_engine.py line 54) is already factually wrong — the standards are published and final.

**Why it happens:**
The CBOM classifier (classifier.py line 144) already correctly uses the FIPS 203/204/205 designations. The risk engine remediation strings were written before August 2024 finalization and were not updated. For BACK-79 rich finding context, new strings will be added — if written carelessly, they inherit the same staleness.

**How to avoid:**
Use only NIST-normative names in all new remediation text: "ML-KEM" (FIPS 203), "ML-DSA" (FIPS 204), "SLH-DSA" (FIPS 205). Never write "Kyber" or "Dilithium" in user-facing strings. Cite the FIPS number explicitly when possible. Replace the stale "when NIST PQC standards are adopted upstream" phrasing with "NIST finalized FIPS 203/204/205 in August 2024 — migration planning should begin now. Federal systems must migrate by 2030 per NIST IR 8547." Extract all PQC remediation strings into a shared constant module so they are updated once and propagate everywhere. Add a CI grep check for "Kyber" or "Dilithium" in remediation strings.

**Warning signs:**
- Any string in risk_engine.py or a new remediation module containing "Kyber", "Dilithium", or "when standards are adopted"
- CBOM classifier and risk engine use different algorithm names for the same algorithm
- Compliance report contains a FIPS citation that references a draft document number

**Phase to address:**
BACK-79 phase — do a remediation string audit before writing any new strings.

---

### Pitfall 5: Compliance mapping becomes a maintenance liability the moment it ships

**What goes wrong:**
Hardcoding control IDs like "FIPS 140-3 IG D.F", "PCI-DSS 4.0 Req 4.2.1", "NIST SP 800-208 Section 3.1" directly in finding dicts or Python constants makes the mapping a one-way door. PCI-DSS 4.0.1 was released in June 2024, renumbering some requirements from PCI-DSS 4.0. HIPAA does not use numbered control IDs — it uses safeguard names ("Encryption and Decryption", 45 CFR §164.312(a)(2)(iv)) that are stable but easy to misformat. Mapping findings to specific PCI-DSS 4.0.1 requirement numbers that shift in a future version will require codebase edits when PCI-DSS 5.0 arrives.

**Key PCI-DSS 4.0 vs 3.2.1 differences that affect QUIRK:**
- Req 4.2.1 and 4.2.1.1 are new in 4.0: require documented inventory of all TLS keys and certs — maps directly to QUIRK's cert inventory feature
- 4.0 requires TLS 1.2+ (not 1.1+); weak cipher suites explicitly disallowed
- 4.0.1 (June 2024) adjusts numbering — always cite version string in the mapping

**How to avoid:**
Separate compliance mapping data from finding logic. Use a `COMPLIANCE_MAP: dict[str, list[dict]]` module constant, keyed by finding category (e.g., "TLS_EXPIRED", "RSA_WEAK_KEY"), not by finding title string. Each entry is a list of dicts: `{"framework": "PCI-DSS", "version": "4.0.1", "control": "4.2.1", "requirement": "..."}`. Findings stay unchanged; the compliance layer is additive. Updating to PCI-DSS 5.0 means editing one dict, not auditing 30 finding generators. Include a `version` key on every mapping entry.

**Warning signs:**
- Compliance control IDs are string literals inside `_derive_tls_findings()` or equivalent
- No `version` key on any compliance mapping entry
- HIPAA references use requirement numbers (HIPAA has no numbered controls — it uses safeguard names)

**Phase to address:**
BACK-20 phase — design the `COMPLIANCE_MAP` data structure before writing any mappings.

---

### Pitfall 6: Nmap running as non-root silently exhausts file descriptors on macOS with large scopes

**What goes wrong:**
The current `nmap_provider.py` uses `-sT` (TCP connect scan) which does not require root — correct. However, on macOS, running nmap against large CIDR blocks with `-sT -Pn` opens one socket per (host, port) combination simultaneously. For a /24 with 17 ports that is 4,335 concurrent sockets, exceeding macOS's default per-process file descriptor limit of 256 and silently dropping results. On Linux systems where nmap has the SUID bit set, nmap may auto-upgrade from `-sT` to `-sS` (SYN scan requiring raw sockets) — which then fails for non-root callers despite SUID.

**Why it happens:**
`_default_nmap_args()` does not limit concurrent parallelism. The BACK-75 phase adds nmap as a pre-scan probe. If the consultant runs it against a client's /16 (65,536 hosts × 17 ports = 1.1M combinations), the default 1800-second timeout will be exceeded and nmap returns an empty target list — with no user-visible finding or warning.

**How to avoid:**
Add `--max-parallelism 100` to `_default_nmap_args()`. Add a target count guard before invoking nmap: if `len(targets) * len(ports) > 10_000`, warn and ask for confirmation. For CIDR inputs larger than /24, recommend splitting the scope. The RuntimeError on timeout (already in `nmap_provider.py` line 80) is good — ensure it propagates through `_wrapped_phase` correctly. Never document or suggest setting the SUID bit on nmap in the operator's guide.

**Warning signs:**
- Nmap returns 0 open ports on a target known to have open ports
- `quirk.db` contains 0 TLS endpoints after a nmap-discovery scan on a non-trivial scope
- Nmap discovery blocks until the full `--nmap-timeout` with no progress output

**Phase to address:**
BACK-75 phase — add `--max-parallelism` to defaults and target count guard before invocation.

---

### Pitfall 7: Multi-target wizard accepting bare hostnames that are actually file paths

**What goes wrong:**
The interactive wizard (`_prompt_list()` in interactive.py) splits on comma/whitespace and accepts any token as an FQDN. If the user types a filename like `targets.txt` intending file-based input (which BACK-77 will add), the current code will try to resolve `targets.txt` as a hostname, fail silently at scan time (TLS connection refused or DNS NXDOMAIN), and produce 0 findings for all those targets with no user-visible explanation.

**Why it happens:**
File-based input does not exist yet. When it is added, the parsing logic must differentiate between a path token and a hostname token before any input enters the target list. Without this check, user error produces a silent zero-findings scan that looks identical to a successful scan of unreachable hosts.

**How to avoid:**
When BACK-77 adds file-based input, detect file paths before the FQDN split: if a token starts with `/`, `./`, or ends with `.txt`/`.csv`, attempt to read it as a file first. If the file does not exist, warn explicitly ("'targets.txt' not found as a file — treating as hostname"). Add FQDN validation: reject tokens that are empty strings after stripping, or that contain only digits and dots but fail `ipaddress.ip_address()` (likely a malformed IP). Strip and filter empty strings from all `_prompt_list()` output — a trailing comma currently produces an empty-string hostname.

**Warning signs:**
- Interactive wizard accepts `targets.txt` without warning and produces a scan with 0 TLS endpoints
- User-supplied CIDR like `10.0.0.0/8` generates 16 million IPs silently without confirmation
- Token list contains empty strings after split (user typed trailing comma or double space)

**Phase to address:**
BACK-77 phase — validation must run before targets are written to config, not after.

---

### Pitfall 8: IPv6 literal addresses breaking target parsing

**What goes wrong:**
`expand_targets()` in `target_expander.py` handles IPv4 CIDRs via `ipaddress.ip_network()`. IPv6 addresses typed as literals (e.g., `2001:db8::1`) via `_prompt_list()` are not currently validated. `ipaddress.ip_network("2001:db8::1/64")` raises `ValueError: 2001:db8::1/64 has host bits set` unless `strict=False` is passed — and the multi-target wizard would surface this as an unhandled traceback. Additionally, sslyze's `ServerNetworkLocation` and `socket.create_connection` have different expectations for IPv6 bracket formatting.

**How to avoid:**
In `expand_targets()`, detect IPv6 CIDRs and retry with `strict=False`. Document in the operator's guide that IPv6 CIDR ranges in nmap notation are not supported (confirmed in nmap docs — IPv6 only accepts full addresses, not CIDR). For the sslyze path, bracket IPv6 literals before passing to `ServerNetworkLocation`. For the fallback path, `socket.create_connection` accepts raw IPv6 literals without brackets.

**Warning signs:**
- User types `::1` as a target and gets an unhandled ValueError at scan start
- IPv6 target produces sslyze `ERROR_NO_CONNECTIVITY` while the fallback path succeeds for the same host

**Phase to address:**
BACK-77 phase — input validation layer.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoding compliance control IDs in finding dicts | Fast to ship | Every framework version bump requires code audit across 30+ finding generators | Never — use a COMPLIANCE_MAP constant |
| Copying PQC remediation text per finding type | Each message is customizable | 8+ places to update when algorithm names change | Never — extract into a shared PQC_REMEDIATION module |
| Promoting optional extras to defaults without testing transitive deps | "Just works" for first install | pyOpenSSL / impacket / sslyze version conflict re-emerges silently | Never for impacket |
| Using `issuer == subject` as the only self-signed signal | Simple one-liner | Internal CA certs incorrectly flagged as self-signed in enterprise environments | Acceptable only when paired with a distinct "Untrusted chain" check |
| Nmap with no parallelism cap | Works on small lab scopes | Exceeds socket limit on /24+ enterprise scopes | Never without target count guard |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| sslyze CERTIFICATE_INFO | Treating `attempt.status != COMPLETED` as partial success; returning half-populated CryptoEndpoint | Return `None` from `_scan_one_sslyze` when cert info command fails; let fallback populate cert fields |
| sslyze `verified_certificate_chain` | Treating `None` as proof of self-signed cert | `None` means trust validation failed against bundled stores; self-signed requires `issuer == subject` |
| `cryptography` library datetime | Using `.not_valid_before` / `.not_valid_after` (deprecated) | Always prefer `not_valid_before_utc` / `not_valid_after_utc`; the existing hasattr guard is correct — do not remove it |
| nmap `-sT` + `-Pn` on macOS | No socket count limit; exhausts file descriptors on large scopes | Add `--max-parallelism 100` to default args |
| impacket in meta-extras | Including impacket in `all` or default extra | Keep in `[identity]` only; pyOpenSSL conflict is documented in PROJECT.md Key Decisions |
| FIPS 203/204 naming | Using "Kyber"/"Dilithium" in user-facing remediation text | Use "ML-KEM" (FIPS 203), "ML-DSA" (FIPS 204), "SLH-DSA" (FIPS 205) |
| PCI-DSS version references | Mapping to "PCI-DSS 4.0" when 4.0.1 is current | Always include version string; PCI-DSS 4.0.1 was released June 2024 |
| Interactive wizard file input | No detection of file-path tokens in FQDN list | Detect `.txt`/`.csv` path tokens before hostname validation; warn if file not found |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Nmap against /16 CIDR with no parallelism cap | 65K hosts × 17 ports = 1.1M socket attempts; 1800s timeout; 0 results returned | Target count guard before nmap invocation; warn above /24 | Any scope larger than ~256 hosts without tuning |
| sslyze per-server thread with no host timeout | Hung host blocks thread for full `tls_timeout` seconds in 50+ host scans | `_wrapped_phase` handles BaseException; ensure TLS timeout is passed to `ServerNetworkConfiguration` | 50+ host scan with unreachable hosts |
| COMPLIANCE_MAP as nested inline dicts in finding generators | Correct for 5 mappings; unmanageable at 50 | Module-level constant dict keyed by finding category | When second or third compliance framework is added |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Documenting nmap SUID setup in operator's guide | Enables privilege escalation; attackers can spawn root shell via nmap NSE lua scripts | Never document or suggest SUID on nmap; always run as non-root with `-sT` |
| PQC remediation text citing deprecated algorithm names | Consultant delivers report with "Kyber" — procurement department purchases a non-FIPS product | CI grep check: fail on "Kyber" or "Dilithium" in any file under `quirk/` |
| Compliance mapping that does not pin a framework version | Client fails audit because report cites PCI-DSS 3.2.1 controls that do not exist in 4.0.1 | Always include `version` key; make version a data attribute not a string literal |
| Treating `CERT_VERIFY_FAILED` as a scan error rather than a finding-opportunity | Self-signed / expired certs are silently skipped | `CERT_VERIFY_FAILED` should still allow cert field population via `ssl.CERT_NONE`; existing fallback already does this — do not regress it when adding BACK-74 logic |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| PQC remediation saying "plan to migrate when standards are adopted" | Consultant looks uninformed — FIPS 203/204 are final | Phrase as "NIST finalized FIPS 203 (ML-KEM) and FIPS 204 (ML-DSA) in August 2024. Federal systems must migrate by 2030 per NIST IR 8547." |
| Compliance mapping without version numbers | Client asks "which version of PCI-DSS?" — consultant cannot answer | Always format as "PCI-DSS 4.0.1 Req 4.2.1" not "PCI DSS Req 4.2.1" |
| Nmap discovery returning 0 targets silently | Consultant assumes scan ran; delivers blank report | Log a WARNING and surface in scan completion summary if nmap returns 0 open ports for any target in scope |
| Multi-target wizard accepting trailing comma | Produces empty-string hostname; silent DNS failure | Strip and filter empty strings from `_prompt_list()` output before returning |
| `missing_extra` advisory buried in verbose log | IT generalist never sees it; thinks scanner ran fully | Surface `missing_extra` advisory in the scan completion summary, not only in verbose log |

---

## "Looks Done But Isn't" Checklist

- [ ] **BACK-76 ImportError degradation:** Verify with a clean venv that has ONLY core deps — no identity, motion, cloud, or db extras. Every optional scanner must produce a `missing_extra` advisory and continue, not raise ImportError and crash.
- [ ] **BACK-74 expired cert detection:** Verify with a chaos lab cert that has `not_valid_after` in the past that the risk engine produces exactly one "TLS certificate expired" HIGH finding — not zero, not two.
- [ ] **BACK-74 self-signed vs internal CA:** Verify that a cert signed by an internal CA (issuer != subject) produces "Untrusted certificate chain" not "Self-signed or untrusted TLS certificate." The two finding titles must be distinct strings so they appear separately in reports.
- [ ] **BACK-74 RSA-1024 detection:** Verify that a chaos lab cert with RSA-1024 produces the "TLS certificate uses undersized RSA key" HIGH finding, not just the generic "quantum-vulnerable RSA" MEDIUM.
- [ ] **BACK-79 PQC remediation naming:** grep for "Kyber" and "Dilithium" in all modified files before shipping — zero hits required.
- [ ] **BACK-20 compliance map versioning:** Every entry in COMPLIANCE_MAP has a `version` key with a specific version string (not just "PCI-DSS"). Confirmed by unit test.
- [ ] **BACK-75 nmap target guard:** Verify that a target list exceeding the count threshold triggers a user-visible warning, not a silent 1800-second timeout.
- [ ] **BACK-77 file-based input:** Verify that typing `targets.txt` (file does not exist) in the wizard produces an explicit warning, not a silent NXDOMAIN scan.
- [ ] **BACK-77 trailing comma:** Verify that `host1,,host2` input produces a 2-element list, not a 3-element list with an empty-string entry.
- [ ] **BACK-65+66 docs freshness:** Verify every CLI flag documented in the operator's guide matches `quirk --help` output exactly. Version string in docs matches `quirk --version` output.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| impacket transitive conflict re-introduced via meta-extra | MEDIUM | Remove from meta-extra; release patch version; document in CHANGELOG |
| sslyze partial-success path ships with NULL cert fields | LOW | Two-line guard in `_scan_one_sslyze`; existing tests catch it if chaos lab mTLS target is in place |
| Compliance map with wrong PCI-DSS version string | LOW | Update COMPLIANCE_MAP constant; no DB migration; republish affected reports |
| PQC naming inconsistency shipped in client deliverable | HIGH | Requires updated report regeneration for affected scans; client communication required |
| Nmap hanging on /16 scope | LOW | User cancels with Ctrl-C; `_wrapped_phase` captures exception; next scan with smaller scope works |
| File-path token accepted as hostname silently | LOW | Rescan with correct input; no data corruption |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Extras-by-default transitive conflict | BACK-76 | `pip install quirk` (no extras) in clean venv; `python -c "from quirk.scanner.kerberos_scanner import scan_kerberos_targets"` produces advisory, not ImportError |
| sslyze `verified_certificate_chain` conflated with self-signed | BACK-74 | Chaos lab with internal CA cert: finding title is "Untrusted certificate chain" not "Self-signed" |
| sslyze partial success with NULL cert fields | BACK-74 | Chaos lab with mTLS endpoint: cert fields populated on successful TLS connection |
| RSA-1024 finding gap | BACK-74 | Chaos lab cert with RSA-1024: "undersized RSA key" HIGH finding present in risk output |
| FIPS 203/204 naming staleness | BACK-79 | CI grep: `grep -r "Kyber\|Dilithium" quirk/` returns 0 results |
| Compliance map maintenance debt | BACK-20 | Unit test: every COMPLIANCE_MAP entry has `version` key with non-empty string value |
| Nmap parallelism + target count | BACK-75 | Test with >500 target list: warning emitted before nmap invocation; `--max-parallelism` present in nmap args |
| Multi-target file-path token | BACK-77 | Interactive wizard test: `targets.txt` (non-existent file) input produces warning, not silent NXDOMAIN scan |
| IPv6 literal in target list | BACK-77 | `::1` as FQDN input: does not raise unhandled ValueError |
| Documentation drift | BACK-65/66 | CLI help text snapshot compared against operator's guide content; version string matched |

---

## Sources

- QU.I.R.K. codebase — `quirk/scanner/tls_scanner.py`, `quirk/engine/risk_engine.py`, `quirk/discovery/nmap_provider.py`, `quirk/interactive.py`, `quirk/scanner/target_expander.py`, `pyproject.toml` (direct code inspection, HIGH confidence)
- `.planning/PROJECT.md` Key Decisions — impacket/pyOpenSSL conflict decision recorded explicitly (HIGH confidence)
- [sslyze issue #355 — verified_certificate_chain None for internal CAs](https://github.com/nabla-c0d3/sslyze/issues/355) (MEDIUM confidence)
- [NIST CSRC — FIPS 203/204/205 finalized August 2024](https://csrc.nist.gov/news/2024/postquantum-cryptography-fips-approved) (HIGH confidence)
- [PCI-DSS 4.0 cryptographic requirements — Req 4.2.1/4.2.1.1](https://www.appviewx.com/blogs/decoding-the-pci-dss-v4-0-cryptographic-requirements/) (MEDIUM confidence — cross-verify against pcisecuritystandards.org before shipping compliance mappings)
- [Nmap performance — host timeout, parallelism options](https://nmap.org/book/man-performance.html) (HIGH confidence)
- [Python optional import patterns — module-level try/except](https://discuss.python.org/t/optional-imports-for-optional-dependencies/104760) (HIGH confidence)
- [Clock skew and TLS certificate validity — UTC naive datetime pitfall](https://shop.trustico.com/blogs/stories/how-time-synchronization-affects-ssl-certificate-validation-why-incorrect-clocks-cause-certificate-errors) (MEDIUM confidence)

---
*Pitfalls research for: QU.I.R.K. v4.6 Enterprise Readiness milestone*
*Researched: 2026-05-03*
