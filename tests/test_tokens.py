"""Minted bearer tokens must survive being passed as a separate CLI argument.

`secrets.token_urlsafe` draws from A-Z a-z 0-9 - _, so about 1 token in 64
starts with "-". argparse reads `--api-token -Xyz...` as a new option and
fails with "argument --api-token: expected one argument". That was the real
cause of the intermittent Windows Sensor E2E failure filed as todo 260929.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pytest

from quirk import tokens

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_mint_token_redraws_a_dash_led_token(monkeypatch):
    draws = iter(["-dashFirst", "-dashAgain", "letterFirst"])
    monkeypatch.setattr(tokens.secrets, "token_urlsafe", lambda n: next(draws))
    assert tokens.mint_token() == "letterFirst"


@pytest.mark.parametrize("_", range(2000))
def test_mint_token_never_starts_with_a_dash(_):
    tok = tokens.mint_token()
    assert not tok.startswith("-")
    assert len(tok) == 43  # 32 bytes, base64url, unpadded


def test_minted_token_parses_as_a_separate_argument():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-token")
    for _ in range(500):
        tok = tokens.mint_token()
        assert parser.parse_args(["--api-token", tok]).api_token == tok


def test_dash_led_value_needs_the_equals_form():
    """Pins the argparse behaviour the workflow and docs work around."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-token")
    with pytest.raises(SystemExit):
        parser.parse_args(["--api-token", "-dashFirst"])
    assert parser.parse_args(["--api-token=-dashFirst"]).api_token == "-dashFirst"


# A printed shell hint, not a minting site: the token it makes goes into the
# QUIRK_API_TOKEN environment variable, never after an argparse flag.
_HINT_ONLY = {"quirk/dashboard/server.py"}


def test_no_production_code_mints_tokens_directly():
    offenders = [
        f"{p.relative_to(REPO_ROOT)}:{n}"
        for p in sorted((REPO_ROOT / "quirk").rglob("*.py"))
        if p.name != "tokens.py"
        and p.relative_to(REPO_ROOT).as_posix() not in _HINT_ONLY
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"\bsecrets\.token_urlsafe\(", line)
    ]
    assert not offenders, (
        "Mint bearer tokens with quirk.tokens.mint_token(), which never returns "
        "a dash-led value:\n  " + "\n  ".join(offenders)
    )
