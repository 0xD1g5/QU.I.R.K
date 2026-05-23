"""quirk analyze-token — decode and classify a bearer/JWT token (Phase 94 TOKEN-01/TOKEN-03).

Passive analysis only: no signature verification, no network requests, no DB writes.
The raw token value is never persisted or echoed to stdout/logs.

Input forms (Phase 93 reference-not-secret model):
  positional   — quirk analyze-token <token>
                 WARNING: the positional form may expose the token in shell history /
                 process table. Prefer @file or stdin for sensitive tokens.
  @file        — quirk analyze-token @/path/to/token.txt   (reads first non-empty line)
  stdin        — echo <token> | quirk analyze-token -      (reads from stdin)

Exit codes:
  0  — analysis complete; no CRITICAL findings
  1  — CRITICAL finding (alg:none or other critical issue)
  2  — usage error

Threat mitigations:
  T-94-01: alg:none detected via header["alg"].lower()=="none" (not raw string search)
  T-94-02: token never printed; exceptions wrapped in safe_str()
  T-94-04: algorithms=[alg] always passed to jwt.decode() (PyJWT>=2.4 requirement)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any

import jwt
import jwt.exceptions

from quirk.cbom.classifier import classify_algorithm, quantum_safety_label
from quirk.util.safe_exc import safe_str


# ---------------------------------------------------------------------------
# Token input resolution — reuses Phase 93 reference-not-secret model
# ---------------------------------------------------------------------------

def _resolve_token_input(raw: str) -> str:
    """Resolve @file or stdin ('-') references to the actual token string.

    Returns the stripped token text. Never logs the token value.
    """
    if raw == "-":
        # Read from stdin
        return sys.stdin.read().strip()
    if raw.startswith("@"):
        path = raw[1:]
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        return line
        except OSError as exc:
            sys.exit(f"ERROR: cannot read token file: {safe_str(exc)}")
        sys.exit("ERROR: token file is empty")
    return raw.strip()


# ---------------------------------------------------------------------------
# JWT decode helpers
# ---------------------------------------------------------------------------

def _decode_token(raw: str) -> dict[str, Any]:
    """Decode a JWT without signature verification.

    Returns a dict with keys: header, claims, alg, is_alg_none, expired, exp,
    nist_level, quantum_safety, classical_level.

    Raises jwt.exceptions.DecodeError for opaque (non-JWT) tokens.

    T-94-04: always passes algorithms=[alg] per PyJWT>=2.4 hardening.
    T-94-01: detects alg:none via header dict key, not raw string search.
    """
    header = jwt.get_unverified_header(raw)
    alg = header.get("alg") or ""

    # T-94-04: always provide algorithms list — never algorithms=None
    # Per RESEARCH Pitfall 1: use ["none"] when alg is falsy.
    alg_list = [alg] if alg else ["none"]

    try:
        claims = jwt.decode(
            raw,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=alg_list,
        )
    except jwt.exceptions.DecodeError:
        # Claims decode failed but header was valid — treat claims as empty
        claims = {}

    # T-94-01: case-insensitive alg:none check on the decoded header dict value
    is_alg_none = alg.lower() == "none"
    # WR-05: a JWT with NO alg header is as forgeable as alg:none — treat as critical.
    is_alg_missing = not alg

    # Expiry
    exp = claims.get("exp")
    expired = False
    if exp is not None:
        try:
            expired = (
                datetime.fromtimestamp(int(exp), tz=timezone.utc)
                < datetime.now(timezone.utc)
            )
        except (ValueError, OSError):
            expired = False

    # Quantum-safety classification via existing classifier
    primitive, nist_level, classical_level = classify_algorithm(alg.lower())
    qs_label = quantum_safety_label(nist_level)

    return {
        "alg": alg if alg else "UNKNOWN",
        "is_alg_none": is_alg_none,
        "is_alg_missing": is_alg_missing,
        "expired": expired,
        "exp": exp,
        "nist_level": nist_level,
        "quantum_safety": qs_label,
        "classical_level": classical_level,
        "header": header,
        "claims": claims,
    }


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def _format_human(info: dict[str, Any]) -> str:
    """Format token analysis as human-readable text.

    The raw token value is never included in the output (T-94-02).
    """
    lines = [
        "--- quirk analyze-token ---",
        f"  Algorithm    : {info['alg']}",
        f"  alg:none     : {'YES — CRITICAL: unsigned JWT, trivially forgeable' if info['is_alg_none'] else 'no'}",
        f"  Quantum safety: {info['quantum_safety']}",
        f"  NIST PQC level: {info['nist_level']}",
        f"  Expired      : {'yes' if info['expired'] else 'no'}",
    ]
    if info.get("exp") is not None:
        try:
            exp_dt = datetime.fromtimestamp(int(info["exp"]), tz=timezone.utc)
            lines.append(f"  Expiry (UTC) : {exp_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        except (ValueError, OSError):
            lines.append(f"  Expiry       : <unparseable>")
    lines.append("---------------------------")
    return "\n".join(lines)


def _format_json(info: dict[str, Any]) -> str:
    """Format token analysis as JSON (T-94-02: never includes the raw token)."""
    output = {
        "alg": info["alg"],
        "is_alg_none": info["is_alg_none"],
        "is_alg_missing": info["is_alg_missing"],
        "expired": info["expired"],
        "exp": info["exp"],
        "nist_level": info["nist_level"],
        "quantum_safety": info["quantum_safety"],
    }
    return json.dumps(output)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_analyze_token(argv: list[str]) -> None:
    """quirk analyze-token entry point. argv is sys.argv[2:] (after the subcommand name).

    Exit codes:
      0 — success, no CRITICAL findings
      1 — CRITICAL finding (alg:none)
      2 — usage error (argparse)
    """
    parser = argparse.ArgumentParser(
        prog="quirk analyze-token",
        description=(
            "Decode and classify a bearer/JWT token. "
            "Passive analysis — no signature verification, no network requests, no DB writes. "
            "Token value is never echoed or persisted."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "INPUT FORMS:\n"
            "  positional   quirk analyze-token <token>\n"
            "               WARNING: positional form may expose token in shell history.\n"
            "               Prefer @file or stdin for sensitive tokens.\n"
            "  @file        quirk analyze-token @/path/to/token.txt\n"
            "  stdin        echo <token> | quirk analyze-token -\n"
        ),
    )
    parser.add_argument(
        "token",
        nargs="?",
        metavar="TOKEN|@FILE|-",
        help="JWT or bearer token to analyze. Use @file to read from a file, '-' for stdin.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit machine-readable JSON instead of human-readable text.",
    )

    args = parser.parse_args(argv)

    # Resolve token input
    if args.token is None:
        # No positional — try stdin
        if sys.stdin.isatty():
            parser.error("No token provided. Pass a token, @file, or pipe via stdin.")
        raw_token = _resolve_token_input("-")
    else:
        raw_token = _resolve_token_input(args.token)

    if not raw_token:
        parser.error("Token is empty.")

    # Attempt JWT decode
    try:
        info = _decode_token(raw_token)
    except jwt.exceptions.DecodeError:
        # Opaque token — not a JWT
        print("INFO: token does not appear to be a JWT (opaque token) — cannot classify")
        sys.exit(0)
    except Exception as exc:
        # T-94-02: wrap exception in safe_str() — never log raw token
        print(f"ERROR: token analysis failed: {safe_str(exc)}")
        sys.exit(2)

    # Output results
    if args.json_output:
        print(_format_json(info))
    else:
        print(_format_human(info))

    # T-94-01: alg:none → CRITICAL + exit 1. WR-05: a missing alg header is equally forgeable.
    if info["is_alg_none"]:
        if not args.json_output:
            print(
                "CRITICAL: alg:none detected — this JWT is unsigned and trivially "
                "forgeable. Any party can craft arbitrary claims."
            )
        sys.exit(1)
    if info["is_alg_missing"]:
        if not args.json_output:
            print(
                "CRITICAL: no 'alg' header present — this JWT declares no signing "
                "algorithm and is as forgeable as an alg:none token."
            )
        sys.exit(1)

    sys.exit(0)
