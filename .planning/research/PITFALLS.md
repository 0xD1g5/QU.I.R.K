# Pitfalls Research

**Domain:** Cryptographic inventory scanner — stabilization + tech debt sweep (v5.0)
**Researched:** 2026-05-22
**Confidence:** HIGH for project-specific pitfalls (code read); MEDIUM for OQS/sslyze observability (multiple external sources)

---

## Critical Pitfalls

### Pitfall 1: lxml XXE — load_dtd=True silently re-enables entity expansion even with resolve_entities=False

**What goes wrong:**
`resolve_entities=False` alone blocks *external* entity resolution but does NOT block billion-laughs-style internal entity expansion if the DTD is loaded. Calling `ET.XMLParser(resolve_entities=False, load_dtd=True)` appears safe but allows internal entity recursion because loading the DTD enables the parser to process internal entity declarations. A billion-laughs payload (nested `&lol;` entities) can saturate memory in milliseconds despite `resolve_entities=False` being present.

The existing `saml_scanner.py` implementation is currently correct:

```python
ET.XMLParser(resolve_entities=False, no_network=True)
```

The danger emerges if a future developer adds `load_dtd=True` (to inspect DTD-constrained schemas) without understanding the interaction. There are three specific footguns:

**Footgun 1 — `load_dtd=True`:** Makes internal entity declarations in the DTD processable, removing the backstop against billion-laughs payloads.

**Footgun 2 — `huge_tree=True`:** Removes lxml's internal depth and text-length limits. Tempting for large SAML metadata federation files. Combined with internal entity lists in the DTD it removes all resource bounds.

**Footgun 3 — `iterparse()` does not inherit XMLParser options in all lxml versions:** The current codebase uses `fromstring()` (via `_safe_ET_fromstring`). Any future streaming XML parse must explicitly pass the hardened parser; `lxml.etree.iterparse(f)` uses different defaults.

**Footgun 4 — `nmap_parser.py` currently uses defusedxml:** When BACK-67 migrates `nmap_parser.py` to lxml, the parser config must be copied explicitly from `saml_scanner.py`. Leaving it to lxml defaults would be a silent regression.

**Why it happens:**
`load_dtd` and `resolve_entities` sound orthogonal. Developers adding `load_dtd=True` for unrelated reasons (e.g., DTD-constrained validation of SAML federation metadata) remove the entity-expansion backstop without knowing it.

**How to avoid:**
The safe configuration, explicit about all four relevant flags:

```python
ET.XMLParser(
    resolve_entities=False,   # block external + internal entity resolution
    no_network=True,          # block all network fetches during parse
    load_dtd=False,           # do NOT load DTD (default=False — be explicit)
    huge_tree=False,          # do NOT remove depth/size limits (default=False — be explicit)
)
```

Write this as a module-level constant in a shared `quirk/util/xml_safe.py` helper:

```python
# quirk/util/xml_safe.py
import lxml.etree as ET

SAFE_XML_PARSER = ET.XMLParser(
    resolve_entities=False,
    no_network=True,
    load_dtd=False,
    huge_tree=False,
)

def safe_fromstring(xml_bytes: bytes):
    return ET.fromstring(xml_bytes, parser=SAFE_XML_PARSER)
```

Both `saml_scanner.py` and `nmap_parser.py` import from this helper after migration. Add a pytest fixture that confirms parsing a billion-laughs payload raises rather than hanging. After migration, remove `defusedxml` from `pyproject.toml` core deps after confirming `grep -r "defusedxml" quirk/` returns zero.

**Warning signs:**
- Any PR adding `load_dtd=True` or `huge_tree=True` to an `XMLParser` call.
- Any `.py` file that does `import lxml.etree as ET` and calls `ET.parse()` or `ET.fromstring()` without constructing an `XMLParser` with the safe flags.
- `defusedxml` still in `pyproject.toml` after the migration phase completes.

**Phase to address:**
Phase 87 (dependency hygiene — the first v5.0 phase, before the 2026-06-02 internal deadline). The lxml migration for `nmap_parser.py` and the `quirk/util/xml_safe.py` shared parser constant must land together in one plan.

---

### Pitfall 2: OQS-nginx — TLS group name instability across oqs-provider versions breaks docker-compose AND scanner observation simultaneously

**What goes wrong:**
The OQS project has renamed algorithm identifiers between releases. The confirmed example: `p384_mlkem1024` was renamed to `SecP384r1MLKEM1024` in oqs-provider 0.9.0 (mid-2025). A docker-compose pinned to `openquantumsafe/nginx:latest` will silently pull a newer image with different group names, causing the nginx `ssl_conf_command Groups X25519MLKEM768:SecP256r1MLKEM768` directive to fail with a cryptic OpenSSL error at container startup — not at `docker-compose up` parse time.

Second confirmed breakage: when OpenSSL 3.5.0 is loaded alongside oqs-provider 0.9.0+, the provider **automatically disables** the pure ML-KEM groups (`mlkem512`, `mlkem768`, `mlkem1024`) in favour of the hybrid variants to avoid double-registration. A docker-compose specifying `mlkem768` as a group silently fails or falls back.

**sslyze observability limitation (distinct from the version-fragility problem):**
sslyze does not have native post-quantum TLS group support in its current release (6.x). sslyze enumerates cipher suites via its own nassl/OpenSSL client build. If that nassl build does not include oqs-provider, sslyze will not advertise PQC key_share extensions in the ClientHello. The server falls back to the best classical group both sides share (e.g., X25519). The connection succeeds; sslyze returns cipher suite and cert data; but PQC group negotiation is NOT observed.

This means: if QUIRK only uses sslyze for the OQS-nginx profile, the scanner will report a successful TLS connection with classical ciphers, missing the entire point of the profile.

**Why it happens:**
The OQS project moved fast because NIST PQC standardization was still in motion through 2024-2025. Algorithm naming tracked NIST drafts → final names. Every `latest` docker tag upgrade can be a breaking change on group names, code points, and hybrid compositions.

**How to avoid:**
Pin the docker image to a specific digest or dated tag:

```yaml
# docker-compose.yml
image: openquantumsafe/nginx@sha256:<digest>  # pin exact version
# OQS: oqs-provider 0.11.0 / liboqs 0.14.0 — group names: X25519MLKEM768, SecP256r1MLKEM768
```

Document the expected oqs-provider version and liboqs version in a comment. The `expected_results_oqs.md` oracle must include the exact group name negotiated (e.g., `X25519MLKEM768`) so CI can detect when a version upgrade silently changes it.

**Fallback strategy when sslyze cannot observe PQC:**
Supplement with a raw `ssl.SSLContext` probe built against system OpenSSL (3.5+) with oqs-provider:

```python
ctx = ssl.create_default_context()
ctx.set_alpn_protocols(["http/1.1"])
# If system openssl has oqs-provider:
ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
# Connect, extract cipher name, check for MLKEM in negotiated group
```

Alternatively use a `curl` subprocess: `curl --curves X25519MLKEM768 --verbose` and parse the `SSL connection using ... / X25519MLKEM768` line. Label the endpoint protocol `PQC-HYBRID-TLS` to distinguish from the standard TLS path.

If neither approach is feasible, emit an `ADVISORY`-category finding: `OQS-nginx PQC-hybrid profile reachable — scanner cannot confirm hybrid group negotiation (sslyze lacks PQC key_share support)`. This preserves the demo value without overstating what the scanner measured.

**Warning signs:**
- Container starts and immediately exits: `nginx: [emerg] invalid value "mlkem768" in ssl_conf_command` — group name drift.
- `quirk scan` shows `TLS_AES_256_GCM_SHA384` with `X25519` key exchange on the OQS-nginx port — classical fallback occurred (PQC not observed).
- `expected_results_oqs.md` shows a group name that doesn't match what the container logs report.

**Phase to address:**
BACK-81 chaos lab phase. Must include: (a) pinned image digest, (b) startup smoke test logging the negotiated group, (c) expected_results oracle with exact group name, (d) fallback advisory finding if sslyze cannot observe PQC, (e) CLAUDE.md obligations: lab.sh `ALL_PROFILES` + README + expected_results in the same change.

---

### Pitfall 3: New TLS chaos profiles — STARTTLS vs implicit TLS confusion causes silent scanner miss

**What goes wrong:**
The existing codebase documents: "sslyze CANNOT speak Redis (no app-layer banner)" — Redis requires a raw `ssl.SSLContext` probe because sslyze sends a TLS ClientHello immediately without issuing the Redis `HELLO` command first, causing the server to drop the connection. The same class of problem applies to every new non-HTTP TLS profile:

**PostgreSQL TLS (BACK-80):** PostgreSQL requires an 8-byte SSLRequest message before the TLS handshake. sslyze has a `--starttls postgres` mode (`ProtocolWithOpportunisticTlsEnum.POSTGRES`) that sends this preamble. If the chaos lab postgres-tls target is probed without this kwarg, the connection is dropped silently.

**SMTP/STARTTLS (BACK-82):** SMTP on port 587 requires `EHLO` + `STARTTLS` exchange before TLS negotiation. The existing email_scanner handles this correctly. The pitfall for a new chaos lab SMTP/STARTTLS profile: do NOT use port 465 (implicit SMTPS) with a `starttls_enum` kwarg. The two upgrade mechanisms are mutually exclusive — mixing them causes sslyze to timeout because the server waits for `EHLO` while sslyze tries a direct TLS ClientHello.

**gRPC TLS (BACK-83):** gRPC uses HTTP/2 with ALPN `h2`. sslyze does probe ALPN but does not emit an HTTP/2 connection preface (`PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n`). The gRPC server, expecting that preface after TLS, may GOAWAY or close the connection. Practical risk: sslyze extracts the certificate and negotiates TLS, but the resulting endpoint gets labeled generic `TLS` instead of `gRPC-TLS` in the CBOM. This is a protocol-label error in the CBOM output.

**Kafka TLS (BACK-84):** Kafka 9093/9094 use implicit TLS (no pre-negotiation handshake). The existing `_scan_one_sslyze_kafka` already handles these correctly. The pitfall is the chaos lab **Docker healthcheck**: Kafka healthchecks must use a plaintext listener, not the TLS listener. A healthcheck pointing at the TLS port with a raw TCP check causes the container to appear unhealthy indefinitely.

**Why it happens:**
"TLS" is not a uniform surface — application-layer TLS negotiation is protocol-specific. Copy-pasting a chaos lab service block from a working profile without adjusting the health check port and sslyze `starttls_enum` causes silent failures that look like scanner bugs.

**How to avoid:**
For each new chaos lab TLS profile, answer three questions before writing any code:
1. Implicit TLS (sslyze raw probe) or opportunistic STARTTLS (must pass `tls_opportunistic_encryption` kwarg)?
2. Does the Docker healthcheck need a plaintext or TLS port?
3. What application-layer banner or ALPN does the server require post-handshake?

For gRPC: use a separate probing function that explicitly sets `ctx.set_alpn_protocols(["h2"])` before the handshake. Label the endpoint `gRPC-TLS` explicitly so the CBOM builder's `else` (TLS default) branch captures cipher suite and cert correctly.

**Warning signs:**
- Chaos lab container shows `healthy` but `quirk scan` returns zero TLS findings for that port — sslyze probe returning `None` due to application-layer rejection.
- Expected_results oracle says port 587 but scan returned a finding on port 465 (or vice versa) — STARTTLS/implicit confusion.
- `./lab.sh status` shows kafka-tls as unhealthy because healthcheck targets the TLS port.

**Phase to address:**
The BACK-80/82/83/84 chaos lab phases. Each new profile must be tested with `./lab.sh up --profile <name>` followed by a raw `quirk scan --targets localhost --ports <port>` before the phase is marked complete. CLAUDE.md obligations apply to every profile: lab.sh `ALL_PROFILES` + README + expected_results updated in the same PR.

---

### Pitfall 4: Scoring fixes — same-bug-class miss leaves render paths out of sync

**What goes wrong:**
v4.10.1 fixed the backend aggregation (`sum / 1.5`) and the dashboard `ScoreGauge` frontend in one atomic phase. Three items were explicitly deferred to v5.0 and carry the same-bug-class risk:

**EVIDENCE-TALLY-01:** Three subscores (data_at_rest, data_in_motion, identity_trust) show exactly 25 despite HIGH/CRITICAL findings for those surfaces. Root cause is different from the aggregation bug: `build_evidence_summary()` in `evidence.py` populates evidence counter keys, but if a scanner emits a `CryptoEndpoint` with `service_detail="MySQL/SSL-OFF"` (which generates a finding via `risk_engine.py`) without the corresponding evidence counter increment firing (`dar_db_weak_ssl_count` in `evidence.py`'s counter loop), the subscore starts at the maximum and no penalty fires. This means a scan with 5 `Database plaintext connections` findings still scores `data_at_rest: 25` after the v4.10.1 aggregation fix.

**RENDER-CLI-01 / RENDER-PDF-01:** The v4.10.1 retrospective identified these as "same bug class likely lives in CLI/HTML/PDF renderers." If the CLI has a separate `_format_score()` function in `writer.py` that formats or rounds the score independently, it may apply a different scale interpretation. If Jinja2 templates for HTML/PDF were authored assuming the overall score is 0–100 and subscores are 0–25, they may already be correct — or they may have hardcoded comparisons (`{% if score > 80 %}`) that use a different threshold.

**The same-bug-class miss pattern:** Fixing EVIDENCE-TALLY-01 by patching one evidence counter (e.g., `dar_db_plaintext_count`) without auditing all six subscore counter families means a different subscore still vacuously shows 25. This is exactly how the original aggregation bug survived for multiple releases.

**Why it happens:**
Finding emission and evidence counter increment are in different code paths. A scanner emits a finding through `risk_engine.py`; separately `build_evidence_summary()` reads `ep.service_detail` to increment counters. If the service_detail format changes (e.g., `"MySQL/SSL-OFF"` vs `"MySQL/ssl-off"` case mismatch) the counter doesn't fire but the finding still appears.

**How to avoid:**
Before writing any fix for EVIDENCE-TALLY-01:
1. Write a parametrized pytest test for all six subscore families. Each test creates a synthetic scan result with one HIGH finding for that surface and asserts `subscore < 25`. All six start RED.
2. Fix evidence counter paths family by family, confirming GREEN after each.
3. For RENDER-CLI-01 and RENDER-PDF-01: locate every place the score dict is consumed outside of `scoring.py` — `writer.py`, Jinja2 templates, FastAPI response serializer. Assert no rendering path re-clamps or re-normalizes independently.
4. After all three are GREEN: run `quirk scan` against the chaos lab `database` profile (plaintext MySQL), confirm `data_at_rest` subscore < 25, confirm CLI output matches JSON matches dashboard matches PDF.

**Warning signs:**
- Subscore is exactly 25 AND there are HIGH-or-CRITICAL findings for that surface in the same scan — evidence counter not firing.
- CLI shows a different overall score than the dashboard for the same scan ID — separate rendering scale.
- PDF shows `100 EXCELLENT` while dashboard shows `80 GOOD` for the same scan.

**Phase to address:**
The scoring residuals phase (absorbs EVIDENCE-TALLY-01, RENDER-CLI-01, RENDER-PDF-01). Do NOT combine with CBOM Pass-1 or chaos lab work — the same-bug-class risk is high enough that it deserves isolated RED-GREEN-REFACTOR discipline. The six-family parametrized test is the mandatory exit criterion.

---

### Pitfall 5: Dead-code removal — "dead" code reachable via dynamic dispatch, optional-extra imports, or __init__.py re-exports

**What goes wrong:**
The project has a documented optional-extra import trap: unconditional top-level imports of optional-extra deps silently break the CLI on minimal install. The inverse pitfall for dead-code removal: removing a function that appears to have zero callers in a `grep` search but is actually reachable via:

**Pattern 1 — Dynamic dispatch in `run_scan.py`:** `_wrapped_phase(scan_fn, ...)` passes a module-level function object. If the function name was changed or an alias was added, a grep for direct call sites shows 0 callers, but the function is reachable via the wrapped dispatch.

**Pattern 2 — Test-only callers:** BACK-50 calls out `build_scorecard_markdown()` in `scorecard.py` as "only called from tests." If the test that calls it is the only test coverage for a CBOM or report formatting code path, deleting the function AND its test removes coverage entirely, not just dead code.

**Pattern 3 — `__init__.py` re-exports:** Some modules have `__all__` exports re-exported by `quirk/__init__.py`. Deleting a function in `__all__` without updating `__init__.py` causes `ImportError` only when users do `from quirk import X` — which may not be tested in the unit suite but is exercised in the wild.

**Pattern 4 — `migration_planner.py` dual categorization (BACK-51):** The roadmap note says `categorize_waves()` "produces `NOW/NEXT/LATER` for terminal output." If any `quirk` CLI subcommand (even undocumented) calls this, removing it breaks that subcommand. The correct call-graph trace starts from `pyproject.toml [project.scripts]`, not from grep.

**Pattern 5 — `tqdm` dead branch (BACK-54):** `tqdm = None` at module scope means `if tqdm:` is always False — this is an unconditionally dead branch confirmed by static analysis. But removing the `tqdm>=4.67` dep from `pyproject.toml` must be verified: does any other module import tqdm? Search for all `import tqdm` and `from tqdm` occurrences, not just in the file being cleaned.

**Why it happens:**
Grep-based dead code detection misses dynamic dispatch and import re-exports. The `tqdm` case is the cleanest example in this codebase: a grep for `tqdm` finds 2 imports + 1 conditional, looks like 3 live usages, but all three are dead because the branch condition is always False.

**How to avoid:**
Before removing any item from BACK-49 through BACK-57:
1. Confirm zero callers via `vulture` or an AST-based analysis (not just grep). Pay specific attention to `run_scan.py`'s `_wrapped_phase` dispatch.
2. For test-only callers: check if the test asserts behavior that should remain tested via a different entry point. If yes, rewrite the test first, THEN delete the function.
3. Check `quirk/__init__.py` and `pyproject.toml [project.scripts]` for re-exports and CLI wiring.
4. For BACK-54 (`tqdm`): remove from `pyproject.toml` AND search all `import tqdm` / `from tqdm` across the full codebase.
5. After deletion: `pip install -e .` on a clean venv + `quirk --help` + every subcommand `--help` must all succeed.

Split BACK-49–57 into two tiers:
- **Tier A (safe, no call-graph risk):** BACK-53 (`qcscan-legacy.sqlite`), BACK-55 (D-reference comments), BACK-56 (`datetime.utcnow()`) — ship these first.
- **Tier B (requires call-graph audit):** BACK-49 (rules.py), BACK-50 (writer.py helpers), BACK-51 (migration_planner), BACK-52 (dead intelligence modules), BACK-54 (tqdm) — ship only after full analysis.

**Warning signs:**
- `ImportError: cannot import name 'X' from 'quirk'` after deletion — function was in `__init__.py` re-exports.
- A test file not updated imports a deleted function and fails — the test was the only caller and should have been updated first.
- `quirk migrate` or `quirk report` CLI subcommand throws `AttributeError` — subcommand used the deleted function.

**Phase to address:**
Dead-code cleanup phase (BACK-49–57). Tier A first, Tier B second. Each deletion batch must be followed by a clean-venv smoke test.

---

### Pitfall 6: Node 20 → 24 — two workflows need updating, the hard-failure date is September 16 2026, and release-container.yml does NOT use setup-node

**What goes wrong:**
PROJECT.md and HORIZON.md state the deadline as "2026-06-02." The official GitHub timeline:
- **June 16, 2026:** Runners default to Node 24; Node 20 still works but triggers deprecation warnings in every run.
- **September 16, 2026:** Node 20 removed from runners entirely — workflows hard-fail.

The June 2 internal target is a "no-more-warnings" goal; the real hard-failure date is September 16.

Reading `release-container.yml` directly confirms it does NOT use `actions/setup-node` — it runs only Docker build steps. The explicit `node-version: '20'` pin is in `dashboard-quality.yml` line 22. If `release.yml` also has a Node pin it needs updating too.

The invisible Node 20 usage: compiled JavaScript bundles inside GitHub Actions (e.g., `actions/checkout@v4`, `docker/build-push-action@v6`) use Node internally. These are maintained by action authors; the user's responsibility is to use recent enough action versions. After the September 16 deadline, old action bundles that bundle Node 20 will fail.

**Why it happens:**
There are two separate Node 20 surfaces: (1) the user-controlled `node-version: '20'` pin (easy to find and fix) and (2) the compiled Node version inside third-party action bundles (invisible until the runner removes it). Developers who update only surface (1) can still have failing workflows due to surface (2).

**How to avoid:**
Two-step fix:
1. Change `node-version: '20'` to `node-version: '24'` in `dashboard-quality.yml` (and `release.yml` if applicable).
2. Verify action versions in all workflows are at releases that use Node 24 runtimes: `actions/checkout@v4`, `docker/setup-qemu-action@v3`, `docker/setup-buildx-action@v3`, `docker/login-action@v3`, `docker/build-push-action@v6`. Check each action's release notes for "Node 20 → 24 migration" entries.

Validation must be via an actual GitHub Actions run on a branch — local execution cannot confirm GHA runner Node version behavior.

**Warning signs:**
- GHA workflow log: `Node.js 20 actions are deprecated. Please update the following actions to use Node.js 24: ...`
- After June 16, 2026: workflows emit warnings on every run even if the build passes.
- After September 16, 2026: `Error: Node.js 20 is not supported` (hard failure).

**Phase to address:**
Phase 87, Plan 1 (before anything else, before lxml migration). Two-file change, CI validation via a test branch push. Must not be bundled with lxml migration in the same plan because a CI failure in one must not block the other.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `defusedxml` as fallback in `saml_scanner.py` after lxml migration | Zero parser config risk | Two codepaths diverge; defusedxml uses stdlib ET (no XPath namespace support) | Never after BACK-67 — remove the fallback completely |
| Pinning OQS-nginx docker image to `latest` | Always gets newest algorithms | Group name renames break nginx config silently between lab runs | Never for a profile whose expected_results oracle is a CI gate |
| Grep-based dead-code detection instead of AST/import analysis | Fast audit | Misses dynamic dispatch and `__init__.py` re-exports | Only for files with no `__all__`, no re-exports, and no string dispatch |
| Fixing one render path (dashboard) and assuming CLI/PDF match | Hotfix ships faster | CLI shows stale score; PDF shows wrong score | Never — the v4.10.1 retrospective chose the atomic fix for exactly this reason |
| Removing `tqdm` from source but not from `pyproject.toml` | Grep looks clean | `pip install quirk` still installs tqdm; reappears on next dep update | Never — dep removal must be atomic with source removal |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| lxml XMLParser | Omitting `load_dtd=False` and `huge_tree=False` (both default False but easy to accidentally set True) | Declare all four flags in a shared `_SAFE_XML_PARSER` constant in `quirk/util/xml_safe.py`; add billion-laughs test |
| OQS-nginx docker image | Using `:latest` tag; using Kyber-era group names (`kyber512`, `p384_mlkem1024`) | Pin to digest; use current names (`X25519MLKEM768`, `SecP256r1MLKEM768`); validate with `openssl s_client -groups X25519MLKEM768` |
| sslyze vs PostgreSQL TLS | Raw sslyze probe without `ProtocolWithOpportunisticTlsEnum.POSTGRES` | Always pass `tls_opportunistic_encryption=ProtocolWithOpportunisticTlsEnum.POSTGRES` for postgres-tls profiles |
| sslyze vs SMTP STARTTLS | Using port 465 (implicit) with a `starttls_enum` kwarg | Port 465: no kwarg (implicit TLS). Port 587: `ProtocolWithOpportunisticTlsEnum.SMTP`. Never mix |
| Kafka TLS Docker healthcheck | Pointing healthcheck at 9093 (TLS listener) with plaintext TCP check | Use plaintext listener (9092) for healthcheck |
| gRPC TLS scanner | Generic sslyze broker probe (no ALPN h2) | Raw `ssl.SSLContext` probe with `ctx.set_alpn_protocols(["h2"])`; label endpoint `gRPC-TLS` |
| Evidence counter increment | Finding emitted via risk_engine without corresponding counter increment in `evidence.py` | Trace from scanner → risk_engine finding → evidence.py counter for every new surface; RED test asserting subscore < 25 when finding present |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `load_dtd=True` with `resolve_entities=False` | Billion-laughs DoS via internal entity expansion | Shared `_SAFE_XML_PARSER` constant; CI grep gate: `grep -r "load_dtd=True"` must return 0 |
| `huge_tree=True` on any lxml parser processing untrusted XML | Removes all memory/depth bounds | CI grep gate: `grep -r "huge_tree=True"` must return 0 |
| Removing XXE test after migration (since defusedxml handled it before) | Security regression invisible until deployed | Keep the billion-laughs test; migrate it from defusedxml testing to direct lxml testing |
| PQC group name drift without oracle update | Scanner reports wrong group; scoring ceiling is untestable | Pin docker image digest; expected_results oracle includes exact group name string |

---

## "Looks Done But Isn't" Checklist

- [ ] **lxml migration (BACK-67):** Both files migrated (`saml_scanner.py` current pass; `nmap_parser.py` must be updated) AND `defusedxml` removed from `pyproject.toml` AND billion-laughs test exists AND `grep -r "defusedxml" quirk/` returns 0.
- [ ] **OQS-nginx chaos profile (BACK-81):** Container starts healthy, scanner confirms TLS connection, CBOM Pass-1 emits an algo component for the negotiated KEM algorithm, lab.sh + README + expected_results all updated in the same PR.
- [ ] **EVIDENCE-TALLY-01 fix:** All six subscore families have a parametrized RED test asserting `subscore < 25` when a HIGH finding exists for that surface; all six GREEN after the fix.
- [ ] **RENDER-CLI-01 / RENDER-PDF-01:** CLI output checked against dashboard for same scan ID; PDF export checked against both. Not just "code looks right" — actual rendered output confirmed.
- [ ] **Dead code removal (BACK-49–57):** `pip install -e .` on a clean venv + `quirk --help` + every subcommand `--help` succeed after each deletion batch.
- [ ] **Node 20 → 24:** GitHub Actions workflow run on a real branch shows zero Node deprecation warnings; dashboard-quality CI passes with the new node version.
- [ ] **New chaos lab profiles (BACK-80–84):** Each profile has: healthy container via `./lab.sh status`, scanner finding, CBOM algo component, expected_results oracle entry, lab.sh ALL_PROFILES inclusion, README section — all in the same PR.

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| lxml XXE footguns (load_dtd, huge_tree, iterparse) | Phase 87 (dependency hygiene) | Billion-laughs pytest test passes; `grep -r "huge_tree=True"` returns 0; `grep -r "defusedxml" quirk/` returns 0 after migration |
| OQS-nginx group name instability | BACK-81 chaos lab phase | `docker-compose up --profile oqs-nginx` shows healthy; oracle test confirms exact group name string in expected_results |
| sslyze PQC observability gap | BACK-81 chaos lab phase | Either PQC group negotiated and recorded in endpoint protocol, or advisory finding emitted explaining the limitation |
| STARTTLS vs implicit TLS confusion (new profiles) | BACK-80/82/83/84 phases | `quirk scan` against each new profile returns a TLS finding with correct port and protocol label |
| Kafka healthcheck against TLS listener | BACK-84 phase | `./lab.sh status` shows kafka-tls as healthy; scanner finds Kafka TLS on 9093 |
| Scoring same-bug-class miss (evidence tally + render paths) | Scoring residuals phase | Six-family parametrized RED/GREEN test suite; CLI/dashboard/PDF output comparison for same scan ID |
| Dead code removal via grep only | Dead-code cleanup phase | `vulture` or AST analysis reviewed; clean-venv smoke test after each deletion batch |
| Node 20 deprecation (dashboard-quality.yml) | Phase 87 (first plan) | GHA run shows zero Node deprecation warnings |

---

## Sources

- Project codebase: `quirk/scanner/saml_scanner.py` (existing lxml safe parser at lines 5–13 — current correct config with `resolve_entities=False, no_network=True`)
- Project codebase: `quirk/discovery/nmap_parser.py` (still uses `defusedxml.ElementTree` — target for BACK-67 migration)
- Project codebase: `quirk/scanner/broker_scanner.py` lines 677–705 (`_probe_redis_tls` — documents "sslyze CANNOT speak Redis" pattern; model for gRPC probe; confirms redis raw ssl.SSLContext approach)
- Project codebase: `quirk/cbom/builder.py` lines 395–552 (Pass-1 protocol dispatch — confirmed `KUBERNETES` and `CLOUD_SQL` are intentional no-ops; `MOTION_PLAINTEXT_PROTOCOLS` is intentional; the 5 vacuously-passing profiles from OBS-1 map to `POSTGRESQL`/`RDS` branch which requires `cert_pubkey_alg` to be set — if the chaos lab DB scanner doesn't populate that field the branch fires but `_register_algorithm` is never called)
- Project codebase: `.github/workflows/dashboard-quality.yml` line 22 — `node-version: '20'` confirmed
- Project codebase: `.github/workflows/release-container.yml` — confirmed no `actions/setup-node` usage
- `.planning/RETROSPECTIVE.md`: v4.10.1 section (aggregation vs penalty-model-change distinction; same-bug-class deferred items); Cross-Milestone Trends Lesson 5 (optional-extra import trap)
- `.planning/PROJECT.md`: v5.0 milestone context; BACK-67 description; Phase 42 OBS-1 context; Node 20→24 internal deadline
- WebSearch + GitHub Changelog: Node 20 deprecation — June 16, 2026 default switch; September 16, 2026 hard removal ([GitHub Changelog](https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/))
- WebSearch: OQS-provider group renames — `p384_mlkem1024` → `SecP384r1MLKEM1024` in oqs-provider 0.9.0; `mlkem512/768/1024` disabled when OpenSSL 3.5 + oqs-provider 0.9.0+ loaded ([oqs-provider releases](https://github.com/open-quantum-safe/oqs-provider/releases))
- WebSearch + lxml docs: lxml security — `load_dtd=False` and `huge_tree=False` must be explicit; `resolve_entities=False` alone does not block internal entity expansion if DTD is loaded ([lxml parsing docs](https://lxml.de/parsing.html), [defusedxml README](https://github.com/tiran/defusedxml))
- WebSearch: sslyze PQC — no native PQC group enumeration in current release; negotiates via nassl OpenSSL build without oqs-provider ([sslyze GitHub](https://github.com/nabla-c0d3/sslyze))
- WebSearch: gRPC TLS scanning — ALPN `h2` and HTTP/2 preface required; sslyze cipher reports work but ALPN-specific behavior depends on gRPC server ([gRPC issue #37016](https://github.com/grpc/grpc/issues/37016))

---
*Pitfalls research for: QU.I.R.K. v5.0 Stabilization + Tech Debt Sweep*
*Researched: 2026-05-22*
