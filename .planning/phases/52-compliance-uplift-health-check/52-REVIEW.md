---
phase: 52-compliance-uplift-health-check
reviewed: 2026-05-05T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - quirk/cbom/builder.py
  - quirk/cli/doctor_cmd.py
  - quirk/compliance/__init__.py
  - quirk/scanner/saml_scanner.py
  - run_scan.py
  - quantum-chaos-enterprise-lab/lab.sh
  - tests/test_cbom_builder.py
  - tests/test_compliance_schema.py
  - tests/test_doctor_cmd.py
  - tests/test_writer.py
  - docs/operators-guide.md
  - docs/configuration.md
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Phase 52: Code Review Report

**Reviewed:** 2026-05-05T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Phase 52 delivers SOC2/ISO 27001 compliance uplift, FIPS 140-3 CBOM annotation, and the `quirk doctor` pre-engagement health-check command. The CBOM builder and compliance module are structurally sound. The doctor command and test coverage have gaps. The SAML scanner contains one security issue (TLS verification disabled) and two code quality defects (dead function, discarded severity value). Documentation for the new frameworks and connectors is incomplete.

---

## Critical Issues

### CR-01: TLS Certificate Verification Disabled for All SAML Metadata Fetches

**File:** `quirk/scanner/saml_scanner.py:65`
**Issue:** `_fetch_metadata()` passes `verify=False` to `httpx.get()` for all SAML IdP metadata and OIDC discovery URL fetches. The comment attributes this to "enterprise CAs (D-13, D-14)" but the mitigation is a blanket disable rather than a custom CA bundle. Any attacker with network position between the scanner host and an IdP can serve a forged SAML metadata document. The lxml XXE mitigations (`resolve_entities=False`, `no_network=True`) do not block this vector because the content is already attacker-controlled before parsing begins. Forged content is then persisted to the SQLite scan database as if it were legitimate IdP data.

**Fix:** Accept an optional CA bundle path via a config knob and pass it as `verify=ca_bundle_path`. Fall back to `verify=True` (the httpx default) rather than `verify=False`. For self-signed enterprise CAs, provide a documented config key (e.g. `connectors.saml_ca_bundle`) so operators can opt in to the bypass explicitly:

```python
# In _fetch_metadata:
def _fetch_metadata(url: str, timeout: int, ca_bundle: str | None = None) -> "bytes | None":
    verify: bool | str = ca_bundle if ca_bundle else True
    response = httpx.get(url, timeout=timeout, follow_redirects=True, verify=verify)
```

---

## Warnings

### WR-01: `severity` Variable Computed in OIDC Parser but Never Stored on CryptoEndpoint

**File:** `quirk/scanner/saml_scanner.py:335-347, 351-363`
**Issue:** In `_parse_oidc_discovery()`, `severity = OIDC_ALG_SEVERITY.get(alg)` is evaluated and its truthiness gates endpoint creation, but the value (`"HIGH"` for RSA/PSS algorithms) is never assigned to `ep.severity`. The `CryptoEndpoint` model has a `severity` column. As shipped, all OIDC algorithm findings enter the database with `severity=None`, leaving the risk_engine to reclassify them from scratch. If the risk_engine does not have matching logic for the SAML/OIDC protocol, severity remains null in reports. At minimum this is dead code; at worst it is a classification gap.

**Fix:** Store the severity on the created endpoint:

```python
severity = OIDC_ALG_SEVERITY.get(alg)
if severity is not None:
    ep = CryptoEndpoint(
        host=host,
        port=port,
        protocol="SAML",
        cert_pubkey_alg=alg,
        cert_pubkey_size=2048 if (alg.startswith("RS") or alg.startswith("PS")) else None,
        service_detail="oidc-discovery|id_token_signing_alg",
        saml_scan_json=json.dumps(scan_dict),
        scanned_at=now,
        severity=severity,   # <-- add this
    )
```

Apply the same fix to the `request_algs` loop at line 351-363.

---

### WR-02: `_classify_key_severity` Defined but Never Called — Dead Code

**File:** `quirk/scanner/saml_scanner.py:135-154`
**Issue:** `_classify_key_severity(key_alg, key_bits)` is defined with a docstring citing D-07 (per-key quantum severity classification for SAML certs), but it is never invoked anywhere in the file. The signing-cert loop (lines 207-229) and encryption-cert loop (lines 237-259) create `CryptoEndpoint` objects without calling this function, so SAML signing/encryption certificate findings carry no severity at the scanner level. This function exists only as dead code and its presence implies an unfinished integration.

**Fix:** Either invoke the function to set `ep.severity` for each signing/encryption cert endpoint, or delete it and document that SAML cert severity is assigned entirely by the risk_engine. The former is the evident original intent given the D-07 spec citation.

```python
# In the signing cert loop, after computing cert_info:
cert_severity = _classify_key_severity(cert_info["key_alg"], cert_info["key_bits"])
ep = CryptoEndpoint(
    ...
    severity=cert_severity,
)
```

---

### WR-03: PyYAML Import Failure in `_check_config` Reported as Config Malformed

**File:** `quirk/cli/doctor_cmd.py:92-97`
**Issue:** `_check_config()` does `import yaml` inside a bare `except Exception` handler. If PyYAML is not installed (e.g., in a minimal Python environment), the `ImportError` is caught and the function returns `(True, None, "[red][✗] ./config.yaml malformed: No module named 'yaml'[/red]")`, setting `cfg_failed=True` and causing `quirk doctor` to exit 1. The operator sees a misleading message: the config file is not malformed — the yaml dependency is missing. This will produce false-positive failures in environments where PyYAML is conditionally absent.

**Fix:** Separate the import failure from the parse failure:

```python
try:
    import yaml
except ImportError:
    return False, "info", "[yellow][!] pyyaml not installed — cannot validate config[/yellow]"
try:
    with open(config_path, "r") as fh:
        yaml.safe_load(fh)
    return False, None, f"[green][✓][/green] {config_path} parses cleanly"
except Exception as exc:
    return True, None, f"[red][✗] {config_path} malformed: {exc}[/red]"
```

---

### WR-04: `test_doctor_exits_0_all_pass` Does Not Mock Compliance Freshness — Test Will Become Flaky

**File:** `tests/test_doctor_cmd.py:8-19`
**Issue:** The test mocks `shutil.which`, `sqlite3.connect`, and `socket.create_connection` but does not mock `quirk.compliance.COMPLIANCE_MAP` or the compliance freshness check. The test relies on the real compliance module, meaning it passes only as long as the `last_verified` dates in `quirk/compliance/__init__.py` remain within `STALENESS_THRESHOLD_DAYS` (365 days). Currently both `_PHASE_49_VERIFIED` and `_PHASE_52_VERIFIED` are `2026-05-05`; after `2027-05-05` this test will begin failing in CI with no code change required, masking real failures.

**Fix:** Mock `_check_compliance_freshness` in the test to isolate the doctor command's exit-code logic from real compliance data:

```python
def test_doctor_exits_0_all_pass(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda x: "/usr/bin/" + x)
    monkeypatch.setattr(
        "quirk.cli.doctor_cmd._check_compliance_freshness",
        lambda: (True, "[green][✓][/green] all frameworks within freshness window"),
    )
    with mock.patch("sqlite3.connect") as mock_conn:
        ...
```

Apply the same isolation to `test_informational_checks_never_exit_1`.

---

### WR-05: `operators-guide.md` §7.2 Omits SOC2 and ISO 27001:2022 Monitoring URLs

**File:** `docs/operators-guide.md:344-349`
**Issue:** Phase 52 added SOC2 (CC6.6, CC6.7) and ISO 27001:2022 (8.24, 8.26) entries to `COMPLIANCE_MAP`. The quarterly review checklist at §7.1 and the source-URL table at §7.2 still list only PCI-DSS, HIPAA, and FIPS 140-3. An operator following §7.1 step 2 ("Visit each publisher URL") has no guidance on where to monitor SOC2 or ISO 27001 for revisions. The §7.4 upgrade path worked example also only covers PCI-DSS. If an SOC2 or ISO 27001 revision is published, operators have no documented process to detect or apply it.

**Fix:** Add rows to the §7.2 table:

```markdown
| SOC2 Trust Services Criteria | AICPA | https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater/trust-services-criteria |
| ISO 27001:2022 | ISO | https://www.iso.org/standard/82875.html |
```

Also extend §7.4 with a brief note that the same upgrade-path pattern applies to `_soc2()` and `_iso()` helpers.

---

## Info

### IN-01: `LXML_AVAILABLE` Flag Name Is Misleading When defusedxml Is the Active Parser

**File:** `quirk/scanner/saml_scanner.py:13-24`
**Issue:** The variable `LXML_AVAILABLE` is set to `True` in both the lxml path and the defusedxml fallback path. When lxml is absent but defusedxml is installed, `LXML_AVAILABLE=True` despite lxml not being available. The intent is to signal "a safe XML parser is available," but the name implies lxml specifically. This confuses any future developer reading the gate at line 379 (`if not LXML_AVAILABLE: return []`).

**Fix:** Rename to `_SAFE_XML_AVAILABLE` or `_XML_PARSER_AVAILABLE` and update the guard accordingly.

---

### IN-02: `status_report(format=...)` Shadows Python Built-in `format`

**File:** `quirk/compliance/__init__.py:251`
**Issue:** The parameter name `format` shadows the Python built-in `format()` function within the body of `status_report`. While the function body does not call the built-in `format`, this is a latent maintenance trap: any future developer adding a `format(value, spec)` call inside this function would get a `TypeError` without a clear error message.

**Fix:** Rename the parameter to `output_format`:

```python
def status_report(output_format: str = "text") -> None:
```

Update the call site in `run_scan.py:243`: `status_report(format=comp_args.format)` → `status_report(output_format=comp_args.format)`.

---

### IN-03: Shipped TODO Comment in `quirk/compliance/__init__.py`

**File:** `quirk/compliance/__init__.py:3`
**Issue:** The module docstring contains `# TODO Phase 50` referencing a maintenance cadence doc that was deferred. Phase 50 has shipped. The comment is stale and leaves readers uncertain whether the referenced task was ever completed.

**Fix:** Remove the `# TODO Phase 50` suffix since the maintenance cadence section now exists in `docs/operators-guide.md §7`.

```python
"""Phase 49 D-01: Compliance mapping for QUIRK findings (PCI-DSS 4.0.1, HIPAA 45 CFR, FIPS 140-3).

Maintenance cadence: see docs/operators-guide.md §"Compliance Map Maintenance".
"""
```

---

_Reviewed: 2026-05-05T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
