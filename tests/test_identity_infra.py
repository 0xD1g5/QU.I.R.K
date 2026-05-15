"""Phase 17 -- Identity Infrastructure RED scaffold.

Tests MUST FAIL before Plan 02 implementation lands.
Covers INFRA-01 (schema), INFRA-02 (config), INFRA-03 (extras group).

The model class is CryptoEndpoint (table: crypto_endpoints) -- the planning
docs call this "ScanResult" conceptually; the physical table name is used in
all inspector calls below.
"""

import pathlib
import unittest

from sqlalchemy import create_engine
from sqlalchemy import inspect as sa_inspect


class TestIdentityInfra(unittest.TestCase):
    """RED scaffold for Phase 17 identity infrastructure requirements."""

    # ------------------------------------------------------------------
    # INFRA-01 -- Schema: new identity columns on crypto_endpoints table
    # ------------------------------------------------------------------

    def test_schema_fresh_db_has_identity_columns(self):
        """Fresh in-memory DB must have kerberos_scan_json, saml_scan_json,
        dnssec_scan_json columns on the crypto_endpoints table.

        RED because: quirk/models.py CryptoEndpoint does not yet declare
        these columns. Base.metadata.create_all() will not produce them.
        """
        from quirk.models import Base

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        col_names = {
            col["name"]
            for col in sa_inspect(engine).get_columns("crypto_endpoints")
        }

        self.assertIn(
            "kerberos_scan_json",
            col_names,
            "CryptoEndpoint model missing kerberos_scan_json column -- "
            "add Column(Text, nullable=True) to quirk/models.py",
        )
        self.assertIn(
            "saml_scan_json",
            col_names,
            "CryptoEndpoint model missing saml_scan_json column -- "
            "add Column(Text, nullable=True) to quirk/models.py",
        )
        self.assertIn(
            "dnssec_scan_json",
            col_names,
            "CryptoEndpoint model missing dnssec_scan_json column -- "
            "add Column(Text, nullable=True) to quirk/models.py",
        )

    def test_schema_migration_idempotent(self):
        """The identity-column migration must be callable twice without error
        on an already-migrated database.

        Phase 77 D-21: per-feature _ensure_identity_columns helper consolidated
        into the generic _ensure_columns helper + _IDENTITY_COLUMNS tuple. The
        idempotency contract is unchanged.
        """
        from quirk.models import Base

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        try:
            from quirk.db import _IDENTITY_COLUMNS, _ensure_columns
        except ImportError:
            self.fail(
                "quirk.db does not export the generic _ensure_columns helper "
                "or the _IDENTITY_COLUMNS tuple (Phase 77 D-21 consolidation)."
            )

        # Both calls must succeed (idempotency requirement)
        _ensure_columns(engine, "crypto_endpoints", _IDENTITY_COLUMNS)
        _ensure_columns(engine, "crypto_endpoints", _IDENTITY_COLUMNS)

        # Columns must exist after migration
        col_names = {
            col["name"]
            for col in sa_inspect(engine).get_columns("crypto_endpoints")
        }
        self.assertIn("kerberos_scan_json", col_names)
        self.assertIn("saml_scan_json", col_names)
        self.assertIn("dnssec_scan_json", col_names)

    # ------------------------------------------------------------------
    # INFRA-02 -- Config: ConnectorsCfg identity flags and target lists
    # ------------------------------------------------------------------

    def test_config_flags_accepted(self):
        """ConnectorsCfg must accept enable_kerberos, enable_saml, enable_dnssec
        keyword arguments without raising TypeError.

        RED because: ConnectorsCfg dataclass does not declare these fields yet.
        Passing unknown keyword args to a dataclass raises TypeError.
        """
        from quirk.config import ConnectorsCfg

        try:
            cfg = ConnectorsCfg(
                enable_aws=False,
                enable_azure=False,
                enable_kerberos=True,
                enable_saml=True,
                enable_dnssec=True,
            )
        except TypeError as exc:
            self.fail(
                f"ConnectorsCfg does not accept enable_kerberos/enable_saml/enable_dnssec "
                f"-- add bool fields per D-04. Original error: {exc}"
            )

        self.assertIs(
            cfg.enable_kerberos,
            True,
            "ConnectorsCfg.enable_kerberos did not store True",
        )
        self.assertIs(
            cfg.enable_saml,
            True,
            "ConnectorsCfg.enable_saml did not store True",
        )
        self.assertIs(
            cfg.enable_dnssec,
            True,
            "ConnectorsCfg.enable_dnssec did not store True",
        )

    def test_config_old_yaml_backward_compat(self):
        """Loading a v4.1 config dict (no identity fields) via config_from_dict
        must not raise, and identity fields must default to False / [].

        RED because: ConnectorsCfg does not have these fields yet, so
        accessing cfg.connectors.enable_kerberos raises AttributeError.
        """
        from quirk.config import config_from_dict

        raw = {
            "assessment": {
                "name": "Test",
                "report_owner": "Tester",
                "data_classification": "INTERNAL",
                "timezone": "UTC",
            },
            "scan": {
                "timeout_seconds": 10,
                "concurrency": 5,
                "ports_tls": [443],
                "include_sni": True,
            },
            "targets": {
                "fqdns": [],
                "cidrs": [],
                "include_ips": ["127.0.0.1"],
                "exclude_ips": [],
            },
            "connectors": {"enable_aws": False, "enable_azure": False},
            "output": {"directory": "./out", "db_path": "./quirk.db"},
        }

        cfg = config_from_dict(raw)

        self.assertIs(
            cfg.connectors.enable_kerberos,
            False,
            "ConnectorsCfg.enable_kerberos default missing -- must default to False per D-04",
        )
        self.assertEqual(
            cfg.connectors.kerberos_targets,
            [],
            "ConnectorsCfg.kerberos_targets default missing -- must default to [] per D-05",
        )
        self.assertIs(
            cfg.connectors.enable_saml,
            False,
            "ConnectorsCfg.enable_saml default missing -- must default to False per D-04",
        )
        self.assertEqual(
            cfg.connectors.saml_targets,
            [],
            "ConnectorsCfg.saml_targets default missing -- must default to [] per D-05",
        )
        self.assertIs(
            cfg.connectors.enable_dnssec,
            False,
            "ConnectorsCfg.enable_dnssec default missing -- must default to False per D-04",
        )
        self.assertEqual(
            cfg.connectors.dnssec_targets,
            [],
            "ConnectorsCfg.dnssec_targets default missing -- must default to [] per D-05",
        )

    # ------------------------------------------------------------------
    # INFRA-03 -- pyproject.toml [identity] extras group
    # ------------------------------------------------------------------

    def test_pyproject_identity_extras_declared(self):
        """pyproject.toml must declare an [identity] optional extras group
        with the five required packages.

        RED because: pyproject.toml currently only has a [dashboard] group;
        no [identity] group exists.
        """
        source = pathlib.Path("pyproject.toml").read_text(encoding="utf-8")

        self.assertIn(
            "identity = [",
            source,
            "pyproject.toml does not declare [identity] extras group -- "
            "add after [dashboard] group per D-07",
        )
        self.assertIn(
            '"impacket>=0.13.0,<0.14"',
            source,
            "pyproject.toml [identity] group missing impacket>=0.13.0,<0.14 -- "
            "add per D-07",
        )
        self.assertIn(
            '"dnspython[dnssec]>=2.8.0"',
            source,
            "pyproject.toml [identity] group missing dnspython[dnssec]>=2.8.0 -- "
            "add per D-07",
        )
        self.assertIn(
            '"lxml>=6.0"',
            source,
            "pyproject.toml [identity] group missing lxml>=6.0 -- add per D-07",
        )
        self.assertIn(
            '"defusedxml>=0.7.1"',
            source,
            "pyproject.toml [identity] group missing defusedxml>=0.7.1 -- add per D-07",
        )
        self.assertIn(
            '"signxml>=4.4.0"',
            source,
            "pyproject.toml [identity] group missing signxml>=4.4.0 -- add per D-07",
        )

    # ------------------------------------------------------------------
    # INFRA-02 -- config_template.yaml identity section
    # ------------------------------------------------------------------

    def test_config_template_has_identity_section(self):
        """quirk/config_template.yaml must contain a commented identity
        connectors subsection with all six identity fields.

        RED because: config_template.yaml currently ends after the
        intelligence section; no identity block exists.
        """
        source = pathlib.Path("quirk/config_template.yaml").read_text(encoding="utf-8")

        self.assertIn(
            "enable_kerberos",
            source,
            "config_template.yaml missing enable_kerberos -- "
            "add identity connectors section per D-09",
        )
        self.assertIn(
            "enable_saml",
            source,
            "config_template.yaml missing enable_saml -- "
            "add identity connectors section per D-09",
        )
        self.assertIn(
            "enable_dnssec",
            source,
            "config_template.yaml missing enable_dnssec -- "
            "add identity connectors section per D-09",
        )
        self.assertIn(
            "kerberos_targets",
            source,
            "config_template.yaml missing kerberos_targets -- "
            "add identity connectors section per D-09",
        )
        self.assertIn(
            "saml_targets",
            source,
            "config_template.yaml missing saml_targets -- "
            "add identity connectors section per D-09",
        )
        self.assertIn(
            "dnssec_targets",
            source,
            "config_template.yaml missing dnssec_targets -- "
            "add identity connectors section per D-09",
        )


if __name__ == "__main__":
    unittest.main()
