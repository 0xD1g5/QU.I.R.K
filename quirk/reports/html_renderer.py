"""Jinja2-based standalone HTML report renderer for QU.I.R.K. (Phase 7, D-08 to D-12)."""
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from quirk.util.safe_exc import safe_str
from quirk.util.sanitize import sanitize_scanner_text


# Phase 78 / HARDEN-04: PDF metadata constants. Title flows from HTML <title>;
# Author is injected post-render via pypdf because Chromium's print-to-PDF does
# not honor <meta name="author">.
PDF_TITLE = "QU.I.R.K. Cryptographic Readiness Report"
PDF_AUTHOR = "QU.I.R.K. Scanner"


def _score_band(total: int) -> str:
    if total >= 85:
        return "EXCELLENT"
    if total >= 70:
        return "GOOD"
    if total >= 55:
        return "MODERATE"
    if total >= 35:
        return "FAIR"
    return "POOR"


def _score_color(band: str) -> str:
    return {
        "EXCELLENT": "#4caf50",
        "GOOD": "#66bb6a",
        "MODERATE": "#f9a825",
        "FAIR": "#f57c00",
        "POOR": "#e53935",
    }.get(band, "#aaaaaa")


def _collect_algorithm_names(endpoints: List[Any]) -> List[str]:
    """Derive the unique algorithm names observed in this scan from endpoints.

    Sources: cipher_suite, cert_pubkey_alg, tls_supported_ciphers_sample.
    Returns a sorted list of unique non-empty algorithm/suite strings.
    """
    names: set = set()
    for ep in endpoints or []:
        for attr in ("cipher_suite", "cert_pubkey_alg"):
            val = getattr(ep, attr, "") or ""
            if isinstance(val, str) and val.strip():
                names.add(val.strip())
        sample = getattr(ep, "tls_supported_ciphers_sample", "") or ""
        if isinstance(sample, str) and sample.strip():
            for tok in sample.split(","):
                tok = tok.strip()
                if tok:
                    names.add(tok)
    return sorted(names)


def build_algorithm_inventory(endpoints: List[Any]) -> List[Dict[str, Any]]:
    """Build the `algorithms` template context (Phase 81 / CMVP-06).

    Each row carries: name, nist_level, fips_status, cmvp_coverage.

    `cmvp_coverage` is a comma-joined list of CMVP module names that cover the
    algorithm, or None for empty matches (the template renders the literal
    "Not in CMVP catalog" in that case).

    Implementation notes:
    - `quirk.compliance.cmvp.coverage_for_algorithm` is imported LAZILY (inside
      this function body) so module-import-time isn't broken if Plan 81-02 has
      not yet committed the cmvp module.
    - `quirk.cbom.classifier.classify_algorithm` provides the NIST level used
      by the existing _fips_status helper; both imports are deferred to keep
      module-load cost low for non-HTML reporting paths.
    - NEVER emits any `certified` boolean — only informational coverage strings
      (v4.10-D-01 invariant).
    """
    rows: List[Dict[str, Any]] = []

    # Lazy imports — Plan 81-02 lands quirk/compliance/cmvp.py concurrently;
    # quirk/cbom/builder.py + classifier.py are foundational and always present
    # but we defer to keep this helper cheap to import.
    try:
        from quirk.compliance.cmvp import coverage_for_algorithm
    except ImportError:
        # Plan 81-02 hasn't committed yet — render with empty coverage so the
        # template gracefully falls back to "Not in CMVP catalog" for every row.
        def coverage_for_algorithm(_name: str):  # type: ignore[no-redef]
            return []

    try:
        from quirk.cbom.classifier import classify_algorithm
        from quirk.cbom.builder import _fips_status
    except ImportError:
        def classify_algorithm(_name: str):  # type: ignore[no-redef]
            return (None, None, None)

        def _fips_status(_lvl):  # type: ignore[no-redef]
            return "non-approved"

    for name in _collect_algorithm_names(endpoints):
        try:
            _, nist_level, _ = classify_algorithm(name)
        except Exception:
            nist_level = None
        fips_status = _fips_status(nist_level) if nist_level is not None or True else "non-approved"
        try:
            coverage = coverage_for_algorithm(name) or []
        except Exception:
            coverage = []
        module_names = [
            (m.get("name") if isinstance(m, dict) else str(m))
            for m in coverage
            if (isinstance(m, dict) and m.get("name")) or (not isinstance(m, dict))
        ]
        cmvp_coverage = ", ".join(module_names) if module_names else None
        rows.append({
            "name": name,
            "nist_level": nist_level if nist_level is not None else "—",
            "fips_status": fips_status,
            "cmvp_coverage": cmvp_coverage,
        })
    return rows


def _severity_color(severity: str) -> str:
    return {
        "CRITICAL": "#e53935",
        "HIGH": "#f57c00",
        "MEDIUM": "#f9a825",
        "LOW": "#5c9cff",
        "INFO": "#888888",
    }.get(str(severity).upper(), "#888888")


# Use FileSystemLoader so templates are found without pip reinstall (RESEARCH.md Pattern 2).
# This works for both development installs and editable installs without package data rebuild.
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def render_html_report(
    path: str,
    cfg: Any,
    endpoints: List[Any],
    findings: List[Dict[str, Any]],
    score: Dict[str, Any],
    conf: Dict[str, Any],
    roadmap_items: List[Dict[str, Any]],
) -> None:
    """Render a self-contained HTML report to *path*.

    All CSS is inlined. No CDN references. Works offline (D-08).
    """
    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "j2"]),
    )
    env.filters["sanitize"] = sanitize_scanner_text
    template = env.get_template("report.html.j2")

    total_score = score.get("total", 0)
    band = _score_band(total_score)

    # Severity counts
    sev_counts: Dict[str, int] = {}
    for f in (findings or []):
        # Phase 45 / D-07: coverage_gap findings are advisory-only and MUST NOT
        # inflate severity counts in the executive summary.
        if f.get("category") == "coverage_gap":
            continue
        s = str(f.get("severity", "INFO")).upper()
        sev_counts[s] = sev_counts.get(s, 0) + 1

    # Roadmap sections
    # Phase 77 D-13 / cbom-intel-reports/IN-07: C-7 verification — both branches
    # (timeframe match and phase match) are reachable; closes IN-07 as
    # audit-flip-only. See tests/test_html_renderer_roadmap_section.py for the
    # mutation evidence.
    def roadmap_section(tf: str) -> List[Dict]:
        return [r for r in (roadmap_items or []) if r.get("timeframe") == tf or r.get("phase") == tf]

    # Phase 81 / CMVP-06: build the Algorithm Inventory `algorithms` context.
    algorithms = build_algorithm_inventory(endpoints or [])

    html = template.render(
        org_name=getattr(getattr(cfg, "assessment", None), "name", "Unknown"),
        report_owner=getattr(getattr(cfg, "assessment", None), "report_owner", ""),
        data_classification=getattr(getattr(cfg, "assessment", None), "data_classification", "CONFIDENTIAL"),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        total_score=total_score,
        score_band=band,
        score_color=_score_color(band),
        confidence=conf.get("confidence", 0),
        sev_counts=sev_counts,
        drivers=score.get("drivers", []),
        findings=findings or [],
        endpoints=endpoints or [],
        algorithms=algorithms,
        roadmap_now=roadmap_section("NOW"),
        roadmap_next=roadmap_section("NEXT"),
        roadmap_later=roadmap_section("LATER"),
        subscores=score.get("subscores", {}),  # D-07 / SCORE-XPARENCY-01 — int values, no sanitize needed
        severity_color=_severity_color,
    )
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def _inject_pdf_metadata(pdf_path: str) -> None:
    """Post-process a rendered PDF to inject /Title and /Author metadata.

    Phase 78 / HARDEN-04: Chromium's headless print-to-PDF embeds <title> as
    /Title but ignores <meta name="author">. We open the freshly rendered PDF
    with pypdf, copy pages into a new writer, set both metadata fields to the
    locked module-level constants, and overwrite the file. This preserves the
    locked Playwright context (JS disabled, offline, CSP enforced) and adds
    Author as a deterministic post-render step.

    pypdf is imported lazily so that `pip install quirk-scanner` (without the
    `[dashboard]` extra) does not break the always-imported report module
    chain — this function is only ever called from render_pdf_report, which
    short-circuits on missing Playwright.
    """
    import pypdf
    reader = pypdf.PdfReader(pdf_path)
    writer = pypdf.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({"/Title": PDF_TITLE, "/Author": PDF_AUTHOR})
    with open(pdf_path, "wb") as f:
        writer.write(f)


def render_pdf_report(html_path: str, pdf_path: str) -> bool:
    """Render html_path to pdf_path using Playwright headless Chromium.

    Returns True on success, False if Playwright is unavailable (graceful degradation, D-11).
    """
    try:
        from playwright.sync_api import sync_playwright
        from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
    except ImportError:
        return False
    browser = None
    context = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            # Phase 78 / HARDEN-04: explicit deny on JS, network, and CSP bypass.
            context = browser.new_context(
                java_script_enabled=False,
                offline=True,
                bypass_csp=False,
            )
            page = context.new_page()
            page.goto(f"file://{os.path.abspath(html_path)}")
            page.pdf(
                path=pdf_path,
                format="A4",
                margin={"top": "15mm", "bottom": "15mm", "left": "12mm", "right": "12mm"},
                print_background=True,
                display_header_footer=False,
            )
        # Phase 78 / HARDEN-04: post-render metadata injection. Chromium's
        # print-to-PDF honors <title> but not <meta name="author">, so we
        # inject /Author (and re-affirm /Title) via pypdf.
        _inject_pdf_metadata(pdf_path)
        return True
    except (PlaywrightError, PlaywrightTimeoutError, OSError, RuntimeError) as e:
        print(
            f"PDF generation failed: {safe_str(e)}; scan complete, HTML report at {html_path}",
            file=sys.stderr,
        )
        return False
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
