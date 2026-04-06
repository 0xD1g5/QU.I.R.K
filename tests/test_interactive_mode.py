"""Phase 13 — Interactive Mode Overhaul: TDD RED scaffold for INTER-01 through INTER-10.

All tests in this file are decorated with @unittest.expectedFailure because they define the
Plan 02 implementation contract. They MUST fail against the current quirk/interactive.py
because:

  - interactive_config() returns AppConfig (not tuple[AppConfig, str])  — D-07
  - timezone is prompted (not auto-detected)                            — D-01
  - include_sni is prompted (not hardcoded True)                        — D-02
  - ports_tls is prompted (not hardcoded consulting-grade list)         — D-03
  - prompt order is metadata-first, not targets-first                   — D-15
  - profile selection menu does not exist                               — D-05/D-06
  - AWS/Azure may carry "(stub)" labels                                 — D-13
  - data classification is a free-text prompt, not a unified 4-tier menu — D-10/D-11

Plan 02 must make every test GREEN by implementing the new interactive_config() behaviour.

Usage (Wave 0 / RED state):
    python -m pytest tests/test_interactive_mode.py -x -q
    # Expected: all tests pass as "expected failures" (xfail) — suite exit 0
"""

from __future__ import annotations

import unittest
from unittest.mock import patch, call

from quirk.interactive import interactive_config

# ---------------------------------------------------------------------------
# MINIMAL_INPUTS — canonical input sequence for the NEW prompt order (D-15)
#
# New prompt order per D-15:
#   1. Targets     — CIDRs, FQDNs, include_ips, exclude_ips
#   2. Scan opts   — profile selection (quick/standard/deep)
#   3. Scanners    — JWT enable, container enable, source enable
#   4. Connectors  — AWS enable, Azure enable
#   5. Output      — output directory, db_path
#   6. Metadata    — assessment name, data classification, report_owner
#                    data_longevity_years, exposure, crown_jewels
#
# This sequence does NOT include a timezone prompt (auto-detected — D-01),
# an SNI prompt (hardcoded True — D-02), or a ports_tls prompt (hardcoded — D-03).
# ---------------------------------------------------------------------------

MINIMAL_INPUTS = [
    "",                         # 0  CIDRs (empty)
    "scan.example.com",         # 1  FQDNs
    "",                         # 2  include_ips (empty)
    "",                         # 3  exclude_ips (empty)
    "",                         # 4  profile selection (default = standard)
    "n",                        # 5  enable JWT (no)
    "n",                        # 6  enable container (no)
    "n",                        # 7  enable source (no)
    "n",                        # 8  enable AWS (no)
    "n",                        # 9  enable Azure (no)
    "output",                   # 10 output directory
    "output/quirk.db",          # 11 db_path
    "",                         # 12 assessment name (default)
    "3",                        # 13 data classification: confidential (default)
    "",                         # 14 report_owner (default)
    "7",                        # 15 data_longevity_years (default)
    "2",                        # 16 exposure (default = mixed)
    "",                         # 17 crown_jewels (empty)
]


# ---------------------------------------------------------------------------
# INTER-01 — Timezone is auto-detected, not prompted
# ---------------------------------------------------------------------------


class TestTimezoneAutoDetected(unittest.TestCase):
    """INTER-01: interactive_config() auto-detects timezone; no input() call for timezone."""

    def test_timezone_auto_detected(self):
        """cfg.assessment.timezone must be a non-empty auto-detected string.

        The mock side_effect uses MINIMAL_INPUTS (new prompt order).
        Timezone must be auto-detected — no input() call for timezone.
        Return type is tuple[AppConfig, str] per D-07.
        """
        inputs = list(MINIMAL_INPUTS)
        with patch("builtins.input", side_effect=inputs):
            result = interactive_config()

        # After D-07 the return type is tuple[AppConfig, str]
        cfg, profile = result

        # Timezone must be a non-empty auto-detected string (e.g., "EDT", "UTC", "PST")
        assert cfg.assessment.timezone, (
            "cfg.assessment.timezone is empty — must be auto-detected via "
            "datetime.datetime.now().astimezone().tzname()"
        )

        # Verify the mock was not called with any argument containing "Timezone" or "timezone"
        # (i.e., no timezone prompt was issued)
        import unittest.mock as _mock
        mock_calls = []
        with patch("builtins.input", side_effect=list(MINIMAL_INPUTS)) as mock_input:
            try:
                interactive_config()
            except Exception:
                pass
            mock_calls = [str(c) for c in mock_input.call_args_list]

        for call_str in mock_calls:
            assert "imezone" not in call_str, (
                f"Timezone prompt was issued — should be auto-detected. Call: {call_str}"
            )


# ---------------------------------------------------------------------------
# INTER-02 — No SNI prompt; include_sni hardcoded True
# ---------------------------------------------------------------------------


class TestNoSniPrompt(unittest.TestCase):
    """INTER-02: interactive_config() does not prompt for SNI; returns include_sni=True."""

    def test_no_sni_prompt(self):
        """cfg.scan.include_sni must be True without any prompt.

        SNI is hardcoded True per D-02. Return type is tuple[AppConfig, str].
        """
        inputs = list(MINIMAL_INPUTS)
        with patch("builtins.input", side_effect=inputs):
            result = interactive_config()

        cfg, profile = result

        # SNI must be hardcoded True (D-02)
        assert cfg.scan.include_sni is True, (
            f"cfg.scan.include_sni={cfg.scan.include_sni!r}; expected True (hardcoded per D-02)"
        )

        # Verify no prompt text contained "SNI" or "sni"
        with patch("builtins.input", side_effect=list(MINIMAL_INPUTS)) as mock_input:
            try:
                interactive_config()
            except Exception:
                pass
            for c in mock_input.call_args_list:
                args_str = str(c)
                assert "SNI" not in args_str and "sni" not in args_str.lower(), (
                    f"SNI prompt was issued — should be hardcoded. Call: {args_str}"
                )


# ---------------------------------------------------------------------------
# INTER-03 — No ADCS prompt
# ---------------------------------------------------------------------------


class TestNoAdcsPrompt(unittest.TestCase):
    """INTER-03: interactive_config() does not prompt for Windows ADCS."""

    def test_no_adcs_prompt(self):
        """No input() call should mention ADCS, adcs, or windows_adcs.

        ADCS feature removed per D-04/INTER-03.
        """
        inputs = list(MINIMAL_INPUTS)
        with patch("builtins.input", side_effect=inputs) as mock_input:
            result = interactive_config()
            all_calls = [str(c) for c in mock_input.call_args_list]

        cfg, profile = result

        for call_str in all_calls:
            assert "ADCS" not in call_str, (
                f"ADCS prompt was issued — feature removed. Call: {call_str}"
            )
            assert "adcs" not in call_str.lower(), (
                f"ADCS-related prompt was issued. Call: {call_str}"
            )
            assert "windows_adcs" not in call_str.lower(), (
                f"windows_adcs prompt was issued. Call: {call_str}"
            )


# ---------------------------------------------------------------------------
# INTER-04 — No "(stub)" labels; credential warnings printed for enabled connectors
# ---------------------------------------------------------------------------


class TestConnectorLabelsNoStub(unittest.TestCase):
    """INTER-04: Connector section labels AWS/Azure without '(stub)'; shows credential warnings."""

    def test_connector_labels_no_stub(self):
        """No print() call should contain '(stub)'; AWS and Azure credential warnings shown.

        When AWS is enabled (answer 'y'), the code must print text containing
        'AWS_ACCESS_KEY_ID' (per D-14). Similarly for Azure with 'AZURE_CLIENT_ID'.
        """
        # Enable both AWS and Azure by answering "y" at positions 8 and 9
        inputs = list(MINIMAL_INPUTS)
        inputs[8] = "y"   # enable AWS
        inputs[9] = "y"   # enable Azure

        printed_lines: list[str] = []

        def capture_print(*args, **kwargs):
            printed_lines.append(" ".join(str(a) for a in args))

        with patch("builtins.input", side_effect=inputs):
            with patch("builtins.print", side_effect=capture_print):
                result = interactive_config()

        cfg, profile = result

        # No stub labels anywhere in printed output
        for line in printed_lines:
            assert "(stub)" not in line, (
                f"Found '(stub)' in print output — remove stub labels per D-13. Line: {line!r}"
            )

        # AWS credential warning must appear (per D-14)
        aws_warning_found = any("AWS_ACCESS_KEY_ID" in line for line in printed_lines)
        assert aws_warning_found, (
            "AWS credential warning not printed after enabling AWS connector. "
            "Expected text containing 'AWS_ACCESS_KEY_ID' per D-14."
        )

        # Azure credential warning must appear (per D-14)
        azure_warning_found = any("AZURE_CLIENT_ID" in line for line in printed_lines)
        assert azure_warning_found, (
            "Azure credential warning not printed after enabling Azure connector. "
            "Expected text containing 'AZURE_CLIENT_ID' per D-14."
        )


# ---------------------------------------------------------------------------
# INTER-05 — JWT, container, and source scanners are surfaced and configurable
# ---------------------------------------------------------------------------


class TestScannerEnables(unittest.TestCase):
    """INTER-05: JWT, container, and source scanner prompts exist and wire config correctly."""

    def test_scanner_enables(self):
        """Enable JWT, container, and source scanners; verify config fields populated.

        Prompt order per D-15: scanners appear at positions 5-7 in MINIMAL_INPUTS.
        """
        inputs = list(MINIMAL_INPUTS)
        inputs[5] = "y"                          # enable JWT
        # After "y" for JWT, a follow-up prompt for JWT endpoint URLs is expected
        # Insert the JWT target URL after the JWT enable prompt
        inputs.insert(6, "https://api.example.com")  # JWT endpoint URL
        # container enable is now at index 7
        inputs[7] = "y"
        # After "y" for container, insert container target
        inputs.insert(8, "nginx:latest")             # container image reference
        # source enable is now at index 9
        inputs[9] = "y"
        # After "y" for source, insert source target
        inputs.insert(10, "/src")                    # source code path

        with patch("builtins.input", side_effect=inputs):
            result = interactive_config()

        cfg, profile = result

        assert cfg.connectors.enable_jwt is True, "enable_jwt should be True"
        assert cfg.connectors.jwt_targets == ["https://api.example.com"], (
            f"jwt_targets={cfg.connectors.jwt_targets!r}; expected ['https://api.example.com']"
        )
        assert cfg.connectors.enable_container is True, "enable_container should be True"
        assert cfg.connectors.container_targets == ["nginx:latest"], (
            f"container_targets={cfg.connectors.container_targets!r}; expected ['nginx:latest']"
        )
        assert cfg.connectors.enable_source is True, "enable_source should be True"
        assert cfg.connectors.source_targets == ["/src"], (
            f"source_targets={cfg.connectors.source_targets!r}; expected ['/src']"
        )


# ---------------------------------------------------------------------------
# INTER-06 — Profile selection returns correct string
# ---------------------------------------------------------------------------


class TestProfileSelection(unittest.TestCase):
    """INTER-06: Profile selection menu returns correct profile string in tuple."""

    def test_profile_selection(self):
        """Selecting profile '3' (deep) returns profile=='deep'; empty string returns 'standard'.

        Profile selection menu implemented per D-05/D-06. Return type is tuple[AppConfig, str].
        """
        # Test: answer "3" for deep profile
        inputs_deep = list(MINIMAL_INPUTS)
        inputs_deep[4] = "3"   # profile selection: deep

        with patch("builtins.input", side_effect=inputs_deep):
            result = interactive_config()

        cfg, profile = result
        assert profile == "deep", (
            f"Expected profile='deep' when answering '3', got {profile!r}"
        )

        # Test: empty string defaults to standard
        inputs_default = list(MINIMAL_INPUTS)
        inputs_default[4] = ""   # profile selection: default

        with patch("builtins.input", side_effect=inputs_default):
            result2 = interactive_config()

        cfg2, profile2 = result2
        assert profile2 == "standard", (
            f"Expected profile='standard' for empty/default input, got {profile2!r}"
        )


# ---------------------------------------------------------------------------
# INTER-07 — Consulting-grade port list hardcoded (no prompt)
# ---------------------------------------------------------------------------


class TestConsultingPorts(unittest.TestCase):
    """INTER-07: ports_tls contains all 17 consulting-grade ports; no ports prompt issued."""

    def test_consulting_ports(self):
        """cfg.scan.ports_tls must equal the exact 17-port consulting set from D-03.

        Consulting-grade ports hardcoded per D-03. No prompt issued for ports.
        """
        EXPECTED_PORTS = {
            443, 8443, 9443, 10443, 4433, 5001,  # original list
            636, 3269,                             # LDAPS
            993, 995, 465,                         # IMAPS, POP3S, SMTPS
            6443, 2376,                            # K8s API, Docker TLS
            5432, 3306, 1433,                      # PostgreSQL, MySQL, MSSQL
            8200,                                  # Vault
        }

        inputs = list(MINIMAL_INPUTS)
        with patch("builtins.input", side_effect=inputs):
            result = interactive_config()

        cfg, profile = result
        actual_ports = set(cfg.scan.ports_tls)

        missing = EXPECTED_PORTS - actual_ports
        extra = actual_ports - EXPECTED_PORTS

        assert not missing and not extra, (
            f"ports_tls mismatch. Missing: {missing}. Extra: {extra}. "
            f"Got: {sorted(actual_ports)}"
        )


# ---------------------------------------------------------------------------
# INTER-08 — Prompt order is targets-first
# ---------------------------------------------------------------------------


class TestPromptOrder(unittest.TestCase):
    """INTER-08: Prompts appear in targets-first order per D-15."""

    def test_prompt_order(self):
        """Verify target prompts appear before profile/scanner prompts, output before metadata.

        Prompt order per D-15: Targets -> Scan opts -> Scanners -> Connectors -> Output -> Metadata.
        """
        # Capture all input() call prompt strings in order
        prompt_texts: list[str] = []
        original_input = __builtins__["input"] if isinstance(__builtins__, dict) else __import__("builtins").input

        inputs = list(MINIMAL_INPUTS)

        with patch("builtins.input", side_effect=inputs) as mock_input:
            try:
                interactive_config()
            except Exception:
                pass
            prompt_texts = []
            for c in mock_input.call_args_list:
                # call args: (prompt_string,) or keyword args
                if c.args:
                    prompt_texts.append(str(c.args[0]))
                elif c.kwargs:
                    prompt_texts.append(str(list(c.kwargs.values())[0]))

        # Find index of first target-related prompt (CIDR / FQDN / IP)
        target_keywords = ["CIDR", "FQDN", "IP", "cidr", "fqdn"]
        first_target_idx = next(
            (i for i, t in enumerate(prompt_texts)
             if any(kw in t for kw in target_keywords)),
            None,
        )

        # Find index of first metadata prompt (assessment name, classification, owner)
        metadata_keywords = ["Assessment name", "assessment name", "classification",
                              "owner", "report_owner", "Owner"]
        first_metadata_idx = next(
            (i for i, t in enumerate(prompt_texts)
             if any(kw in t for kw in metadata_keywords)),
            None,
        )

        # Find index of first output prompt (directory, db_path)
        output_keywords = ["Output", "output", "directory", "db_path", "SQLite"]
        first_output_idx = next(
            (i for i, t in enumerate(prompt_texts)
             if any(kw in t for kw in output_keywords)),
            None,
        )

        assert first_target_idx is not None, (
            "No target-related prompt (CIDR/FQDN/IP) found in prompt sequence"
        )
        assert first_metadata_idx is not None, (
            "No metadata prompt (assessment name/classification/owner) found"
        )
        assert first_output_idx is not None, (
            "No output prompt (directory/db_path) found"
        )

        # Targets must come BEFORE metadata
        assert first_target_idx < first_metadata_idx, (
            f"Targets prompt at index {first_target_idx} appears AFTER metadata prompt "
            f"at index {first_metadata_idx}. Prompts: {prompt_texts}"
        )

        # Output must come BEFORE metadata
        assert first_output_idx < first_metadata_idx, (
            f"Output prompt at index {first_output_idx} appears AFTER metadata prompt "
            f"at index {first_metadata_idx}."
        )


# ---------------------------------------------------------------------------
# INTER-09 — No enable_windows_adcs in generated config
# ---------------------------------------------------------------------------


class TestNoAdcsInConfig(unittest.TestCase):
    """INTER-09: Generated config dict has no enable_windows_adcs field anywhere."""

    def test_no_adcs_in_config(self):
        """dataclasses.asdict(cfg) must not contain 'enable_windows_adcs' key at any level.

        Dead ADCS field removed per D-04/INTER-09.
        """
        import dataclasses

        inputs = list(MINIMAL_INPUTS)
        with patch("builtins.input", side_effect=inputs):
            result = interactive_config()

        cfg, profile = result
        d = dataclasses.asdict(cfg)

        assert "enable_windows_adcs" not in str(d), (
            "enable_windows_adcs found in config dict — dead field must be absent per D-04/INTER-09. "
            f"Config keys: {list(d.keys())}"
        )


# ---------------------------------------------------------------------------
# INTER-10 — Unified data classification prompt sets both config fields
# ---------------------------------------------------------------------------


class TestDataClassificationUnified(unittest.TestCase):
    """INTER-10: Single classification prompt populates data_classification AND data_types."""

    def test_data_classification_unified(self):
        """Classification choice sets cfg.assessment.data_classification and get_context data_types.

        Tests three mappings from D-11:
          - "4" -> data_classification="regulated", data_types=["PCI", "PHI"]
          - "1" -> data_classification="public", data_types=["PUBLIC"]
          - "3" -> data_classification="confidential", data_types=["FINANCIAL", "TRADE"]

        Single unified prompt per D-10/D-11 sets both config fields.
        """
        from quirk.assessment.operator_context import get_context

        # ---- Test 1: "4" → regulated ----------------------------------------
        inputs_regulated = list(MINIMAL_INPUTS)
        inputs_regulated[13] = "4"  # data classification: regulated

        with patch("builtins.input", side_effect=inputs_regulated):
            result = interactive_config()
        cfg, profile = result

        assert cfg.assessment.data_classification == "regulated", (
            f"data_classification={cfg.assessment.data_classification!r}; "
            f"expected 'regulated' for choice '4'"
        )
        ctx = get_context(cfg)
        assert ctx["data_types"] == ["PCI", "PHI"], (
            f"data_types={ctx['data_types']!r}; expected ['PCI', 'PHI'] for 'regulated'"
        )

        # ---- Test 2: "1" → public -------------------------------------------
        inputs_public = list(MINIMAL_INPUTS)
        inputs_public[13] = "1"

        with patch("builtins.input", side_effect=inputs_public):
            result2 = interactive_config()
        cfg2, profile2 = result2

        assert cfg2.assessment.data_classification == "public", (
            f"data_classification={cfg2.assessment.data_classification!r}; expected 'public'"
        )
        ctx2 = get_context(cfg2)
        assert ctx2["data_types"] == ["PUBLIC"], (
            f"data_types={ctx2['data_types']!r}; expected ['PUBLIC'] for 'public'"
        )

        # ---- Test 3: "3" → confidential (default) ---------------------------
        inputs_conf = list(MINIMAL_INPUTS)
        inputs_conf[13] = "3"

        with patch("builtins.input", side_effect=inputs_conf):
            result3 = interactive_config()
        cfg3, profile3 = result3

        assert cfg3.assessment.data_classification == "confidential", (
            f"data_classification={cfg3.assessment.data_classification!r}; expected 'confidential'"
        )
        ctx3 = get_context(cfg3)
        assert ctx3["data_types"] == ["FINANCIAL", "TRADE"], (
            f"data_types={ctx3['data_types']!r}; expected ['FINANCIAL', 'TRADE'] for 'confidential'"
        )


if __name__ == "__main__":
    unittest.main()
