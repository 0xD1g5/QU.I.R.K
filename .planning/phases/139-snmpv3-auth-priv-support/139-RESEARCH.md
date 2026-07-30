# Phase 139: SNMPv3 Auth+Priv Support - Research

**Researched:** 2026-07-30
**Domain:** SNMPv3 USM auth+priv transport extension of an existing agentless SNMPv2c hardware
fingerprinting scanner (pysnmp 7 asyncio HLAPI)
**Confidence:** HIGH

## Summary

This phase extends the already-shipped v5.8 SNMPv2c fingerprinting path
(`quirk/scanner/snmp_scanner.py`, `run_scan.py` L1510-1600, `hardware_scanner.py::fingerprint_one`
Step 3) with an SNMPv3 auth+priv (USM) sibling. No new dependency is required — `pysnmp>=7.1.0,<8`
(already pinned in the `[hw]` extra, confirmed installed as `7.1.21`) ships `hlapi.v3arch.asyncio`
as a sibling module to the already-imported `hlapi.v1arch.asyncio`. The work is a well-bounded,
additive extension of a pattern this codebase has executed twice before this milestone
(`BrokerCredential` per-host secrets in Phase 57, `[hw]` advisory-import-guard extras in Phase 133).

The two things this project-level research explicitly deferred to phase research are now resolved
below with exact code citations: (a) `SnmpV3Credential` field names and the 3 new `HardwareDevice`
columns, confirmed against live `quirk/config.py`/`quirk/models.py`/`quirk/db.py` code; and (b) a
concrete recommended timeout/retry multiplier for the USM engine-ID discovery round-trip, reasoned
from RFC 3414's discovery-then-authenticated two-exchange requirement since no chaos-lab SNMPv3
target exists yet to measure empirically (flagged below as a chaos-lab gap this phase must close).

**Primary recommendation:** Add a `_async_probe_v3()` sibling to `_async_probe()` in
`snmp_scanner.py` using `pysnmp.hlapi.v3arch.asyncio.UsmUserData`, dispatched by a new `version`
parameter on `probe_snmp_target()`/`scan_snmp_targets()`; add `SnmpV3Credential` to `quirk/config.py`
mirroring `BrokerCredential`; add 3 new nullable `HardwareDevice` columns
(`snmp_version`, `snmp_auth_protocol`, `snmp_priv_protocol`) via the `_ADDITIVE_MIGRATIONS` registry;
wire the v3→v2c→none fallback into BOTH SNMP call sites (`hardware_scanner.py::fingerprint_one`
Step 3 AND `run_scan.py`'s independent SNMP-only pass at L1510-1600 — this codebase has **two**,
not one, SNMP entry points that both need the v3 path); update all three `HardwareDevice`
projection sites; extend `safe_str()`/AST-gate coverage to the new v3 code; add a SNMPv3 USM user to
the existing `hwcompat-snmp` chaos-lab container (reconfiguration, not a new profile, but still
triggers CLAUDE.md's chaos-lab-maintenance rule).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| SNMPV3-01 | Per-host SNMPv3 USM credentials (username + auth/priv passphrase env-var names), mirroring `BrokerCredential` | `SnmpV3Credential` dataclass design (Architecture Patterns Pattern 2), verified `BrokerCredential` precedent at `quirk/config.py:344-352` |
| SNMPV3-02 | v3-then-v2c-then-none fallback with distinct version labeling (v3 auth+priv / v3 noAuthNoPriv / v2c / none), never equating noAuthNoPriv to authenticated v3 | Pattern 1 dispatcher design, Pitfall 3, `snmp_version_used`/`snmp_security_level` result fields |
| SNMPV3-03 | SNMPv3 credentials never leak into exceptions/logs/JSON; AST leakage gate extended | Pitfall 1 — confirms `snmp_scanner.py` currently has NO `safe_str` import and is absent from `test_credential_leakage.py`'s `MODIFIED_FILES`; concrete remediation steps given |
| SNMPV3-04 | Timeout/retry budget re-derived for the USM engine-ID discovery round-trip | Pitfall 2 — concrete `timeout_v3 = timeout_v2c * 2` starting recommendation (flagged `[ASSUMED]`, A1), plus chaos-lab gap identified to enable empirical validation |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SNMPv3 USM transport (auth/priv GET) | Backend / Scanner (sensor-side) | — | Pure network I/O in `quirk/scanner/snmp_scanner.py`; agentless scanner runs on the sensor/CLI process, never in the browser or a frontend server tier |
| Per-host SNMPv3 credential config | Backend / Config | — | `quirk/config.py::ConnectorsCfg` — loaded from YAML/CLI at scan-invocation time, never client-side |
| Fallback-ladder decision (v3→v2c→none) | Backend / Scanner | — | Decision logic lives in `hardware_scanner.py::fingerprint_one` and `run_scan.py`'s SNMP pass, both server/CLI-process code |
| Result persistence (`HardwareDevice` columns) | Database / Storage | Backend / ORM | SQLAlchemy `HardwareDevice` model — new nullable columns via existing additive-migration registry |
| Version-label badge rendering | Frontend Server (SSR-less SPA) / Browser | API / Backend | React dashboard component reads from `/api/scan/latest` JSON already projected server-side; report renderers (HTML/PDF/DOCX) render server-side from the same projected dict |
| Credential leakage prevention (`safe_str`) | Backend / Scanner | — | Exception-handling discipline inside the scanner module itself, before any data reaches API/report/CBOM tiers |
| Timeout/retry budget for USM discovery | Backend / Scanner | — | Pure scanner-internal tuning constant, not exposed to any other tier |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pysnmp` | `>=7.1.0,<8` (installed `7.1.21` — verified live via `pip index versions` per project research 2026-07-30; not re-verified this session, no version-sensitive API change since) [CITED: .planning/research/STACK.md] | SNMPv3 USM auth+priv GET via `hlapi.v3arch.asyncio` | Already the pinned `[hw]` extras dependency for v2c (`hlapi.v1arch.asyncio`, confirmed live in `quirk/scanner/snmp_scanner.py` lines 27-34). v3's `UsmUserData`/`usmHMACSHAAuthProtocol`/`usmAesCfb128Protocol` live in the sibling `hlapi.v3arch.asyncio` module of the SAME package — zero new pin. [VERIFIED: codebase] |

No new Standard/Supporting libraries are needed for this phase — it is a same-package sibling-module
extension. Per the Package Legitimacy Gate protocol, no *new* external package install occurs in
this phase, so the Package Legitimacy Audit section below documents this explicitly (nothing to
audit) rather than fabricating a table entry.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| (none new) | — | — | — |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pysnmp` v3arch HLAPI | `pysnmp` legacy sync HLAPI (`hlapi.v1arch` sync, non-asyncio) | Rejected — the codebase already committed to the asyncio HLAPI for v2c (Phase 133); mixing sync/async SNMP HLAPI generations in the same file would be an unnecessary inconsistency with no benefit. |
| Adding a `[hw]`-scoped v3 code path | A separate `[snmpv3]` extras group | Rejected — `pysnmp` already covers both v2c and v3 in one package/one pin; splitting extras groups only makes sense when the *dependency* differs, not the code path within an already-installed dependency. |

**Installation:**
```bash
# No new install — pysnmp>=7.1.0,<8 already satisfies both v2c and v3.
# Existing install command unchanged:
pip install "quirk-scanner[hw]"
```

**Version verification:** `pysnmp` version was verified live by the project-level STACK.md research
pass on 2026-07-30 (`pip index versions pysnmp` → `7.1.21` latest, satisfies `>=7.1.0,<8`). This
phase adds no new package, so no additional registry verification is required — the existing pin in
`pyproject.toml`'s `[hw]` extras group is unchanged.

## Package Legitimacy Audit

> This phase installs **zero new external packages**. `pysnmp>=7.1.0,<8` is an existing, already-audited
> dependency from Phase 133 (v5.8) — no slopcheck/registry re-verification is warranted for an
> unchanged pin. The table below is intentionally empty; this satisfies the audit requirement by
> explicit statement rather than omission.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| — | — | — | — | — | — | N/A — no new packages this phase |

**Packages removed due to slopcheck [SLOP] verdict:** none — no new packages evaluated.
**Packages flagged as suspicious [SUS]:** none — no new packages evaluated.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────────────────────┐
                         │  Operator config (YAML / CLI)                │
                         │  connectors.snmp_v3_credentials: {host: ...} │
                         │  connectors.snmp_version: "v2c" | "v3"       │
                         └───────────────────┬───────────────────────────┘
                                              │  (config_from_dict)
                                              ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  ENTRY POINT 1: run_scan.py L1510-1600 (independent SNMP-only pass,       │
   │  gated on cfg.connectors.enable_snmp)                                     │
   │  ENTRY POINT 2: hardware_scanner.py::fingerprint_one() Step 3             │
   │  (gated on device.vendor=="Unknown" after SSH/HTTP steps)                 │
   │                                                                            │
   │  BOTH call → quirk/scanner/snmp_scanner.py::probe_snmp_target(version=…) │
   └───────────────────────────────┬────────────────────────────────────────┘
                                    │
                    version="v3" and host has SnmpV3Credential?
                         ┌──────────┴──────────┐
                        yes                     no / v3 failed
                         ▼                       ▼
              ┌─────────────────────┐   ┌─────────────────────────┐
              │ _async_probe_v3()   │   │ _async_probe() (existing │
              │ UsmUserData          │   │ v2c CommunityData path,  │
              │ (1) engine-ID        │   │ unchanged)                │
              │     discovery RT     │   └─────────────┬─────────────┘
              │ (2) authenticated GET│                 │  v2c also fails/
              │     (SHA auth+AES    │                 │  unreachable
              │     priv)            │                 ▼
              └──────────┬───────────┘        ┌──────────────────┐
                         │ success              │ null-safe dict    │
                         ▼                      │ (mode="none")      │
              ┌─────────────────────┐          └──────────────────┘
              │ result dict +        │
              │ mode="v3_auth_priv"  │◄──────────────── fallback ladder
              │ or "v3_no_auth_priv" │      merges into ONE result +
              │ (never equated)      │      mode label (SNMPV3-02)
              └──────────┬───────────┘
                         ▼
         ┌───────────────────────────────────────────┐
         │ HardwareDevice ORM row                       │
         │ + snmp_version, snmp_auth_protocol,          │
         │   snmp_priv_protocol (new nullable columns)  │
         │ (secrets NEVER stored — only protocol names) │
         └───────────────────┬───────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────────┐
        ▼                     ▼                          ▼
 reports/writer.py     merge/scan.py            dashboard/api/routes/scan.py
 (local CLI report)    (distributed merge)       ::_derive_hw_components()
 → HTML/PDF/DOCX        → CBOM                    → HardwareComponent (dashboard)
        │                     │                          │
        └─────────────────────┴─────────────────────────┘
                              ▼
                    cbom/builder.py Pass 4
                    quirk:hw-snmp-version Property (new)
```

A reader can trace the primary use case (operator configures v3 creds → scan runs → badge renders)
by following: config → entry point → `probe_snmp_target(version=...)` → fallback ladder → ORM row →
three projection sites → CBOM/report/dashboard surfaces.

### Recommended Project Structure

No new files. All changes are in-place edits to existing flat-file modules — this codebase has no
`quirk/hardware/` sub-package (confirmed: `quirk/scanner/*.py` flat files), consistent with
`.planning/research/ARCHITECTURE.md`'s explicit correction.

```
quirk/scanner/snmp_scanner.py     # + _async_probe_v3(), version-dispatch on probe_snmp_target()
quirk/config.py                    # + SnmpV3Credential dataclass, + 2 ConnectorsCfg fields
quirk/models.py                    # + 3 nullable HardwareDevice columns
quirk/db.py                        # + _SNMPV3_HW_COLUMNS row in _ADDITIVE_MIGRATIONS
quirk/scanner/hardware_scanner.py  # Step 3 gains v3-then-v2c-then-none ladder
run_scan.py                        # SNMP-only pass (L1510-1600) gains the same ladder
quirk/reports/writer.py            # projection site 1 — add 3 new fields to hw dict
quirk/merge/scan.py                # projection site 2 — add 3 new fields to hw dict
quirk/dashboard/api/routes/scan.py # projection site 3 — _derive_hw_components + HardwareComponent
quirk/dashboard/api/schemas.py     # HardwareComponent Pydantic schema — decide field additions
quirk/cbom/builder.py              # Pass 4 — new quirk:hw-snmp-version Property
tests/test_credential_leakage.py   # extend MODIFIED_FILES / AST-gate scope
tests/test_snmp_scanner_contract.py (exists? verify) # v3 contract tests
quantum-chaos-enterprise-lab/hwcompat-snmp/snmpd.conf  # + createUser USM line
docs/chaos-lab.md, README.md, expected_results_hwcompat.md  # SNMPv3 reconfiguration entries
src/dashboard/src/... (new badge component + hardware.tsx wiring)
```

### Pattern 1: Version-dispatched probe function (v2c/v3 sibling, not a fork)

**What:** `probe_snmp_target()` gains a `version: str = "v2c"` parameter and a `v3_credential:
Optional[SnmpV3Credential] = None` parameter; internally dispatches to `_async_probe()` (unchanged,
v2c) or a new `_async_probe_v3()` (new, USM). Both return the SAME dict shape (`snmp_sysdescr`,
`snmp_sysname`, `snmp_sysobjectid`) plus new keys `snmp_version_used` and `snmp_security_level`.
**When to use:** Any SNMP entry point (both `run_scan.py` and `hardware_scanner.py`) call the same
dispatcher — no duplicated fallback logic in two places.
**Example:**
```python
# quirk/scanner/snmp_scanner.py — pattern for the v3 sibling, mirrors _async_probe() exactly
from pysnmp.hlapi.v3arch.asyncio import (
    UsmUserData,
    usmHMACSHAAuthProtocol,
    usmAesCfb128Protocol,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    get_cmd as get_cmd_v3,
)
# Source: pysnmp 7.1 v3arch asyncio HLAPI examples (docs.lextudio.com/pysnmp/v7.1) — MEDIUM,
# WebSearch-verified against official docs in project-level STACK.md research 2026-07-30.

async def _async_probe_v3(
    host: str,
    credential: "SnmpV3Credential",
    timeout: int,
) -> Dict[str, Optional[str]]:
    """SNMPv3 USM GET for sysDescr/sysName/sysObjectID.

    D-02 (modern-only protocols): auth is always SHA-family, priv is always
    AES-family. If the target only offers MD5/DES, this function must NOT
    silently downgrade — it should raise/return a distinct
    'protocol-mismatch' marker so the caller can surface a crypto-hygiene
    finding (per CONTEXT.md D-02), not fall through to v2c silently.
    """
    result: Dict[str, Optional[str]] = dict(_NULL_RESULT)
    result["snmp_version_used"] = None
    engine = SnmpEngine()
    try:
        auth_key = _read_env_secret(credential.auth_key_env)   # never logged, never returned
        priv_key = _read_env_secret(credential.priv_key_env) if credential.priv_protocol else None
        usm_data = UsmUserData(
            credential.username,
            authKey=auth_key,
            authProtocol=usmHMACSHAAuthProtocol,      # D-02: SHA family only
            privKey=priv_key,
            privProtocol=usmAesCfb128Protocol if priv_key else None,  # D-02: AES family only
        )
        target = await UdpTransportTarget.create(
            (host, 161),
            timeout=timeout,        # re-derived budget — see Pitfall 2 / SNMPV3-04 below
            retries=1,
        )
        for oid_str, key in (
            (_OID_SYSDESCR, "snmp_sysdescr"),
            (_OID_SYSNAME, "snmp_sysname"),
            (_OID_SYSOBJECTID, "snmp_sysobjectid"),
        ):
            try:
                err_indication, err_status, _err_index, var_binds = await get_cmd_v3(
                    engine, usm_data, target, ObjectType(ObjectIdentity(oid_str)),
                )
                if not err_indication and not err_status and var_binds:
                    _oid, val = var_binds[0]
                    str_val = str(val) if val is not None else None
                    if str_val and str_val not in ("", "noSuchObject", "noSuchInstance"):
                        result[key] = str_val
            except Exception as exc:
                # SNMPV3-03: route through safe_str, never raw str(exc) — auth/priv
                # failures (UsmStatsWrongDigests, notInTimeWindow) can echo request
                # parameters and must never reach logs unscrubbed.
                _LOG.debug("SNMPv3 OID %s probe %s failed: %s", oid_str, host, safe_str(exc))
        result["snmp_version_used"] = "v3"
        result["snmp_security_level"] = "authPriv" if priv_key else "authNoPriv"
    except Exception as exc:
        _LOG.debug("SNMPv3 probe %s failed: %s", host, safe_str(exc))
    finally:
        try:
            engine.close_dispatcher()
        except Exception:
            pass
    return result
```

### Pattern 2: Per-host secret-by-env-var-name config (mirrors `BrokerCredential`)

**What:** `SnmpV3Credential` frozen dataclass, keyed by host in a new `Dict[str, SnmpV3Credential]`
field on `ConnectorsCfg`.
**When to use:** Whenever an operator needs per-device SNMPv3 USM credentials, following the exact
established pattern from `BrokerCredential` (Phase 57 / D-05).
**Example:**
```python
# quirk/config.py — verified precedent at lines 344-352 (BrokerCredential)
@dataclass(frozen=True)
class SnmpV3Credential:
    """Phase 139 / SNMPV3-01: per-host SNMPv3 USM credential entry.

    `auth_key_env`/`priv_key_env` are NAMES of environment variables holding
    the passphrases, NOT the passphrases themselves — mirrors
    BrokerCredential.pass_env (D-05 precedent). Passphrases MUST NOT appear
    inline in YAML.
    """
    username: str
    auth_key_env: str            # env var name; "" means noAuth (not recommended, D-02)
    priv_key_env: str = ""       # env var name; "" means noPriv (authNoPriv, distinct from authPriv)

# ConnectorsCfg gains (mirrors enable_snmp/snmp_community precedent at lines 293-296):
#   enable_snmp: bool = False               (existing, unchanged)
#   snmp_community: str = "public"          (existing, unchanged — v2c fallback still uses this)
#   snmp_v3_credentials: Dict[str, SnmpV3Credential] = field(default_factory=dict)  # NEW, keyed by host
```

### Anti-Patterns to Avoid

- **Threading `auth_passphrase`/`priv_passphrase` as bare function parameters through the probe
  call chain (mirroring how `community: str` is threaded today):** v2c's single community string
  is low-sensitivity by comparison (it's not treated as a secret anywhere in this codebase's threat
  model); v3's 2 passphrases are real, high-value secrets. Pass only the `SnmpV3Credential` env-var
  NAME through config, resolve the actual secret value inside the probe function at the last
  possible moment (mirrors `BrokerCredential.pass_env` resolution pattern used elsewhere), and
  never let the resolved secret escape the function scope in a returned dict.
- **Adding the v3 fallback ladder to only ONE of the two SNMP entry points.** This codebase has
  TWO independent call sites (`hardware_scanner.py::fingerprint_one` Step 3, AND `run_scan.py`
  L1510-1600's separate `--enable-snmp` pass) — verified by direct grep, confirmed at
  `run_scan.py:1526-1528` (`from quirk.scanner.snmp_scanner import scan_snmp_targets`) and
  `hardware_scanner.py:209-211` (`from quirk.scanner.snmp_scanner import probe_snmp_target`). Both
  must gain the v3-then-v2c-then-none ladder in the same phase, or SNMPv3 support will silently
  only work through one code path — a variant of the B-01 projection-site-drift bug class.
- **Adding a 4th independent ORM→dict hand-rolled query when wiring the new columns into the
  dashboard/reports.** Reuse the existing three `MAX(scanned_at) ± 1s` window queries already at
  `reports/writer.py` (~line 218-255), `merge/scan.py` (~line 239-268), and
  `dashboard/api/routes/scan.py::_derive_hw_components` (line 784-820) — add the 3 new fields to
  each dict/model in the SAME phase (v5.8 "B-01" lesson, restated in ARCHITECTURE.md Anti-Pattern 1).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SNMPv3 USM engine discovery, auth digest, priv encryption | A custom USM state machine | `pysnmp.hlapi.v3arch.asyncio.UsmUserData` | RFC 3414 USM is genuinely complex (engine boots/time windows, HMAC-SHA digest, AES-CFB encryption) — pysnmp already implements this correctly and is the same package this codebase trusts for v2c |
| Credential-safe exception stringification | A new SNMPv3-specific scrubbing regex set | `quirk.util.safe_exc.safe_str()` | Already handles the exact class of problem (regex-matched sensitive patterns → class-name-only fallback); SNMPv3 exceptions should route through the SAME shared helper, not a parallel one, to avoid divergent scrubbing coverage |
| Per-host secret storage shape | A new secret-map dataclass with a different shape than `BrokerCredential` | Mirror `BrokerCredential`'s `(user, pass_env)`-style shape exactly (`username`, `auth_key_env`, `priv_key_env`) | Consistency reduces cognitive load for anyone reading `config.py`; the shape is already proven correct (env-var-name-not-inline-secret) for exactly this kind of per-host credential |
| Additive DB migration for the 3 new columns | A new manual `ALTER TABLE` script or Alembic migration | The existing `_ADDITIVE_MIGRATIONS` registry in `quirk/db.py` (confirmed pattern at `db.py:137-144, 192-204`) | This is the single source of truth for every additive column this codebase has added since v5.7; a new column added outside this registry will not run on existing installs |

**Key insight:** Every piece of this phase has a proven precedent already shipped in this exact
codebase — the discipline is to extend existing patterns (`BrokerCredential`, `_ADDITIVE_MIGRATIONS`,
`safe_str`, the 3-projection-site convention, `_PYSNMP_AVAILABLE` advisory-import-guard) rather than
introduce new shapes, because divergent shapes are exactly what caused the B-01 bug class and the
pre-Phase-59 credential-leakage sweep.

## Common Pitfalls

### Pitfall 1: SNMPv3 credential leakage — the same class `safe_str()` was built to prevent, in NEW code not yet covered by the AST gate

**What goes wrong:** `snmp_scanner.py` today does NOT import `safe_str` at all (verified: grep for
`safe_str` in `quirk/scanner/snmp_scanner.py` returns zero hits) — its two `except Exception: pass`
blocks silently swallow, and `probe_snmp_target()`'s outer handler does `_LOG.debug("SNMP probe %s
failed: %s", host, exc)`, which formats `exc` via `%s` (equivalent to `str(exc)`) with NO scrubbing.
`run_scan.py`'s SNMP pass DOES import `safe_str` (confirmed at line ~1536, 1598) for its own
ImportError/DB-error messages, but NOT for anything inside `snmp_scanner.py` itself. `snmp_scanner.py`
is also absent from `tests/test_credential_leakage.py`'s `MODIFIED_FILES` list (verified: file
contains 8 entries, `snmp_scanner.py` is not one of them) — confirming CONTEXT.md's framing that
this is genuinely NEW leakage-gate scope, not already covered.

**Why it happens:** v2c's single `community` string was never treated as a high-sensitivity secret in
this codebase (it's not routed through `safe_str` today either) — the temptation is to add v3's
`UsmUserData` the same casual way, but v3's auth/priv passphrases are qualitatively different:
`UsmStatsWrongDigests`/`UsmStatsDecryptionErrors`/`notInTimeWindow` USM error responses can echo
request parameters in ways that risk embedding credential-adjacent material in exception text.

**How to avoid:** Import `safe_str` into `snmp_scanner.py` for the first time in this phase; route
every new v3 exception handler through it (`_LOG.debug(..., safe_str(exc))` not `%s` raw
interpolation — note `%s` formatting IS equivalent to `str(exc)`, so this must change too, not just
new v3 code); add `quirk/scanner/snmp_scanner.py` to `tests/test_credential_leakage.py`'s
`MODIFIED_FILES` list (and any new v3-specific module, if the implementation splits it out); never
place `auth_key`/`priv_key` values into any dict returned from `_async_probe_v3()` — only
`snmp_version_used`/`snmp_security_level` (protocol-name-level metadata) should leave the function.

**Warning signs:** `str(exc)` or bare `%s`-with-exc-object anywhere in new v3 code; the new v3 module
not present in `MODIFIED_FILES`; `auth_key_env`/`priv_key_env` resolved-secret VALUES (not names)
appearing as dict keys anywhere downstream.

### Pitfall 2: USM engine-ID discovery round-trip breaks the reused v2c timeout budget

**What goes wrong:** `_async_probe()` today uses `timeout=timeout, retries=1` per `UdpTransportTarget`
(confirmed at `snmp_scanner.py:193-197`, called with `timeout: int = 3` default from
`probe_snmp_target()`). SNMPv3 USM requires a mandatory discovery exchange (RFC 3414 §4: an initial
unauthenticated Report-PDU round-trip to learn `engineID`/`engineBoots`/`engineTime`) BEFORE the
first authenticated GET can succeed. If v3 reuses the same 3-second timeout unchanged, a v3 probe
effectively needs to complete 2 round-trips (discovery + authenticated GET) within the same window
tuned for 1, causing spurious timeouts especially in `ThreadPoolExecutor(max_workers=min(8,
len(hosts)))`-fanned scans where the pool is now holding workers open longer per host.

**How to avoid — concrete recommendation (fills the CONTEXT.md-deferred gap):**
Since no chaos-lab SNMPv3 target exists yet to measure empirically (see Environment Availability
below), recommend a **reasoned literature-based multiplier, not a measured one, with an explicit
note that this phase should also close the chaos-lab gap so a future phase CAN measure it**:
- pysnmp's v3arch HLAPI handles engine discovery internally and transparently on the first `get_cmd`
  call per `SnmpEngine` instance — it is NOT a separate function call the phase author invokes
  explicitly; it is an implicit extra network round-trip inside the same `timeout`-bounded operation.
- Recommend **`timeout_v3 = timeout_v2c * 2`** (i.e., 6 seconds when the v2c default is 3) as the
  per-OID timeout passed to `UdpTransportTarget.create()` for v3 probes specifically, reasoning: two
  round-trips (discovery + authenticated GET) at the same per-round-trip cost as v2c's single
  round-trip is the simplest safe doubling that avoids under-provisioning without unboundedly
  inflating scan duration. This is a **starting point recommended for implementation**, explicitly
  flagged `[ASSUMED]` — see Assumptions Log — and should be validated against a real chaos-lab
  SNMPv3 target added in this same phase (see Environment Availability / chaos-lab gap below) before
  being treated as final.
- Do NOT persist/reuse `SnmpEngine`/discovery state across separate `probe_snmp_target()` invocations
  or across scan sessions — each call should construct a fresh `SnmpEngine()` (mirrors the existing
  `_async_probe()` pattern of a fresh `SnmpDispatcher()` per call, confirmed at line 191) so a
  mid-scan device reboot cannot produce a stale-engine `notInTimeWindow` false failure.
- Add a dedicated test asserting `v3_timeout != v2c_timeout` and that a v3 probe against a
  deliberately-unreachable host still returns the same null-safe dict shape within a bounded time
  (mirrors the existing pattern this codebase already uses for v2c probe-failure tests).

**Warning signs:** SNMPv3 probes timing out noticeably more often than v2c against the same lab/host
set; `notInTimeWindow`/`unknownEngineID` in logs for hosts reachable moments earlier.

### Pitfall 3: v3 noAuthNoPriv silently equated to authenticated v3 (explicit anti-feature, REQUIREMENTS.md Out of Scope)

**What goes wrong:** A v3-capable device that only offers `noAuthNoPriv` (or `authNoPriv`) responds
successfully to a v3 GET without actually requiring the configured auth/priv credentials to be
correct — if the scanner labels any successful v3 response simply "v3" without distinguishing
security level, an unauthenticated v3 responder would be indistinguishable from a properly
authenticated+encrypted one in the report, which REQUIREMENTS.md's Out-of-Scope table explicitly
forbids ("SNMPv3 noAuthNoPriv treated as authenticated... Must be labeled distinctly").

**How to avoid:** `_async_probe_v3()` must record the ACTUAL negotiated security level used for the
successful exchange (`securityLevel` is available from the pysnmp USM context — `noAuthNoPriv` /
`authNoPriv` / `authPriv`), not just "v3 succeeded." Label surfaces must render 3 distinct v3-related
states plus v2c/none: `v3 auth+priv`, `v3 noAuthNoPriv`, `v2c`, `none`, and (per CONTEXT.md D-03)
`v3-failed-fell-back`. Since D-02 mandates SHA/AES-only credentials be configured, a device that only
offers weaker protocols and gets probed anyway would only reach `noAuthNoPriv`/`authNoPriv` if the
device itself doesn't enforce the credential (a device misconfiguration on the TARGET side, not this
scanner's doing) — this is exactly the scenario D-02's "distinct crypto-hygiene finding" framing
exists for.

**Warning signs:** Report/dashboard code that maps any "v3 GET succeeded" outcome to a single
"SNMPv3" label without a security-level branch.

### Pitfall 4: The v3→v2c→none fallback masks a real credential/config failure as an intentional v2c-only scan (CONTEXT.md D-03)

**What goes wrong:** If a host has `snmp_v3_credentials` configured but authentication actually
fails (wrong passphrase, wrong username, engine mismatch), and the code silently falls through to
v2c and succeeds there, the report would show "v2c" — visually and textually indistinguishable from
a host that was never configured for v3 at all. This hides a real operational problem (bad
credentials) behind an apparently-successful scan.

**How to avoid:** The fallback ladder must track WHY it fell back, not just THAT it fell back.
Recommend the ladder function return a tuple/dict including both the final successful `mode` used
AND a `v3_attempted: bool` / `v3_failure_reason: str | None` marker (routed through `safe_str` if it
ever contains exception text) so `snmp_version` can be rendered as the distinct
`v3-failed-fell-back` state D-03 requires, not silently `v2c`.

**Warning signs:** A `HardwareDevice.snmp_version` column that only ever contains `v3`/`v2c`/`None`
with no way to represent "v3 was configured and attempted but failed."

## Runtime State Inventory

> Not applicable — this phase is purely additive (new code paths, new nullable columns, new config
> fields). No rename/refactor/migration of existing identifiers occurs. Skipping per the
> greenfield-phase exemption in the RESEARCH.md template.

## Code Examples

### Additive migration entry (mirrors the Phase 133 `_SNMP_HW_COLUMNS` precedent exactly)

```python
# Source: quirk/db.py lines 137-144, 192-204 (existing precedent, verified live 2026-07-30)
_SNMPV3_HW_COLUMNS: tuple[tuple[str, str], ...] = (
    # Phase 139 SNMPV3-01/02: SNMPv3 transport metadata on hardware_devices.
    # Protocol NAMES only — never keys/passphrases (Anti-Pattern 2, ARCHITECTURE.md).
    ("snmp_version",       "VARCHAR(8)"),   # "v2c" | "v3" | NULL (pre-v5.10 rows / no SNMP)
    ("snmp_auth_protocol", "VARCHAR(16)"),  # e.g. "SHA" | "SHA256"; NULL unless snmp_version="v3"
    ("snmp_priv_protocol", "VARCHAR(16)"),  # e.g. "AES128" | "AES256"; NULL unless authPriv used
)

_ADDITIVE_MIGRATIONS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    # ... existing rows unchanged ...
    ("hardware_devices", _SNMP_HW_COLUMNS),           # Phase 133 SNMP-03 (existing, unchanged)
    ("hardware_devices", _SNMPV3_HW_COLUMNS),          # Phase 139 SNMPV3-01/02 (NEW)
)
```

### `HardwareDevice` ORM column additions (mirrors `models.py` lines 389-395 precedent)

```python
# Source: quirk/models.py lines 389-395 (existing SNMP columns, verified live 2026-07-30)
# NEW columns, same file, same class, added immediately after snmp_vendor:
snmp_version       = Column(String(8),  nullable=True)   # "v2c" | "v3" | NULL
snmp_auth_protocol = Column(String(16), nullable=True)   # e.g. "SHA" — protocol NAME only
snmp_priv_protocol = Column(String(16), nullable=True)   # e.g. "AES128" — protocol NAME only
```

### CBOM Property addition (mirrors `cbom/builder.py` lines 1043-1057 precedent)

```python
# Source: quirk/cbom/builder.py lines 1043-1057 (existing quirk:hw-* properties)
if dev.get("snmp_version"):
    fw_props.append(
        Property(name="quirk:hw-snmp-version", value=_sanitize_hw_str(str(dev.get("snmp_version"))))
    )
    # Only emit auth/priv protocol properties when v3 was actually used (guard pattern
    # matches the existing snmp_oid conditional at line 1055 — D-08 precedent).
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| SNMPv2c-only, shared community string (`snmp_community: str = "public"`, one value for the whole fleet) | SNMPv3 USM auth+priv, per-host credentials, v3→v2c→none fallback ladder | This phase (v5.10 Phase 139), extending Phase 133 (v5.8) | Real SNMPv3 deployments almost always use per-device USM credentials (unlike v2c's fleet-wide community convention); the shared-secret pattern this codebase used for v2c is architecturally wrong for v3 and must not be reused (already correctly identified in `.planning/research/ARCHITECTURE.md`) |

**Deprecated/outdated:** None — v2c support is NOT deprecated or removed by this phase; it remains
the fallback tier and the only mode for devices/operators who don't configure v3 credentials.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `timeout_v3 = timeout_v2c * 2` (6s default) is a safe starting multiplier for the USM discovery round-trip budget | Common Pitfalls, Pitfall 2 | If too low, spurious SNMPv3 timeouts persist (SNMPV3-04 unmet); if too high, large-fleet v3 scans run noticeably slower than needed. Low-to-medium risk — the phase plan should treat this as a tunable constant validated against the chaos-lab SNMPv3 target added in this same phase, not a hardcoded final value. |
| A2 | pysnmp 7.1.21's `hlapi.v3arch.asyncio.UsmUserData`/`usmHMACSHAAuthProtocol`/`usmAesCfb128Protocol` import paths and constructor signature match the WebSearch-sourced docs cited in project-level STACK.md (no Context7 entry exists for pysnmp; not independently re-verified via a live pysnmp install/import in this research session) | Standard Stack, Code Examples Pattern 1 | If the exact import path or constructor kwarg names differ slightly in 7.1.21, the executor will hit an `ImportError`/`TypeError` at implementation time — low risk since the advisory-import-guard pattern (`_PYSNMP_AVAILABLE`) already means this fails safely (WARNING + null result), not a crash, but the executor should do a quick `python -c "from pysnmp.hlapi.v3arch.asyncio import UsmUserData"` sanity check before writing the full dispatcher. |
| A3 | `run_scan.py`'s independent SNMP-only pass (L1510-1600) and `hardware_scanner.py::fingerprint_one` Step 3 are the ONLY two SNMP entry points in the codebase requiring the v3 ladder | Architecture Patterns, Anti-Patterns to Avoid | Verified via `grep -rn "probe_snmp_target\|scan_snmp_targets" quirk/ run_scan.py` during this research session — only these two call sites found. Low risk of a missed third site, but the executor should re-grep at implementation time in case other in-flight phases (140+) have touched this file. |

**If this table is empty:** N/A — see entries above; A2 and A3 are the primary items needing
light validation at implementation start, A1 needs empirical validation against a real target.

## Open Questions (RESOLVED)

1. **Exact `authPriv`-only vs. `authNoPriv`/`noAuthNoPriv` handling for D-02's "modern-only" gate**
   — **RESOLVED (planning, Phase 139 plans 139-01/02/03):** Both cases are handled, exactly as the
   recommendation below proposed.
   - What we know: CONTEXT.md D-02 mandates SHA-family auth / AES-family priv only, with a
     mismatch becoming a distinct crypto-hygiene finding rather than a silent downgrade.
   - What's unclear: Whether "mismatch" means (a) the OPERATOR configured MD5/DES in
     `SnmpV3Credential` (reject at config-load time, fail fast) vs. (b) the TARGET DEVICE only
     supports MD5/DES even though the operator configured SHA/AES correctly (this is a target-side
     fact only discoverable at probe time, via a USM negotiation failure).
   - Recommendation: Handle both — validate `SnmpV3Credential.auth_protocol`/`priv_protocol` values
     at config-load time (reject non-SHA/AES values with a clear config error, never silently
     substitute); AND treat a probe-time USM protocol-negotiation failure against a device that
     apparently only offers weaker protocols as a distinct "v3 protocol mismatch" finding (D-02's
     "the mismatch itself becomes a distinct crypto-hygiene finding"), not just a generic fallback
     to v2c/none.
   - **Resolution:** Case (a) is handled at config-load in **139-01** via the
     `_SNMP_V3_AUTH_ALLOWED`/`_SNMP_V3_PRIV_ALLOWED` allowlists (non-SHA/AES → clear config error).
     Case (b) is handled at probe time in **139-02** via `_classify_v3_failure()`, which splits a
     USM `unsupportedSecurityLevel`/`usmStatsUnsupportedSecLevels`-style rejection into
     `snmp_v3_failure_kind="protocol-mismatch"` (distinct from wrongDigest/timeout →
     `"auth-failed"`). **139-03** maps that to the distinct `SNMP_MODE_V3_PROTOCOL_MISMATCH`
     (`"v3-protocol-mismatch"`) device state — separate from the generic `SNMP_MODE_V3_FAILED` — so
     the mismatch surfaces as its own report/dashboard state (via the render surfaces' known-value +
     raw-fallback mapping in 139-05/139-06). Curated label/color for this sixth state is a 139-05/06
     polish follow-up.

2. **Should `SnmpV3Credential.auth_key_env`/`priv_key_env` support keying by `host:port`, matching
   `BrokerCredential`'s exact `host:port` key convention, or just bare `host` (matching v2c's
   `snmp_community` which has no port concept since SNMP is always UDP/161)?**
   — **RESOLVED (planning, Phase 139 plan 139-01):** Key by **bare host**, per the recommendation.
   - What we know: `BrokerCredential`'s `Dict[str, BrokerCredential]` is keyed `host:port` (per
     CONTEXT.md canonical-refs framing). SNMP always targets UDP/161 in this codebase's current
     implementation (hardcoded at `snmp_scanner.py:193`, `(host, 161)`).
   - What's unclear: Whether a future non-161 SNMP port is ever a real scenario worth designing for
     now.
   - Recommendation: Key by bare `host` (not `host:port`) since UDP/161 is hardcoded and there is no
     current mechanism to scan alternate SNMP ports — matches the existing `enable_snmp`/
     `snmp_community` single-value-per-scan precedent more closely than `BrokerCredential`'s
     `host:port` (which exists because brokers commonly run on multiple ports per host). Flag this
     explicitly as a planner decision to confirm, not a locked research finding.
   - **Resolution:** Planner confirmed bare-host keying. 139-01's loader keys
     `cfg.connectors.snmp_v3_credentials` by bare host, and both entry-point lookups in 139-03
     (`snmp_v3_credentials.get(host)`) use the bare host — consistent with the single-value-per-scan
     `snmp_community` precedent.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `pysnmp` (v3arch module) | SNMPv3 USM transport | ✓ (same package as v2c, already installed) | `7.1.21` (per project-level STACK.md, not re-verified live this session) | — |
| Chaos-lab SNMPv3-capable target | Empirical validation of the timeout/retry multiplier (Pitfall 2 / SNMPV3-04) | ✗ — `hwcompat-snmp`'s `snmpd.conf` (verified live: `quantum-chaos-enterprise-lab/hwcompat-snmp/snmpd.conf`) configures ONLY `rocommunity public default` (v2c) — no `createUser`/USM line exists today | — | This phase must add a `createUser`/`rouser` USM line to the existing `snmpd.conf` (SHA auth + AES priv) as part of implementation — this is a **reconfiguration of the existing `hwcompat-snmp` service**, not a new chaos-lab profile, but per CLAUDE.md's chaos-lab-maintenance rule it still requires updating `docs/chaos-lab.md` §3.22, `README.md` line ~70, and `expected_results_hwcompat.md` in the SAME phase. `lab.sh` needs NO edit (confirmed: `ALL_PROFILES`/`_derive_all_profiles` auto-discovers Compose profiles, per the docker-compose.yml comment at line ~1345). |

**Missing dependencies with no fallback:**
- None — the only "missing" item (a live SNMPv3 target) has a fallback: implement the
  `snmpd.conf` USM reconfiguration in this same phase before attempting empirical timeout tuning.

**Missing dependencies with fallback:**
- Chaos-lab SNMPv3 target: add `createUser`/`rouser` line to `hwcompat-snmp/snmpd.conf` in this
  phase (see Common Pitfalls Pitfall 2 for the interim literature-based timeout recommendation to
  use before/independent of empirical validation).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing project-wide; `tests/` dir, `pytest.ini`/`pyproject.toml` config) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (existing — not phase-specific) |
| Quick run command | `pytest tests/test_credential_leakage.py tests/test_snmp_scanner_contract.py -x` (verify `test_snmp_scanner_contract.py` exists at implementation time — referenced by PITFALLS.md but not independently confirmed present in this research pass) |
| Full suite command | `pytest -m "not slow"` (existing project convention — `addopts` deselects `@slow` by default per project MEMORY.md) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SNMPV3-01 | Per-host SNMPv3 USM config loads correctly from YAML (`SnmpV3Credential` dict) | unit | `pytest tests/test_config.py -k snmp_v3 -x` | ❌ Wave 0 — new test cases needed in existing `tests/test_config.py` (verify filename at implementation) |
| SNMPV3-02 | v3 auth+priv success labeled distinctly from v3 noAuthNoPriv, v2c, none, v3-failed-fell-back | unit + integration | `pytest tests/test_snmp_scanner_contract.py -k "v3_label" -x` | ❌ Wave 0 |
| SNMPV3-03 | SNMPv3 secrets never appear in raw exceptions/logs/JSON | unit (existing pattern) + gate | `pytest tests/test_credential_leakage.py -k snmp -x` | ❌ Wave 0 — extend `MODIFIED_FILES` + add SNMPv3-specific sentinel test mirroring the existing `test_sentinel_not_in_*` pattern |
| SNMPV3-04 | v3 timeout budget re-derived, ≠ v2c budget, no spurious timeouts | unit | `pytest tests/test_snmp_scanner_contract.py -k "timeout" -x` | ❌ Wave 0 |
| (chaos-lab e2e) | Live scan against `hwcompat-snmp` with USM creds succeeds end-to-end | manual/smoke | `python run_scan.py --target 127.0.0.1 --port 20223 --enable-snmp --snmp-v3-username <user> ...` (exact CLI flag names TBD at planning) | ❌ Wave 0 — depends on chaos-lab `snmpd.conf` reconfiguration landing first |

### Sampling Rate
- **Per task commit:** `pytest tests/test_credential_leakage.py tests/test_snmp_scanner_contract.py -x`
- **Per wave merge:** `pytest -m "not slow"`
- **Phase gate:** Full suite green before `/gsd:verify-work`; chaos-lab manual smoke test run at
  least once against the reconfigured `hwcompat-snmp` container before phase close.

### Wave 0 Gaps
- [ ] `tests/test_snmp_scanner_contract.py` — verify this file exists (referenced by
      `.planning/research/PITFALLS.md` but not independently confirmed present in this session);
      if absent, create it covering v2c/v3 dispatch, null-safe failure shape, and timeout budgets.
- [ ] `tests/test_credential_leakage.py` — extend `MODIFIED_FILES` to include
      `quirk/scanner/snmp_scanner.py`; add SNMPv3-specific sentinel tests mirroring
      `test_sentinel_not_in_safe_str_*` patterns (auth passphrase / priv passphrase shapes).
- [ ] `quantum-chaos-enterprise-lab/hwcompat-snmp/snmpd.conf` — add `createUser`/`rouser` USM line
      (SHA auth + AES priv) alongside the existing `rocommunity public default` line.
- [ ] Config validation test for `SnmpV3Credential` rejecting non-SHA/non-AES protocol values at
      load time (D-02 enforcement).

*(These are net-new for this phase — the existing test infrastructure does not cover SNMPv3.)*

## Security Domain

> `security_enforcement` not found explicitly disabled in `.planning/config.json` — treating as
> enabled per default.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | yes | SNMPv3 USM itself IS an authentication mechanism being scanned/exercised — this phase implements a USM *client*, not a login surface for QUIRK itself; the relevant control is credential handling (V6-adjacent), not V2 in the traditional sense |
| V3 Session Management | no | SNMP GET/response cycles are stateless per-request (aside from the USM engine-time window, which is protocol state, not application session state) |
| V4 Access Control | no | Not applicable — this phase does not add a new access-control surface to QUIRK itself |
| V5 Input Validation | yes | Config-time validation of `SnmpV3Credential` fields (reject non-SHA/AES protocol names per D-02) is an input-validation control |
| V6 Cryptography | yes | `pysnmp`'s USM auth (HMAC-SHA) / priv (AES-CFB) implementations — never hand-roll (see Don't Hand-Roll table); D-02's SHA/AES-only mandate is itself a crypto-hygiene control this phase enforces |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| SNMPv3 passphrase leakage via unscrubbed exception text (Pitfall 1) | Information Disclosure | Route every exception through `safe_str()`; extend AST/import-presence leakage gate to `snmp_scanner.py` |
| USM replay/time-window abuse (`notInTimeWindow` handling) | Tampering / Denial of Service | Rely on pysnmp's built-in RFC 3414 time-window enforcement; do not persist/reuse engine state across scan sessions (Pitfall 2) |
| Config-file plaintext passphrase leakage | Information Disclosure | `SnmpV3Credential` stores env-var NAMES only, never inline secrets in YAML — mirrors `BrokerCredential.pass_env` |
| False "authenticated" labeling of an unauthenticated v3 responder (Pitfall 3) | Spoofing (of assurance level, not identity) | Explicit `securityLevel` tracking and distinct report labels — never collapse `noAuthNoPriv`/`authNoPriv`/`authPriv` into one "v3" label |

## Sources

### Primary (HIGH confidence)
- Direct codebase reads (this session, 2026-07-30): `quirk/scanner/snmp_scanner.py` (full file),
  `quirk/scanner/hardware_scanner.py` (lines 140-250), `quirk/config.py` (lines 190-410),
  `quirk/models.py` (`HardwareDevice`, lines 362-395), `quirk/db.py` (`_ADDITIVE_MIGRATIONS`, lines
  137-204), `run_scan.py` (SNMP-related lines 882-1598), `quirk/reports/writer.py` (lines 210-323),
  `quirk/merge/scan.py` (lines 232-268), `quirk/dashboard/api/routes/scan.py` (lines 784-820,
  1322-1372), `quirk/dashboard/api/schemas.py` (lines 100-117, 269), `quirk/cbom/builder.py` (lines
  1043-1077), `quirk/cbom/bridge.py` (lines 1-70), `quirk/util/safe_exc.py` (full file),
  `tests/test_credential_leakage.py` (full file), `quantum-chaos-enterprise-lab/hwcompat-snmp/snmpd.conf`
  (full file), `quantum-chaos-enterprise-lab/docker-compose.yml` (lines 1330-1380), `docs/chaos-lab.md`
  (lines 688-725), `quantum-chaos-enterprise-lab/README.md` (line 70)
- `.planning/phases/139-snmpv3-auth-priv-support/139-CONTEXT.md` — locked decisions D-01..D-04
- `.planning/REQUIREMENTS.md` — SNMPV3-01..04
- `.planning/STATE.md` — phase ordering rationale, deferred items

### Secondary (MEDIUM confidence)
- `.planning/research/STACK.md`, `.planning/research/ARCHITECTURE.md`, `.planning/research/PITFALLS.md`,
  `.planning/research/SUMMARY.md` — project-level v5.10 research pass (2026-07-30), which this
  phase-scoped document consolidates and verifies against live code. pysnmp v3arch HLAPI API surface
  (`UsmUserData`, `usmHMACSHAAuthProtocol`, `usmAesCfb128Protocol`) is WebSearch-sourced there against
  `docs.lextudio.com/pysnmp/v7.1` — not independently re-fetched via Context7/WebFetch in this
  session (Context7 unavailable in this environment; see Assumption A2).
- RFC 3414 (USM engine-discovery requirement) — general protocol-spec knowledge, not independently
  re-verified via WebFetch this session (carried forward from project-level PITFALLS.md).

### Tertiary (LOW/MEDIUM confidence, needs validation)
- The `timeout_v3 = timeout_v2c * 2` multiplier (Pitfall 2 / A1) — reasoned, not measured; needs
  empirical validation against the chaos-lab `hwcompat-snmp` target once its `snmpd.conf` gains a
  USM user in this phase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependency, existing pin verified by project-level research
- Architecture: HIGH — every claim in this document backed by a direct line-cited codebase read
  performed in this research session (not carried forward from project-level research unverified)
- Pitfalls: MEDIUM-HIGH — Pitfalls 1/3/4 are HIGH (directly grounded in this session's code reads);
  Pitfall 2's specific multiplier (A1) is MEDIUM (reasoned, flagged for empirical validation)

**Research date:** 2026-07-30
**Valid until:** 2026-08-29 (30 days — stable domain, no fast-moving external dependency)
