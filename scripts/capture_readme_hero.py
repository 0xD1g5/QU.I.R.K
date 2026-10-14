"""Scripted, reproducible README hero capture (Phase 225 D-10).

Why this exists: the UAT-85-08 hand capture depended on a chaos-lab profile being
up and was never reproducible; the dashboard gauges drew mirrored for six months
and nobody noticed. This script snapshots the canonical ``./quirk-output/quirk.db``
(sqlite3 backup API, read-only source) into a temp dir, starts a loopback uvicorn
against that COPY, opens the executive page in the dark theme at 2x DPR,
guards against capturing the login form / unbuilt placeholder, corroborates by
geometry that each gauge is NOT mirrored, and writes a PNG.

Run: ``.venv/bin/python -m scripts.capture_readme_hero [--out PATH] ...``

Local-only tooling (Playwright is a ``dashboard`` extra). The operator's visual
confirmation remains the acceptance; the arc-reach check is corroboration only.
The canonical DB is never served (225-REVIEW CR-02: the app writes at startup and
runs init_db migrations per request), so it is not mutated. As corroboration, the
sha256 of the DB and any -wal/-journal sidecar is compared before and after, on
EVERY exit path (try/finally), and a mismatch fails loudly with DB_MUTATED.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import socket
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from quirk.dashboard.api.routes.pdf import IMAGE_SETTLE_PREDICATE

REPO_ROOT = Path(__file__).resolve().parent.parent

_PLACEHOLDER_SIGNATURE = "npm run build"
_SIDEBAR_NAV = 'nav[aria-label="Dashboard navigation"]'
_LOGIN_FORM = 'form[aria-label="Dashboard login"]'
_BRAND_NAME = "QU.I.R.K."
_GAUGES_CARD = "div.flex.flex-wrap.justify-around.gap-7"
_MAX_PNG_BYTES = 1_048_576
_REACH_TOLERANCE = 0.02
_EXPECTED_GAUGES = 7
_SUBSCORE_ORDER = (
    "hygiene", "modern_tls", "identity_trust",
    "agility_signals", "data_at_rest", "data_in_motion",
)

_REACH_JS = """(sel) => {
  const card = document.querySelector(sel);
  if (!card) return null;
  return Array.from(card.querySelectorAll('svg')).map(svg => {
    const p = svg.querySelectorAll('path');
    if (p.length < 1) return null;
    const n = d => d.match(/-?\\d+(\\.\\d+)?/g).map(Number);
    const t = n(p[0].getAttribute('d'));
    const sx = t[0], r = t[2];
    if (p.length < 2) return {label: svg.closest('div.flex-col')?.innerText || '', reach: 0};
    const f = n(p[1].getAttribute('d'));
    return {label: (svg.closest('div.flex-col')?.innerText || '').replace(/\\s+/g, ' ').trim(),
            reach: (f[f.length - 2] - sx) / (2 * r)};
  }).filter(Boolean);
}"""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


_DB_SIDECARS = ("", "-wal", "-journal")


def db_fingerprint(db: Path) -> dict[str, str | None]:
    """sha256 of the DB file and each -wal/-journal sidecar (None if absent).

    -shm is deliberately excluded: it is a shared-memory index that any reader
    (including a concurrent ``quirk serve``) rewrites without changing content.
    """
    out: dict[str, str | None] = {}
    for suffix in _DB_SIDECARS:
        p = Path(str(db) + suffix)
        out[p.name] = _sha256(p) if p.exists() else None
    return out


def snapshot_db(db: Path, dest_dir: Path) -> Path:
    """Consistent copy of ``db`` into ``dest_dir`` via the sqlite3 backup API.

    The source is opened ``mode=ro`` so this process can never write to the
    canonical DB (no checkpoint, no journal, no schema migration).
    """
    snap = Path(dest_dir) / "quirk.db"
    src = sqlite3.connect(f"{db.as_uri()}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(snap))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return snap


def stamp_from_scanned_at(scanned_at: str) -> str:
    """'2026-09-28T13:21:39...' -> '20260928-132139' (the artifact filename stamp)."""
    ymd, hms = scanned_at.split("T", 1)
    return ymd.replace("-", "") + "-" + hms[:8].replace(":", "")


def build_scoped_config(stamp: str, workdir: str, evidence: dict) -> str:
    """Write a config whose output.directory holds ONLY the canonical scan's real
    report artifacts (symlinked, never regenerated), so the executive header's
    "Report from scan" refers to the scan the dashboard is displaying rather than
    a newer unrelated run-stats file in quirk-output/. Returns the config path.
    """
    import yaml

    src_dir = REPO_ROOT / "quirk-output"
    out_dir = Path(workdir) / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    linked = []
    for f in sorted(src_dir.glob(f"*-{stamp}.*")):
        (out_dir / f.name).symlink_to(f)
        linked.append(f.name)
    if not any(n.startswith("report-") and n.endswith(".html") for n in linked) or not any(
        n.startswith("run-stats-") for n in linked
    ):
        raise SystemExit(
            f"NO_REPORT_ARTIFACTS: quirk-output/ has no report-{stamp}.html + "
            f"run-stats-{stamp}.json for the canonical scan; generate them first."
        )
    cfg = yaml.safe_load((REPO_ROOT / "config.yaml").read_text())
    cfg.setdefault("output", {})["directory"] = str(out_dir)
    cfg_path = Path(workdir) / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    evidence["report_artifacts"] = {"stamp": stamp, "files": linked}
    return str(cfg_path)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read()


@contextlib.contextmanager
def serve_dashboard(db_path: Path, config_path: str | None = None):
    """Background a loopback uvicorn serving the dashboard app; yield its origin.

    Its scratch dir is a TemporaryDirectory removed on exit (225-REVIEW WR-02).
    """
    with tempfile.TemporaryDirectory(prefix="quirk-hero-") as tmp:
        with _serve_dashboard(db_path, config_path, tmp) as origin:
            yield origin


@contextlib.contextmanager
def _serve_dashboard(db_path: Path, config_path: str | None, tmp: str):
    port = _free_port()
    env = dict(os.environ)
    env["QUIRK_DB_PATH"] = str(db_path)
    env["QUIRK_SERVE_PORT"] = str(port)
    # Auth passthrough only when BOTH token sources resolve empty.
    env.pop("QUIRK_API_TOKEN", None)
    env["QUIRK_CONFIG_PATH"] = config_path or os.path.join(tmp, "absent", "config.yaml")
    # WR-01: server output goes to a log file, never an unread PIPE (a full
    # pipe buffer blocks uvicorn's event loop mid-capture).
    log_path = Path(tmp) / "uvicorn.log"
    log_fh = open(log_path, "wb")
    # close_fds=False and no cwd: avoids the macOS fork() SIGSEGV path.
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "quirk.dashboard.api.app:app",
             "--host", "127.0.0.1", "--port", str(port)],
            env=env, stdout=log_fh, stderr=subprocess.STDOUT,
            close_fds=False,
        )
    except BaseException:
        log_fh.close()
        raise
    origin = f"http://127.0.0.1:{port}"
    try:
        deadline = time.time() + 30
        ready = False
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                if urllib.request.urlopen(f"{origin}/api/health", timeout=2).status == 200:
                    ready = True
                    break
            except OSError:
                pass
            time.sleep(1)
        if not ready:
            proc.kill()
            with contextlib.suppress(Exception):
                proc.wait(timeout=10)
            raise SystemExit(
                f"SERVER_NOT_READY: uvicorn did not answer {origin}/api/health in 30s "
                f"(exit={proc.returncode}); log tail:\n" + _log_tail(log_fh, log_path)
            )
        yield origin
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                with contextlib.suppress(Exception):
                    proc.wait(timeout=10)
        log_fh.close()


def _log_tail(log_fh, log_path: Path, limit: int = 8192) -> str:
    with contextlib.suppress(Exception):
        log_fh.flush()
    try:
        data = log_path.read_bytes()
    except OSError as exc:
        return f"<log unreadable: {exc}>"
    return data[-limit:].decode("utf-8", "replace")


def assert_spa_mounted(page) -> None:
    """Abort (named) if the page is the placeholder, the login form, or an empty shell."""
    if _PLACEHOLDER_SIGNATURE in page.content():
        raise SystemExit(
            "PLACEHOLDER_PAGE: served the unbuilt-dashboard placeholder; run `npm run build`."
        )
    root_children = page.evaluate(
        "() => { const r = document.getElementById('root'); return r ? r.children.length : -1; }"
    )
    if root_children <= 0:
        raise SystemExit(f"SPA_NOT_MOUNTED: #root has {root_children} children.")
    if page.locator(_LOGIN_FORM).count() != 0:
        raise SystemExit(
            "LOGIN_FORM: landed on the login form; an API token resolved in the served process."
        )
    if page.locator(_SIDEBAR_NAV).count() == 0:
        raise SystemExit("NO_SIDEBAR_NAV: authenticated shell sidebar nav is absent.")
    logo = page.locator("aside").get_by_role("img", name=_BRAND_NAME).first
    if not logo.is_visible():
        raise SystemExit("NO_BRAND_LOGO: sidebar brand logo not visible (viewport < 1024?).")


def _expected_reach(score: float, max_value: float) -> float:
    return (1 - math.cos(math.pi * (score / max_value))) / 2


def _png_size(path: Path) -> tuple[int, int]:
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("BAD_PNG: output is not a PNG.")
    return struct.unpack(">II", head[16:24])


def capture(args, origin: str, scan: dict, evidence: dict) -> None:
    from playwright.sync_api import sync_playwright  # lazy: `dashboard` extra

    W, H = args.width, args.height
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            ctx = browser.new_context(
                viewport={"width": W, "height": H},
                device_scale_factor=2,
                color_scheme="dark",
                reduced_motion="reduce",
            )
            ctx.add_init_script("window.localStorage.setItem('quirk-ui-theme', 'dark')")
            page = ctx.new_page()
            page.goto(origin + "/", wait_until="networkidle")
            page.wait_for_selector("main h1")
            assert_spa_mounted(page)
            page.wait_for_function(
                "(sel) => document.querySelectorAll(sel + ' svg').length >= 7",
                arg=_GAUGES_CARD,
            )
            page.evaluate("() => document.fonts.ready")
            page.wait_for_function(IMAGE_SETTLE_PREDICATE)
            page.wait_for_timeout(500)

            rows = page.evaluate(_REACH_JS, _GAUGES_CARD)
            if not rows or len(rows) != _EXPECTED_GAUGES:
                raise SystemExit(
                    f"GAUGE_COUNT: expected {_EXPECTED_GAUGES} gauges, got "
                    f"{0 if not rows else len(rows)}."
                )
            subs = scan["score"]["subscores"]
            expected_inputs = [(scan["score"]["score"], 100)] + [
                (subs[k], 25) for k in _SUBSCORE_ORDER
            ]
            table = []
            bad = []
            for row, (val, mx) in zip(rows, expected_inputs):
                exp = _expected_reach(float(val), mx)
                delta = row["reach"] - exp
                table.append({
                    "label": row["label"], "value": val, "max": mx,
                    "reach": round(row["reach"], 4),
                    "expected": round(exp, 4), "delta": round(delta, 4),
                })
                if abs(delta) > _REACH_TOLERANCE:
                    bad.append(table[-1])
            evidence["reach"] = table
            if bad:
                raise SystemExit(f"GAUGE_MIRRORED: arc reach differs from expected: {bad}")

            # Issue 4: dismiss the regression alert (a real, dismissible control)
            # BEFORE measuring, since removing it shifts layout.
            alert = page.get_by_role("alert").filter(has_text="finding(s) detected")
            if alert.count() > 0:
                btn = alert.get_by_role("button", name="Dismiss regression alert")
                if btn.count() != 1:
                    raise SystemExit("ALERT_NOT_DISMISSIBLE: regression banner has no dismiss button.")
                btn.click()
                try:
                    alert.wait_for(state="detached", timeout=5000)
                except Exception:
                    raise SystemExit("ALERT_NOT_DISMISSED: banner still present after clicking dismiss.")
                evidence["alert_dismissed"] = True
            else:
                evidence["alert_dismissed"] = False

            hdr = page.get_by_text("Report from scan:")
            if hdr.count() == 0:
                raise SystemExit("NO_REPORT_HEADER: executive header does not read 'Report from scan: ...'.")
            evidence["report_header"] = hdr.first.inner_text()

            # Issue 2: all 7 gauges must share one row.
            tops = page.evaluate(
                "(sel) => Array.from(document.querySelector(sel).querySelectorAll('svg'))"
                ".map(s => Math.round(s.getBoundingClientRect().top))",
                _GAUGES_CARD,
            )
            evidence["gauge_tops"] = tops
            evidence["gauges_one_row"] = len(set(tops)) == 1
            if len(set(tops)) != 1 and not args.allow_wrapped_gauges:
                raise SystemExit(f"GAUGES_WRAPPED: gauges are not on one row (tops={tops}); raise --width.")

            # Issue 1: the sidebar is viewport-height, so grow the viewport to the
            # clip bottom and re-measure until stable (layout can shift).
            def measure():
                b = page.locator(_GAUGES_CARD).bounding_box()
                return math.ceil(b["y"] + page.evaluate("() => window.scrollY") + b["height"]), b
            def nav_deficit():
                return page.evaluate(
                    "(sel) => { const n = document.querySelector(sel); return Math.max(0, n.scrollHeight - n.clientHeight); }",
                    _SIDEBAR_NAV,
                )
            vh = H
            for _ in range(6):
                bottom, box = measure()
                need = max(bottom + args.pad, vh + nav_deficit())
                if need == vh:
                    break
                vh = need
                page.set_viewport_size({"width": W, "height": vh})
                page.wait_for_timeout(300)
            bottom, box = measure()
            card_bottom = box["y"] + page.evaluate("() => window.scrollY") + box["height"]
            # Clip is the full viewport: the sidebar is viewport-tall, so the card may
            # end above the viewport bottom once the sidebar needs more height.
            clip = {"x": 0, "y": 0, "width": W, "height": vh}
            nav_clipped = page.evaluate(
                "(sel) => { const n = document.querySelector(sel); return n.scrollHeight > n.clientHeight + 1; }",
                _SIDEBAR_NAV,
            )
            evidence["viewport"] = {"width": W, "height": vh}
            evidence["sidebar_nav_overflowing"] = nav_clipped
            if nav_clipped:
                raise SystemExit("SIDEBAR_NAV_CLIPPED: nav list still scrolls at this viewport height.")
            evidence["clip"] = clip
            evidence["card_bottom"] = card_bottom
            page.screenshot(path=str(out), clip=clip, animations="disabled")
        finally:
            browser.close()

    pw_, ph_ = _png_size(out)
    nbytes = out.stat().st_size
    evidence["png"] = {"width": pw_, "height": ph_, "bytes": nbytes, "path": str(out)}
    if nbytes >= _MAX_PNG_BYTES:
        raise SystemExit(f"PNG_TOO_LARGE: {nbytes} >= {_MAX_PNG_BYTES} bytes.")
    if ph_ != 2 * clip["height"]:
        raise SystemExit(f"PNG_TRUNCATED: png_height {ph_} != 2 * clip.height {clip['height']}.")
    if not card_bottom <= clip["y"] + clip["height"]:
        raise SystemExit("CARD_CUT_OFF: gauges card bottom lies outside the clip.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--width", type=int, default=1680)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--out", default="docs/images/dashboard-hero.png")
    ap.add_argument("--db", default=str(REPO_ROOT / "quirk-output" / "quirk.db"))
    ap.add_argument("--allow-wrapped-gauges", action="store_true",
                    help="Do not fail when the 7 gauges wrap (layout is max-w-[1200px]; width cannot fix it).")
    ap.add_argument("--pad", type=int, default=24)
    ap.add_argument("--evidence-json", default=None)
    args = ap.parse_args(argv)

    if args.width < 1024:
        raise SystemExit("BAD_WIDTH: --width must be >= 1024 (sidebar logo is `hidden lg:block`).")
    db = Path(args.db).resolve()
    if not db.is_file():
        raise SystemExit(f"DB_MISSING: {db} does not exist; refusing to start.")

    before = db_fingerprint(db)
    evidence: dict = {"db": str(db), "db_sha256_before": before,
                      "viewport": {"width": args.width, "height": args.height}}
    mutated = False
    try:
        with tempfile.TemporaryDirectory(prefix="quirk-hero-db-") as snapdir:
            # CR-02: serve a snapshot, never the canonical file.
            served = snapshot_db(db, Path(snapdir))
            evidence["served_db"] = "temp snapshot (sqlite3 backup API, ro source)"
            _run(args, served, evidence)
    finally:
        after = db_fingerprint(db)
        evidence["db_sha256_after"] = after
        if before != after:
            mutated = True
            print(f"DB_MUTATED: canonical DB fingerprint changed during capture: "
                  f"before={before} after={after}", file=sys.stderr)
    text = json.dumps(evidence, indent=2, default=str)
    print(text)
    if args.evidence_json:
        Path(args.evidence_json).write_text(text + "\n")
    return 1 if mutated else 0


def _run(args, db: Path, evidence: dict) -> None:
    """Probe the served snapshot for the canonical scan, then capture."""
    # Resolve the canonical scan first (throwaway server) so the real server can be
    # started with a report dir scoped to that scan's artifacts.
    with serve_dashboard(db) as probe_origin:
        meta0 = json.loads(_get(probe_origin + "/api/scan/latest")).get("meta") or {}
    scanned_at = meta0.get("scanned_at")
    if not scanned_at:
        raise SystemExit("NO_SCAN_META: /api/scan/latest meta.scanned_at is missing.")
    # WR-02: the scoped config.yaml copy (which may carry connector credentials)
    # and the report symlinks live only for the duration of the capture.
    with tempfile.TemporaryDirectory(prefix="quirk-hero-reports-") as workdir:
        cfg_path = build_scoped_config(
            stamp_from_scanned_at(scanned_at), workdir, evidence)
        _capture_with_server(args, db, cfg_path, evidence)


def _capture_with_server(args, db: Path, cfg_path: str, evidence: dict) -> None:
    with serve_dashboard(db, cfg_path) as origin:
        scan = json.loads(_get(origin + "/api/scan/latest"))
        score = scan.get("score") or {}
        m_ = scan.get("meta") or {}
        evidence["scan"] = {"id": m_.get("scan_id"), "timestamp": m_.get("scanned_at")}
        evidence["score"] = score
        evidence["meta"] = scan.get("meta")
        html = _get(origin + "/").decode("utf-8", "replace")
        import re
        m = re.search(r"assets/(index-[A-Za-z0-9_-]+\.js)", html)
        if not m:
            raise SystemExit("NO_BUNDLE: served index.html references no assets/index-*.js.")
        evidence["bundle"] = m.group(1)
        if not (REPO_ROOT / "quirk" / "dashboard" / "static" / "assets" / m.group(1)).is_file():
            raise SystemExit(f"STATIC_MISSING: {m.group(1)} not in quirk/dashboard/static/assets.")
        try:
            capture(args, origin, {"score": score}, evidence)
        finally:
            pass

if __name__ == "__main__":
    raise SystemExit(main())
