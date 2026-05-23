# Phase 96: Active REST Fuzzing — Research

**Researched:** 2026-05-23
**Domain:** schemathesis programmatic dispatch, TLS crypto-posture fuzzing, JWT alg-confusion, safety gating, chaos lab
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Engine: `schemathesis` drives request dispatch against Phase-94-discovered OpenAPI
  endpoints; custom crypto-posture assertions are applied to responses/connection.
- **Day-1 task:** verify `schemathesis Case.as_transport_kwargs()` httpx dispatch
  integration before building on it (carried-over gap note).
- Probe set (FUZZ-01): TLS downgrade, cipher acceptance, HSTS, HTTP-only credential
  transmission — reuse existing TLS scanner capabilities for the crypto checks.
- Endpoint source: Phase 94 OpenAPI endpoint discovery + `cfg.targets`; no fuzzing
  without a discovered, in-scope endpoint.
- Six safety guardrails (FUZZ-02):
  1. GET-only by default; other HTTP methods require explicit opt-in.
  2. Hard budget ceiling: default 50, hard max 500 — exceeding aborts.
  3. Rate cap: 5 req/s default (reuse the nmap TokenBucket pattern).
  4. `CONFIRM` prompt.
  5. Target-scope enforcement via `validate_external_url` + `cfg.targets`.
  6. 5xx-cascade pause after 3 consecutive 5xx responses.
- CONFIRM gate: TTY → present budget summary + require literal word `CONFIRM`; non-TTY →
  hard-abort BEFORE sending any request (differs from nmap which auto-proceeds).
- JWT alg-confusion (FUZZ-04) behind `--fuzz-jwt-alg-confusion` sub-flag; reuse Phase 93
  CredentialContext + Phase 94 token decode/classify.
- `schemathesis` added to `[api]` extras only (excluded from `[all]`); existing CI guard
  `tests/test_install_all_excludes_schemathesis.py` already enforces this.
- Chaos lab: NEW isolated `fuzz-target` profile — update `lab.sh` ALL_PROFILES (dynamic
  `_derive_all_profiles`), chaos README, and `expected_results_*.md` in the same change.
- Scoring: fuzzing findings feed `agility_signals`; SCORE_WEIGHTS +4.0 → 303.0. Update
  BOTH the sum AND count invariant assertions together.

### Claude's Discretion

- Exact evidence counter key(s) for the fuzzing agility signal, the weight split, module
  structure, and CONFIRM prompt wording.

### Deferred Ideas (OUT OF SCOPE)

- POST/PUT/DELETE fuzzing by default — GET-only default; opt-in only.
- Generic schema-validation fuzzing beyond crypto-posture probes.
- Fuzzing without a discovered/scoped endpoint (ad-hoc URL).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FUZZ-01 | Opt-in active REST crypto-posture fuzzing (TLS downgrade, cipher, HSTS, HTTP-only cred), gated behind flag + CONFIRM + bounded budget | schemathesis `from_dict` + `include(method='GET')` + `get_all_operations()` + `case.as_transport_kwargs()` confirmed; requests.Session dispatch with per-request scope check |
| FUZZ-02 | Six safety guardrails: GET-only, hard budget, rate cap, CONFIRM, scope, 5xx-cascade | TokenBucket reuse confirmed; validate_external_url confirmed; CONFIRM gate pattern in targets.py |
| FUZZ-03 | Hard abort in non-TTY before any network request | Pattern confirmed: check `sys.stdin.isatty()` before request loop; test via `unittest.mock.patch` asserting zero requests sent |
| FUZZ-04 | JWT RS256→HS256 alg-confusion probe behind `--fuzz-jwt-alg-confusion` | PyJWT 2.12.1 `jwt.encode(..., secret=pub_key_pem, algorithm='HS256')` confirmed; CredentialContext.bearer_declared_alg() provides source alg |
| SCORE-01 | +4.0 → 303.0 final SCORE_WEIGHTS; fuzzing signals in agility_signals | Current state: sum=299.0, count=40; add 1 key at +4.0 → sum=303.0, count=41 |
| LAB-01 | Chaos lab fuzz-target profile: isolated weak REST target + oracle updates | `_derive_all_profiles` is dynamic (yq/grep parse), no ALL_PROFILES hardcoded list; just add profile to compose file + update README + expected_results_v4.md |
</phase_requirements>

---

## Summary

Phase 96 is the final delivery phase of the v5.1 milestone. It adds opt-in, defensively-gated active REST crypto-posture fuzzing using schemathesis as the request generator, feeding custom TLS/cipher/HSTS/credential-transmission assertions. The phase finalizes SCORE_WEIGHTS at 303.0 and adds the chaos lab `fuzz-target` profile.

The highest-risk item — `Case.as_transport_kwargs()` httpx dispatch integration — is now **fully verified** (see Code Examples). The method exists in schemathesis 4.4.4, returns a `{'method', 'url', 'headers', 'cookies', 'params'}` dict that can be unpacked directly into `requests.Session.request(**kwargs)`. schemathesis does pull `hypothesis` as a transitive dependency (for `strategy.example()`) and also imports `schemathesis.pytest` at module load time (a thin adapter layer), but the full `_pytest` runtime is NOT loaded — tests ran clean. This is acceptable for an `[api]` extras-only dep.

The CONFIRM gate is architecturally distinct from the existing nmap `maybe_confirm_probe_budget`: the nmap gate auto-proceeds in non-TTY; the fuzz gate HARD-ABORTS in non-TTY. This is a new function (`confirm_fuzz_gate`) in a new module `quirk/scanner/rest_fuzzer.py`. All safety code must be tested before any dispatch code per CONTEXT specifics.

**Primary recommendation:** Build the module as `quirk/scanner/rest_fuzzer.py`. Wave 0 installs schemathesis into `[api]` and writes gate tests. Wave 1 implements the fuzzer core (confirm gate, budget, rate limiter, scope check, TLS/cipher/HSTS probes, 5xx cascade). Wave 2 adds the JWT alg-confusion probe. Wave 3 wires run_scan.py flags, SCORE_WEIGHTS, evidence counter, and chaos lab.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CONFIRM / TTY gate | CLI / run_scan.py | rest_fuzzer.py (injectable fn) | Gate lives at the CLI boundary before scan entry; fuzzer module exposes injectable `prompt_fn` for tests |
| Request budget enforcement | rest_fuzzer.py | — | Hard ceiling on total dispatched requests; unbypassable internal counter |
| Rate limiting (5 req/s) | rest_fuzzer.py | TokenBucket (engine/rate_limiter.py) | TokenBucket is the existing shared primitive |
| Scope gate | rest_fuzzer.py | validate_external_url (util/url_allowlist.py) | Per-request SSRF guard using existing validator |
| schemathesis operation enumeration | rest_fuzzer.py | openapi_scanner.py (endpoint source) | Fuzzer calls `schemathesis.openapi.from_dict()` from the spec dict already parsed in Phase 94 |
| TLS downgrade / cipher / HSTS probes | rest_fuzzer.py | stdlib ssl / tls_scanner patterns | New probe functions; reuse tls_scanner cipher-weakness predicates |
| HTTP-only credential transmission probe | rest_fuzzer.py | CredentialContext | Probe sends creds over http:// URL variant; detects server acceptance |
| JWT alg-confusion probe | rest_fuzzer.py | credentials.py + analyze_token_cmd.py | Forge HS256 token using RS256 public key; detect 2xx response |
| Evidence accumulation | evidence.py | — | New `agility_fuzz_finding_count` counter; add to `_PROTOCOL_KEYS` as `"REST_FUZZ"` |
| Scoring | scoring.py + test_score_weights_invariant.py | — | New weight key; BOTH sum AND count invariants updated together |
| Chaos lab target | docker-compose.yml (fuzz-target profile) | — | Isolated FastAPI service with weak TLS config, accepts forged JWT |

---

## Standard Stack

### Core

| Library | Version (venv) | Purpose | Why Standard |
|---------|----------------|---------|--------------|
| schemathesis | 4.4.4 (PyPI) | OpenAPI spec → request generation; `Case.as_transport_kwargs()` dispatch | CONTEXT D-01 locked; confirmed works programmatically |
| requests | 2.33.1 | HTTP dispatch from `as_transport_kwargs()` kwargs | Already in venv; schemathesis also depends on it |
| httpx | 0.28.1 | TLS-level probes (custom SSL context for downgrade testing) | Already in venv; needed for TLS 1.0/1.1 attempt with custom context |
| PyJWT | 2.12.1 | HS256 token forge for alg-confusion probe | Already in venv; `jwt.encode(payload, pub_key_pem, algorithm='HS256')` confirmed |
| stdlib ssl | 3.11+ | TLS downgrade probe contexts (`ssl.SSLContext`, `ssl.TLSVersion`) | No dep; used in tls_scanner.py fallback path already |
| TokenBucket | (project) | 5 req/s rate cap | `quirk/engine/rate_limiter.py` — already used by nmap path |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hypothesis | 6.108+ (transitive via schemathesis) | `strategy.example()` draws one Case per operation | Used internally by schemathesis; do not call hypothesis directly |
| cryptography | (venv, >=44.0) | Extract RSA public key bytes for alg-confusion HMAC secret | Already a core dep; `serialization.Encoding.PEM` on public_key() |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `case.as_transport_kwargs()` + `requests` | `case.call()` | `call()` hits the live target directly but wraps hook machinery; `as_transport_kwargs()` gives a plain dict that QUIRK controls — easier to intercept for scope check + rate limit before dispatch |
| stdlib ssl for TLS downgrade | sslyze `ScanCommand.TLS_1_0_CIPHER_SUITES` | sslyze is the [scanner] extra; for fuzzing probes, stdlib ssl handshake attempt suffices and avoids heavy scanning overhead |

**Installation (Wave 0 task):**
```bash
# Add to pyproject.toml [api] extras (NOT [all])
# Then install dev environment:
.venv/bin/pip install -e ".[api]"
```

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| schemathesis | PyPI | ~7 yrs | 300k+/mo | github.com/schemathesis/schemathesis | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

slopcheck run: `slopcheck install schemathesis` → `[OK]`. [VERIFIED: PyPI registry + slopcheck]

---

## Architecture Patterns

### System Architecture Diagram

```
run_scan.py
  │ --fuzz flag present
  │ --fuzz-jwt-alg-confusion flag present
  ▼
confirm_fuzz_gate()          ← MUST fire before any network I/O
  │ non-TTY → HARD ABORT (zero requests)
  │ TTY → print budget summary → require "CONFIRM"
  │ any other input → clean abort
  ▼
rest_fuzzer.run_fuzz_scan(spec_dict, cfg, cred_ctx, opts)
  │
  ├─ schemathesis.openapi.from_dict(spec_dict)
  │    .include(method="GET")           ← GET-only default
  │    .get_all_operations()
  │
  ├─ For each operation (budget counter checked before dispatch):
  │    case = operation.as_strategy().example()
  │    kwargs = case.as_transport_kwargs(base_url=target_base_url)
  │    │
  │    ├─ validate_external_url(kwargs['url'], ...)  ← scope gate
  │    ├─ token_bucket.acquire()                     ← rate limit
  │    ├─ session.request(**kwargs)                  ← actual HTTP
  │    │
  │    ├─ crypto_probe_tls_downgrade(host, port)     ← ssl handshake
  │    ├─ crypto_probe_cipher(host, port)            ← cipher acceptance
  │    ├─ crypto_probe_hsts(response)                ← HSTS header check
  │    ├─ crypto_probe_http_creds(url, cred_ctx)     ← http:// cred send
  │    └─ [if --fuzz-jwt-alg-confusion]
  │         crypto_probe_alg_confusion(url, cred_ctx) ← forge HS256
  │
  ├─ 5xx cascade tracker → pause + warn at 3 consecutive 5xx
  └─ Yield List[CryptoEndpoint] with protocol="REST_FUZZ"
```

### Recommended Project Structure

```
quirk/scanner/
└── rest_fuzzer.py            # All fuzzing logic; public: run_fuzz_scan(), confirm_fuzz_gate()

tests/
├── test_rest_fuzzer_gate.py  # TTY/non-TTY confirm gate; budget; zero-requests assertion
├── test_rest_fuzzer_probes.py # TLS/cipher/HSTS/cred/alg-confusion probe unit tests
└── test_score_weights_invariant.py  # (existing — update sum+count)

quantum-chaos-enterprise-lab/
├── docker-compose.yml        # Add fuzz-target profile (port 20100)
├── fuzz-target/              # New service dir
│   ├── Dockerfile
│   ├── main.py               # Deliberately-weak FastAPI: no HSTS, accepts forged JWT
│   └── requirements.txt
├── expected_results_v4.md    # Add ## Profile: fuzz-target section
└── README.md                 # Add fuzz-target profile entry
```

### Pattern 1: schemathesis Programmatic Request Generation (VERIFIED)

```python
# Source: schemathesis 4.4.4 wheel inspection + live API test
import schemathesis
from schemathesis.core.result import Ok

def _iter_get_operations(spec_dict: dict, base_url: str):
    """Yield (operation, transport_kwargs) for GET-only operations."""
    schema = schemathesis.openapi.from_dict(spec_dict)
    get_schema = schema.include(method="GET")
    for result in get_schema.get_all_operations():
        if isinstance(result, Ok):
            op = result.ok()
            case = op.as_strategy().example()
            kwargs = case.as_transport_kwargs(base_url=base_url)
            # kwargs = {'method': 'GET', 'url': '...', 'headers': {...},
            #           'cookies': {}, 'params': {}}
            yield op, kwargs
```

**Verified output shape of `as_transport_kwargs()`:**
```python
{
  'method': 'GET',
  'url': 'http://localhost:8080/status',
  'cookies': {},
  'headers': {
    'User-Agent': 'schemathesis/4.4.4',
    'Accept-Encoding': 'gzip, deflate, zstd',
    'Accept': '*/*',
    'Connection': 'keep-alive',
    'X-Schemathesis-TestCaseId': 'tuu5NP'
  },
  'params': {}
}
```

### Pattern 2: CONFIRM Gate — Fuzz-Specific (NEW, distinct from maybe_confirm_probe_budget)

```python
# Source: quirk/util/targets.py maybe_confirm_probe_budget (analog) + CONTEXT.md FUZZ-03
import sys

def confirm_fuzz_gate(
    budget: int,
    target_count: int,
    is_tty: bool | None = None,
    prompt_fn=input,
    stderr_print_fn=None,
) -> bool:
    """Return True if fuzzing should proceed.

    CRITICAL: differs from maybe_confirm_probe_budget:
    - Non-TTY → HARD ABORT (returns False, prints error)
    - TTY → require literal 'CONFIRM' (not just y/n)
    - Any other input → abort (returns False)
    """
    if is_tty is None:
        is_tty = sys.stdin.isatty()

    if not is_tty:
        msg = (
            "ERROR: REST fuzzing requires interactive confirmation "
            "(non-TTY / headless mode detected). "
            "Fuzzing is disabled in non-interactive contexts. Aborting."
        )
        if stderr_print_fn:
            stderr_print_fn(msg)
        else:
            print(msg, file=sys.stderr)
        return False  # HARD ABORT — never auto-proceed

    # TTY: require the literal word CONFIRM
    answer = prompt_fn(
        f"[QUIRK FUZZ] About to send up to {budget} active requests to "
        f"{target_count} endpoint(s).\n"
        "Type CONFIRM to proceed (any other input aborts): "
    ).strip()
    return answer == "CONFIRM"
```

### Pattern 3: Budget Hard Ceiling (unbypassable)

```python
# Source: CONTEXT.md FUZZ-02 + codebase inspection
MAX_FUZZ_BUDGET: Final[int] = 500        # absolute hard cap; user cannot override
DEFAULT_FUZZ_BUDGET: int = 50

def _resolve_budget(requested: int | None) -> int:
    effective = requested if requested is not None else DEFAULT_FUZZ_BUDGET
    if effective > MAX_FUZZ_BUDGET:
        raise ValueError(
            f"Requested fuzz budget {effective} exceeds hard maximum {MAX_FUZZ_BUDGET}. "
            "Reduce --fuzz-budget."
        )
    return effective
```

### Pattern 4: TokenBucket Reuse for 5 req/s

```python
# Source: quirk/engine/rate_limiter.py (existing)
from quirk.engine.rate_limiter import TokenBucket

FUZZ_RATE_DEFAULT = 5.0  # req/s

limiter = TokenBucket(rate_per_sec=FUZZ_RATE_DEFAULT, capacity=FUZZ_RATE_DEFAULT)
# Before each request:
limiter.acquire()  # blocks until token available
```

### Pattern 5: Scope Gate Per Request

```python
# Source: quirk/util/url_allowlist.py validate_external_url
from quirk.util.url_allowlist import validate_external_url

def _check_scope(url: str, cfg_targets: list, allow_internal: bool) -> bool:
    result = validate_external_url(url, allow_internal=allow_internal)
    if not result.ok:
        logger.warning(f"Fuzz target URL rejected by scope gate: {result.reason}")
        return False
    return True
```

### Pattern 6: JWT RS256 → HS256 Alg-Confusion Forge

```python
# Source: PyJWT 2.12.1 (in venv) + analyze_token_cmd.py _decode_token pattern
import jwt
from cryptography.hazmat.primitives import serialization
from quirk.auth.credentials import CredentialContext

def _forge_hs256_token(bearer_token: str) -> bytes | None:
    """Forge an HS256 token using the RS256 public key as the HMAC secret.

    Returns the forged token bytes, or None if the source token is not RS256.
    The forged token has the SAME payload claims as the original — only the
    algorithm and signature differ.

    T-96-01: raw public key bytes are the HMAC secret (the classic alg-confusion
    attack; per https://auth0.com/blog/critical-vulnerabilities-in-json-web-token-libraries/).
    """
    try:
        header = jwt.get_unverified_header(bearer_token)
    except Exception:
        return None
    if header.get("alg", "").upper() != "RS256":
        return None  # only applicable to RS256 source tokens

    try:
        claims = jwt.decode(
            bearer_token,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=["RS256"],
        )
    except Exception:
        return None

    # Extract public key from JWKS or token 'x5c'/'jwk' header — if unavailable,
    # the probe cannot proceed (returns None). Fallback: probe_skipped finding.
    # TODO in plan: document the public key extraction path from the RS256 service.
    # For the chaos lab case: fetch /.well-known/jwks.json from the fuzz target.
    return None  # placeholder — full implementation in rest_fuzzer.py
```

**Key insight for alg-confusion probe:** The public key PEM bytes are used directly as the HMAC-SHA256 `key` argument in `jwt.encode()`. PyJWT 2.12.1 accepts this (emits an `InsecureKeyLengthWarning` for short keys, which is expected). The forged token, when sent to the server, is accepted only if the server uses the public key to verify HMAC signatures — i.e., the library is vulnerable to the alg-confusion CVE class.

### Pattern 7: TLS Downgrade Probe (stdlib ssl)

```python
# Source: quirk/scanner/tls_scanner.py _scan_one_fallback pattern + stdlib ssl
import ssl
import socket

def probe_tls_downgrade(host: str, port: int) -> bool:
    """Return True if server accepts TLS 1.0 or TLS 1.1 (a crypto-posture weakness)."""
    for tls_ver in (ssl.TLSVersion.TLSv1_1, ssl.TLSVersion.TLSv1):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = tls_ver
        ctx.maximum_version = tls_ver
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            with socket.create_connection((host, port), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=host):
                    return True  # accepted legacy version
        except (ssl.SSLError, OSError):
            continue  # refused or unsupported — good
    return False
```

**Note:** `ssl.TLSVersion.TLSv1` emits a `DeprecationWarning` in Python 3.12+. Suppress with `warnings.filterwarnings` in the probe or accept the warning — it is correct behavior.

### Pattern 8: HSTS Probe

```python
def probe_hsts(response_headers: dict) -> bool:
    """Return True if Strict-Transport-Security header is missing (a crypto weakness)."""
    hsts = response_headers.get("strict-transport-security", "")
    return not bool(hsts)  # True = missing HSTS = finding
```

### Pattern 9: Evidence Counter Integration

```python
# Source: quirk/intelligence/evidence.py — follow Phase 94/95 pattern
# Add "REST_FUZZ" to _PROTOCOL_KEYS tuple in evidence.py:
_PROTOCOL_KEYS = (
    ...,
    "REST_FUZZ",  # Phase 96 FUZZ-01 — active REST crypto-posture fuzz findings
)

# In build_evidence_summary() loop:
elif proto == "REST_FUZZ":
    # Each endpoint represents one fuzz finding; severity carries CRITICAL/HIGH
    sev = str(getattr(ep, "severity", "") or "").upper()
    if sev in ("CRITICAL", "HIGH"):
        fuzz_finding_count += 1
```

### Pattern 10: SCORE_WEIGHTS Update (303.0 / 41)

```python
# Add ONE new key to SCORE_WEIGHTS dict in quirk/intelligence/scoring.py:
"agility_fuzz_crypto_posture_ratio": 4.0,  # Phase 96 FUZZ-01 — active fuzz findings

# Update test_score_weights_invariant.py:
# sum: 299.0 → 303.0 (+4.0)
# count: 40 → 41 (+1)
```

**MUST update BOTH invariant test assertions together** (recurring lesson from v5.0/v5.1).

### Anti-Patterns to Avoid

- **Sending any request before the gate returns True:** The non-TTY abort MUST fire before the first `session.request()` call. Tests must mock the session and assert `call_count == 0`.
- **Using `maybe_confirm_probe_budget` for the fuzz gate:** The semantics differ (auto-proceed vs. hard abort in non-TTY). A new `confirm_fuzz_gate()` function is required.
- **Budget bypass via config:** The hard ceiling (500) must be enforced inside the fuzzer, not relying on CLI argument validation alone. Config-layer checks can be bypassed; the internal check cannot.
- **hypothesis direct use:** Do not call `hypothesis.given()` or `@settings()` directly. Use `operation.as_strategy().example()` — schemathesis handles hypothesis internals.
- **`as_requests_kwargs`:** This method does NOT exist in schemathesis 4.4.4. The correct method is `case.as_transport_kwargs(base_url=...)`.
- **`is_ok()` method on result:** In schemathesis 4.4.4, the result from `get_all_operations()` is `schemathesis.core.result.Ok` or `Err`. Use `isinstance(result, Ok)` not `result.is_ok()`.
- **Protocol casing:** Protocol key is `"REST_FUZZ"` (UPPERCASE) per project convention (`_PROTOCOL_KEYS` pattern). Never `"rest_fuzz"` or `"Rest-Fuzz"`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OpenAPI spec → HTTP request generation | Custom path parser + request builder | `schemathesis.openapi.from_dict()` + `case.as_transport_kwargs()` | schemathesis handles path parameters, query serialization, content negotiation, OpenAPI 2/3 quirks |
| Token-bucket rate limiting | Time-sleep loop | `quirk.engine.rate_limiter.TokenBucket` | Thread-safe, correct burst semantics, already tested |
| URL scope / SSRF guard | Domain-name substring check | `quirk.util.url_allowlist.validate_external_url` | Handles IPv4, IPv6, link-local, cloud metadata, scheme validation |
| JWT HS256 signing | Raw HMAC-SHA256 + base64 encode | `jwt.encode(..., algorithm='HS256')` (PyJWT) | Correct JWT header structure, consistent with existing token work |
| RSA public key serialization | Raw ASN.1 | `cryptography.hazmat.primitives.serialization.Encoding.PEM` | Already a core dep; used in chaos lab jwt/rs256/main.py |

**Key insight:** The schemathesis `Case` object handles all request serialization complexity. Do not try to enumerate paths directly from the `spec_dict` — use the iterator.

---

## Common Pitfalls

### Pitfall 1: Non-TTY Abort Must Fire Before ANY Network I/O

**What goes wrong:** The gate check is placed after some setup that makes a DNS lookup or socket open.
**Why it happens:** Developer puts the gate check after "benign" HTTP calls (e.g., fetching the spec URL, checking the target health). Those ARE network requests.
**How to avoid:** `confirm_fuzz_gate()` must be the first call in `run_fuzz_scan()`, before the schemathesis schema load (which, for `from_dict`, is safe — no network) and before any probe setup that touches sockets.
**Warning signs:** Test asserting zero requests fails if the mock is on `requests.Session.request` but the probe opens a raw `socket.create_connection` — mock both.

### Pitfall 2: schemathesis Pulls pytest and hypothesis into Runtime

**What goes wrong:** `import schemathesis` loads `schemathesis.pytest` (a thin shim) and `hypothesis` at module level. Developers may fear this taints production runtime.
**Why it matters:** This is acceptable — `_pytest` itself (the full test framework) is NOT loaded. Only `schemathesis.pytest.loaders` (an integration shim) imports. The actual `pytest` package IS a declared schemathesis runtime dependency (not dev-only), and hypothesis is required for `strategy.example()`. Both will be present after `pip install -e .[api]`.
**How to avoid:** Do not add a guard like `if not os.environ.get('PYTEST_CURRENT_TEST')` — just import schemathesis normally. The optional-dep import pattern used elsewhere in QUIRK is not needed here since schemathesis is always present when `[api]` is installed.
**Warning signs:** If `import schemathesis` fails at runtime, `[api]` extras were not installed — the CLI should emit a `missing_extra` advisory (follow the `is_extra_available` pattern from run_scan.py).

### Pitfall 3: Budget Counter Must Count Dispatched Requests, Not Generated Cases

**What goes wrong:** Incrementing the budget counter on `case = strategy.example()` generation rather than on `session.request()` dispatch. A case may be generated but skipped by the scope gate.
**Why it happens:** Logical placement error.
**How to avoid:** Increment `budget_used` only after `session.request(**kwargs)` succeeds (i.e., a real HTTP call was made). The scope-gate rejection does NOT consume budget.

### Pitfall 4: SCORE_WEIGHTS Sum and Count Must Both Be Updated

**What goes wrong:** Updating only the sum assertion in `test_score_weights_invariant.py` and missing the count assertion.
**Why it happens:** The two assertions are in separate test functions in the same file.
**How to avoid:** Always edit both `test_score_weights_sum_invariant` (299.0 → 303.0) AND `test_score_weights_count_invariant` (40 → 41) in the same commit. CI will catch a missed one but the failing test output is confusing.

### Pitfall 5: Chaos Lab Triple Update (lab.sh + compose + README + expected_results)

**What goes wrong:** Adding the `fuzz-target` service to `docker-compose.yml` but forgetting to update `expected_results_v4.md` or the `README.md`.
**Why it happens:** `lab.sh` uses `_derive_all_profiles` dynamically (yq/grep parse of compose file), so `lab.sh` does NOT need a hardcoded `ALL_PROFILES` list update. But the oracle files DO need manual updates.
**How to avoid:** Per CLAUDE.md Chaos Lab Maintenance rule: compose profile change → README + expected_results in the SAME change. Verification: `./lab.sh profiles` should list `fuzz-target`.
**Warning signs:** CI diff shows compose modified but expected_results_v4.md untouched.

### Pitfall 6: alg-Confusion Probe Requires Public Key Extraction

**What goes wrong:** The probe assumes the public key is always available as a JWKS endpoint or embedded in the token.
**Why it happens:** The RS256 jwt-rs256 chaos service exposes `/.well-known/jwks.json` — but a real target may not.
**How to avoid:** If the public key cannot be extracted (no JWKS, no `x5c`, no `jwk` header), emit a `probe_skipped` finding (severity INFO) rather than failing. The probe is best-effort.

### Pitfall 7: TLS Downgrade Probe DeprecationWarning in Python 3.12+

**What goes wrong:** `ssl.TLSVersion.TLSv1` emits a DeprecationWarning that clutters test output or causes warning-as-error CI failures.
**Why it happens:** Python 3.12 deprecated these constants.
**How to avoid:** Wrap with `import warnings; with warnings.catch_warnings(): warnings.simplefilter("ignore", DeprecationWarning)` inside the probe function, or use `pytest.warns` in tests. The warning is expected behavior — the probe SHOULD try the deprecated version.

---

## Code Examples

### Full Verified Programmatic Dispatch Pattern

```python
# Source: live schemathesis 4.4.4 API test (2026-05-23)
import schemathesis
from schemathesis.core.result import Ok
import requests

def run_fuzz_scan(spec_dict: dict, base_url: str, budget: int = 50) -> list:
    """Minimal verified dispatch loop (safety gates omitted for clarity)."""
    schema = schemathesis.openapi.from_dict(spec_dict)
    get_schema = schema.include(method="GET")   # FUZZ-02 guardrail 1

    results = []
    budget_used = 0
    session = requests.Session()

    for result in get_schema.get_all_operations():
        if budget_used >= budget:
            break
        if not isinstance(result, Ok):
            continue

        op = result.ok()
        case = op.as_strategy().example()
        kwargs = case.as_transport_kwargs(base_url=base_url)
        # kwargs shape confirmed: {'method', 'url', 'headers', 'cookies', 'params'}
        # Add timeout, verify=True, then dispatch:
        kwargs.setdefault("timeout", 10)
        response = session.request(**kwargs)
        budget_used += 1
        results.append(response)

    return results
```

### Confirmed as_transport_kwargs Output (live test)

```
kwargs = {
  'method': 'GET',
  'url': 'http://localhost:8080/ping',
  'cookies': {},
  'headers': {
    'User-Agent': 'schemathesis/4.4.4',
    'Accept-Encoding': 'gzip, deflate, zstd',
    'Accept': '*/*',
    'Connection': 'keep-alive',
    'X-Schemathesis-TestCaseId': 'tuu5NP'
  },
  'params': {}
}
```

### Chaos Lab fuzz-target Service Skeleton

```python
# fuzz-target/main.py — deliberately weak for probe validation
from fastapi import FastAPI, Header
from typing import Optional
import jwt, datetime

app = FastAPI()

# Deliberately missing HSTS header, accepts TLS 1.0 (nginx-level)
@app.get("/openapi.json")
def openapi_spec():
    # Return a minimal OpenAPI spec for schemathesis to consume
    return {
        "openapi": "3.0.0",
        "info": {"title": "Fuzz Target", "version": "1.0.0"},
        "servers": [{"url": "http://fuzz-target:8000"}],
        "paths": {
            "/probe": {"get": {"responses": {"200": {"description": "OK"}}}}
        }
    }

@app.get("/probe")
def probe(authorization: Optional[str] = Header(None)):
    """Accepts both valid and forged JWT tokens — simulates alg-confusion vulnerability."""
    # NOTE: deliberately does NOT verify signature algorithm properly
    return {"status": "accepted"}
```

---

## Runtime State Inventory

> Phase 96 is not a rename/refactor phase.

None — this is a greenfield feature addition. No stored data, live service config, OS-registered state, secrets, or build artifacts require migration.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `result.is_ok()` | `isinstance(result, Ok)` | schemathesis 4.x | is_ok() does not exist; use isinstance check |
| `case.as_requests_kwargs()` | `case.as_transport_kwargs()` | schemathesis 3→4 | Method name changed; returns same shape dict |
| schemathesis Engine.execute() | `schema.get_all_operations()` + `strategy.example()` | schemathesis 4.x | Engine is for full pytest runs; programmatic use prefers direct iteration |

**Deprecated/outdated:**
- `schemathesis.from_path()` (top-level): moved to `schemathesis.openapi.from_path()` in 4.x. [ASSUMED — based on wheel inspection; top-level alias may still work]
- `case.call()`: Still exists and works, but fires hook machinery (before_call/after_call hooks). For QUIRK's isolated probe use, `as_transport_kwargs()` + `requests.Session.request()` gives cleaner control.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Port 20100 is available for the fuzz-target compose service | Chaos Lab | Port collision with unlisted local service; pick next free port |
| A2 | The `fuzz-target` chaos service can be a plain FastAPI container (no TLS-level config required for the fuzz probes — TLS probes are done at the socket level by the scanner, not the HTTP dispatch) | Architecture | If TLS probes need a live TLS endpoint, the fuzz-target needs nginx TLS termination |
| A3 | `schemathesis.openapi.from_path()` top-level alias still works in 4.4.4 | State of the Art | Minor — `from_dict` is the correct path for QUIRK since Phase 94 already parses the spec |
| A4 | `agility_fuzz_crypto_posture_ratio` at weight 4.0 is an appropriate score signal name and weight split | SCORE_WEIGHTS | At Claude's discretion per CONTEXT; wrong name would fail the invariant test |

**If this table is empty:** Not empty — four low-risk assumptions listed above. None block planning.

---

## Open Questions

1. **Public key extraction for alg-confusion probe**
   - What we know: The chaos lab `jwt-rs256` service exposes `/.well-known/jwks.json` with the RSA public key. Real targets may not.
   - What's unclear: Should the probe skip gracefully (INFO finding) when no public key is discoverable, or should it attempt to fetch the JWKS URL from the JWT `iss` or `jku` header claim?
   - Recommendation: Graceful skip with INFO finding. Fetching `jku` is a separate SSRF risk; not worth it for a probe.

2. **HTTP-only credential transmission probe scope**
   - What we know: The probe should send the bearer token or API key over an `http://` URL variant of the same endpoint.
   - What's unclear: Should QUIRK actually construct an `http://` URL by stripping the `s` from `https://`, or only probe endpoints already declared as `http://` in the OpenAPI spec?
   - Recommendation: Probe only endpoints already declared as `http://` in the spec (Phase 94 already identifies these); do not silently downgrade HTTPS URLs.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| schemathesis | FUZZ-01 dispatch | ✗ (not in .venv) | 4.4.4 on PyPI | Wave 0 installs via `pip install -e ".[api]"` |
| hypothesis | schemathesis transitive | ✗ (not in .venv) | 6.108+ | Installed with schemathesis |
| requests | HTTP dispatch | ✓ | 2.33.1 | — |
| httpx | TLS probes | ✓ | 0.28.1 | — |
| PyJWT | Alg-confusion forge | ✓ | 2.12.1 | — |
| cryptography | RSA key serialization | ✓ | >=44.0 | — |
| Docker | Chaos lab fuzz-target | ✓ | (system) | — |

**Missing dependencies with no fallback:**
- schemathesis + hypothesis (install via Wave 0 `pip install -e ".[api]"`)

**Missing dependencies with fallback:**
- None

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pytest.ini` (root) |
| Quick run command | `.venv/bin/pytest tests/test_rest_fuzzer_gate.py -x -q` |
| Full suite command | `.venv/bin/pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FUZZ-01 | schemathesis case generation + dispatch | unit | `pytest tests/test_rest_fuzzer_probes.py::test_dispatch_integration -x` | Wave 0 |
| FUZZ-02 | Budget ceiling enforcement | unit | `pytest tests/test_rest_fuzzer_gate.py::test_budget_hard_ceiling -x` | Wave 0 |
| FUZZ-02 | Rate cap via TokenBucket | unit | `pytest tests/test_rest_fuzzer_gate.py::test_rate_limiter_invoked -x` | Wave 0 |
| FUZZ-02 | Scope gate rejects out-of-scope URL | unit | `pytest tests/test_rest_fuzzer_gate.py::test_scope_gate_rejects -x` | Wave 0 |
| FUZZ-03 | Non-TTY hard abort — zero requests | unit | `pytest tests/test_rest_fuzzer_gate.py::test_non_tty_hard_abort -x` | Wave 0 (HIGHEST PRIORITY) |
| FUZZ-03 | TTY CONFIRM gate — non-CONFIRM input aborts | unit | `pytest tests/test_rest_fuzzer_gate.py::test_confirm_required -x` | Wave 0 |
| FUZZ-04 | HS256 token forge accepted by server → CRITICAL finding | unit | `pytest tests/test_rest_fuzzer_probes.py::test_alg_confusion_forge -x` | Wave 2 |
| SCORE-01 | SCORE_WEIGHTS sum = 303.0 | unit | `pytest tests/test_score_weights_invariant.py -x` | ✅ (update) |
| SCORE-01 | SCORE_WEIGHTS count = 41 | unit | `pytest tests/test_score_weights_invariant.py -x` | ✅ (update) |
| LAB-01 | fuzz-target profile appears in `./lab.sh profiles` | smoke (manual) | `./lab.sh profiles \| grep fuzz-target` | Wave 3 |

### Sampling Rate

- **Per task commit:** `.venv/bin/pytest tests/test_rest_fuzzer_gate.py tests/test_rest_fuzzer_probes.py -x -q`
- **Per wave merge:** `.venv/bin/pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_rest_fuzzer_gate.py` — covers FUZZ-02 + FUZZ-03 (gates, budget, rate, scope)
- [ ] `tests/test_rest_fuzzer_probes.py` — covers FUZZ-01 dispatch integration + FUZZ-04 alg-confusion
- [ ] `quirk/scanner/rest_fuzzer.py` — module stub (gate functions must exist for test imports)
- [ ] `pip install -e ".[api]"` in `.venv` — installs schemathesis + hypothesis

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | yes | CONFIRM gate + non-TTY hard abort; operator must explicitly authorize each fuzz run |
| V5 Input Validation | yes | validate_external_url (SSRF gate per request URL) |
| V6 Cryptography | yes | TLS/cipher/HSTS probes are the output deliverable; no hand-rolled crypto |

### Known Threat Patterns for REST Fuzzer Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSRF via fuzz target URL | Spoofing | `validate_external_url` per-request; blocks internal IPs, cloud metadata |
| Credential leakage in fuzz findings | Information Disclosure | Phase 93 `safe_str()` scrubbing; no bearer token in finding records |
| Accidental headless fuzzing in CI | Tampering | `is_tty=False` hard abort before any request; test-verified |
| Budget exhaustion / runaway requests | Denial of Service | Hard ceiling `MAX_FUZZ_BUDGET = 500` enforced inside the fuzzer loop |
| alg-confusion HMAC secret disclosure | Information Disclosure | Public key bytes used as HMAC secret are public; no leakage risk |

---

## Sources

### Primary (HIGH confidence)

- schemathesis 4.4.4 wheel (`schemathesis-4.4.4-py3-none-any.whl`) — direct source inspection of `generation/case.py`, `transport/requests.py`, `openapi/loaders.py`, `schemas.py` [VERIFIED: PyPI registry + slopcheck]
- Live API test (2026-05-23): `schemathesis.openapi.from_dict()` + `include(method='GET')` + `get_all_operations()` + `case.as_transport_kwargs()` all confirmed working with exact output shape documented
- `quirk/engine/rate_limiter.py` — TokenBucket implementation (in-codebase) [VERIFIED: codebase]
- `quirk/util/targets.py:maybe_confirm_probe_budget` — nmap gate pattern (in-codebase) [VERIFIED: codebase]
- `quirk/util/url_allowlist.py:validate_external_url` — scope gate (in-codebase) [VERIFIED: codebase]
- `quirk/intelligence/scoring.py:SCORE_WEIGHTS` — current state sum=299.0, count=40 [VERIFIED: codebase]
- `tests/test_score_weights_invariant.py` — invariant test structure [VERIFIED: codebase]
- `quantum-chaos-enterprise-lab/lab.sh:_derive_all_profiles` — dynamic profile discovery [VERIFIED: codebase]

### Secondary (MEDIUM confidence)

- [schemathesis Python API reference](https://schemathesis.readthedocs.io/en/stable/reference/python/) — confirmed `Case.call()`, `schema.include(method=...)`, `schema.get_all_operations()` [CITED: readthedocs.io]

### Tertiary (LOW confidence)

- None

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — schemathesis API live-verified; all other deps confirmed in venv
- Architecture: HIGH — all integration points confirmed in codebase; no new patterns introduced
- Pitfalls: HIGH — derived from actual codebase inspection + schemathesis source reading + live API test
- Chaos lab: HIGH — lab.sh dynamic profile behavior confirmed by source inspection

**Research date:** 2026-05-23
**Valid until:** 2026-06-22 (schemathesis moves fast; re-verify API if > 30 days)
