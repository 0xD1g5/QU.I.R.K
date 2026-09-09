"""Server-side credential redaction for `AppConfig`.

Phase 192 / PARITY-01 / D-05 / D-06 / D-07.

This module is the single gate between the server's typed config tree
(`quirk.config.AppConfig`) and any serialized payload that could leave the
server (dashboard API, pre-flight guards, CLI diagnostics). It answers two
questions without ever letting a secret value cross that boundary:

  - "Is this field a credential?" (`is_credential_field`)
  - "Is this credential currently set?" (`credential_is_set`)

and produces a fully redacted, JSON-serializable projection of an
`AppConfig` (`redact_config`).

**Invariant: no function in this module ever returns, logs, or otherwise
propagates a credential VALUE.** Only its set/not-set status is exposed.

D-06's fail-closed rule: a field is treated as a credential if EITHER it is
listed in `CREDENTIAL_REGISTRY` OR its name matches `CREDENTIAL_NAME_PATTERN`
— even if the registry is incomplete or drifts as new connectors ship —
unless it is explicitly dispositioned safe via `CREDENTIAL_NAME_SAFE_FIELDS`.
Registry-or-pattern, safe-list wins.
"""

from __future__ import annotations

import dataclasses
import os
import re
from dataclasses import dataclass
from typing import Any, Optional

REDACTED_SET = "•••• (set)"
REDACTED_UNSET = "•••• (not set)"


@dataclass(frozen=True)
class CredentialField:
    section: str
    name: str
    env_fallback: Optional[str] = None


# Direct read of quirk/config.py's ConnectorsCfg / SecurityCfg for every
# field that holds a secret value (not an env-var NAME, not a username).
CREDENTIAL_REGISTRY: tuple[CredentialField, ...] = (
    CredentialField("connectors", "vault_token", "VAULT_TOKEN"),
    CredentialField("connectors", "adcs_password"),
    CredentialField("connectors", "pg_scanner_password"),
    CredentialField("connectors", "mysql_scanner_password"),
    CredentialField("connectors", "snmp_community"),
    CredentialField("security", "api_token", "QUIRK_API_TOKEN"),
)

# The defensive fail-closed net (D-06). Deliberately does NOT include a bare
# "key" token — that would swallow non-secret fields like
# azure_keyvault_urls / ssh_key_types, turning fail-closed into fail-useless.
CREDENTIAL_NAME_PATTERN: re.Pattern = re.compile(
    r"(password|passwd|passphrase|secret|token|credential|community"
    r"|private_key|api_key|apikey|access_key|client_secret|connection_string)",
    re.IGNORECASE,
)

# Explicit, per-entry-justified disposition ledger (D-06 / T-192-07): names
# that match the pattern net or otherwise look secret-shaped but are
# deliberately NOT redacted.
CREDENTIAL_NAME_SAFE_FIELDS: frozenset[str] = frozenset(
    {
        # These hold environment-variable NAMES, not secrets — the operator
        # needs to see WHICH variable to set (pairs with OBS-01's
        # missing-credentials pre-flight reason).
        "pass_env",
        "auth_key_env",
        "priv_key_env",
        # Usernames are identity, not secrets — useful pre-flight signal for
        # an already-authenticated operator.
        "adcs_user",
        "pg_scanner_user",
        "mysql_scanner_user",
        # Container/map fields themselves (their VALUES are dataclasses
        # walked separately via _CREDENTIAL_MAP_FIELDS) — the field NAME
        # matches the "credential" token but the field is never redacted as
        # a leaf value.
        "broker_credentials",
        "snmp_v3_credentials",
    }
)

# Section names under which a dict-of-dataclass field's VALUES should be
# walked using the map's own name as the credential-lookup section (rather
# than the containing dataclass's section) — mirrors BrokerCredential.pass_env
# / SnmpV3Credential.auth_key_env / priv_key_env resolving against
# CREDENTIAL_NAME_SAFE_FIELDS.
_CREDENTIAL_MAP_FIELDS = ("broker_credentials", "snmp_v3_credentials")


def _registry_entry(section: str, name: str) -> Optional[CredentialField]:
    for entry in CREDENTIAL_REGISTRY:
        if entry.section == section and entry.name == name:
            return entry
    return None


def is_credential_field(section: str, name: str) -> bool:
    """True if (section, name) must be redacted — registry-or-pattern, safe-list wins."""
    if name in CREDENTIAL_NAME_SAFE_FIELDS:
        return False
    if _registry_entry(section, name) is not None:
        return True
    return bool(CREDENTIAL_NAME_PATTERN.search(name))


def credential_is_set(section: str, name: str, value: Any) -> bool:
    """True if a credential has a value or a live env-var fallback.

    Reads env-var PRESENCE only — the env var's value is never returned,
    logged, or embedded.
    """
    if value is not None and str(value).strip():
        return True
    entry = _registry_entry(section, name)
    if entry is not None and entry.env_fallback:
        env_value = os.environ.get(entry.env_fallback)
        if env_value is not None and env_value.strip():
            return True
    return False


def _redact_dataclass(instance: Any, section: str) -> dict:
    result: dict = {}
    for f in dataclasses.fields(instance):
        name = f.name
        if name.startswith("_"):
            continue
        value = getattr(instance, name)
        if name in _CREDENTIAL_MAP_FIELDS and isinstance(value, dict):
            result[name] = {
                key: _redact_dataclass(entry, name) for key, entry in value.items()
            }
            continue
        if is_credential_field(section, name):
            result[name] = (
                REDACTED_SET if credential_is_set(section, name, value) else REDACTED_UNSET
            )
            continue
        result[name] = _redact_value(value, section)
    return result


def _redact_value(value: Any, section: str) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _redact_dataclass(value, section)
    if isinstance(value, dict):
        return {key: _redact_value(v, section) for key, v in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    if isinstance(value, tuple):
        return [_redact_value(v, section) for v in value]
    if isinstance(value, list):
        return [_redact_value(v, section) for v in value]
    return value


def redact_config(cfg: Any) -> dict:
    """Recursively redact an `AppConfig` into a JSON-serializable plain dict.

    Redacts at construction time (D-07) — never `dataclasses.asdict()` first
    and then filter, since that would produce the unredacted structure in
    memory before redaction has a chance to run.
    """
    result: dict = {}
    for f in dataclasses.fields(cfg):
        name = f.name
        if name.startswith("_"):
            continue
        value = getattr(cfg, name)
        if name in _CREDENTIAL_MAP_FIELDS and isinstance(value, dict):
            result[name] = {
                key: _redact_dataclass(entry, name) for key, entry in value.items()
            }
            continue
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            result[name] = _redact_dataclass(value, name)
        else:
            result[name] = _redact_value(value, name)
    return result
