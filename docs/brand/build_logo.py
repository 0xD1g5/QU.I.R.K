#!/usr/bin/env python3
"""Generate the QU.I.R.K. logo set (SVG) from first principles.

Every shape is computed, not hand-drawn, so the PQC easter eggs are exact:

  * The Q ring is a 256-gon whose vertices sit at angles (2k+1)*pi/256 --
    the 256 roots of X^256 + 1, the polynomial ring R_q shared by
    ML-KEM (FIPS 203) and ML-DSA (FIPS 204).
  * The ring is two 128-vertex halves joined by the tail: a hybrid
    key exchange (X25519 + ML-KEM-768) combined into one secret.
  * Inside the counter is a 3x3 sheared lattice: the k x k public
    matrix A of ML-KEM-768 (k = 3), drawn in a skewed "bad" basis.
  * The centre point is pushed off its lattice node by a small
    vector e: Learning With Errors, b = As + e. The quirk is the error.
  * INK  #0D0124 -> 0x0D01 = 3329    = ML-KEM modulus q.
  * SIG  #7FE001 -> 0x7FE001 = 8380417 = ML-DSA modulus q.

Run:  python3 docs/brand/build_logo.py   (stdlib only; writes into docs/brand/)
"""
from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).resolve().parent

INK = "#0D0124"    # 0x0D01 = 3329, ML-KEM q
SIG = "#7FE001"    # 0x7FE001 = 8380417, ML-DSA q
PAPER = "#F4F5F9"

assert int(INK[1:5], 16) == 3329
assert int(SIG[1:], 16) == 8380417

N = 256                       # degree of X^N + 1
SEAM = math.radians(45)       # tail exits bottom-right (SVG y points down)
GAP_VERTS = 3                 # vertices dropped either side of the open seam


def f(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def ring_halves(cx: float, cy: float, r: float) -> list[str]:
    """Two polyline paths: the 256-gon split along the 45deg diagonal.

    The seam under the tail keeps every vertex (the tail covers it); the
    opposite seam at 225deg drops GAP_VERTS vertices per side so the two
    halves read as separate components joined only through the tail.
    """
    angles = [(2 * k + 1) * math.pi / N for k in range(N)]

    def side(a: float) -> int:  # 0 = upper-right half, 1 = lower-left half
        d = (a - SEAM) % (2 * math.pi)
        return 0 if d >= math.pi else 1

    halves: list[list[float]] = [[], []]
    for a in angles:
        halves[side(a)].append(a)

    paths = []
    for h, verts in enumerate(halves):
        # order each half as a continuous run starting just after a seam
        start = SEAM if h == 1 else SEAM + math.pi
        verts.sort(key=lambda a: (a - start) % (2 * math.pi))
        # open the 225deg seam: trim the end of the run that touches it
        verts = verts[:-GAP_VERTS] if h == 1 else verts[GAP_VERTS:]
        # close the 45deg seam exactly on the diagonal so the tail meets it
        if h == 1:
            verts = [SEAM] + verts
        else:
            verts = verts + [SEAM + 2 * math.pi]
        pts = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in verts]
        d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts)
        paths.append(d)
    return paths


def mark_group(cx, cy, r, w, tail_len, fg, accent, lattice=True, ghost=True, dot=None):
    """The Q mark. Returns SVG elements (no wrapper)."""
    out = []
    for d in ring_halves(cx, cy, r):
        out.append(f'<path d="{d}" fill="none" stroke="{fg}" stroke-width="{f(w)}" '
                   f'stroke-linejoin="round"/>')
    # tail: radial, from the inner edge through the seam outward
    ux, uy = math.cos(SEAM), math.sin(SEAM)
    r0, r1 = r - w / 2, r + tail_len
    out.append(f'<path d="M{f(cx + r0 * ux)} {f(cy + r0 * uy)} L{f(cx + r1 * ux)} '
               f'{f(cy + r1 * uy)}" stroke="{fg}" stroke-width="{f(w)}"/>')

    # lattice: basis b1 = (s, 0), b2 = (shear, s); k = 3 -> 3x3 nodes
    s = r * 0.31
    shear = s * 0.36
    dot = dot or r / 15            # = w*0.24 on the master mark (r=36, w=10)
    err = (s * 0.36, -s * 0.24)        # the LWE error vector e
    if lattice:
        for j in (-1, 0, 1):
            for i in (-1, 0, 1):
                if i == 0 and j == 0:
                    continue
                x = cx + i * s + j * shear
                y = cy + j * s
                out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(dot)}" fill="{fg}"/>')
        if ghost:   # where the point *should* be -- only visible up close
            out.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(dot * 0.9)}" fill="none" '
                       f'stroke="{fg}" stroke-width="{f(dot * 0.32)}" opacity=".5"/>')
        out.append(f'<circle cx="{f(cx + err[0])}" cy="{f(cy + err[1])}" r="{f(dot * 1.3)}" '
                   f'fill="{accent}"/>')
    else:
        out.append(f'<circle cx="{f(cx + err[0] * 0.6)}" cy="{f(cy + err[1] * 0.6)}" '
                   f'r="{f(w * 0.62)}" fill="{accent}"/>')
    return out


# --- wordmark: monoline geometric caps, built on a clipped cap-height band ---

def wordmark(x0, top, cap, w, fg, q=True, round_dots=False):
    """'QU.I.R.K.' as stroked paths. Returns (elements, width).

    q=False drops the Q so a mark can stand in for it. round_dots draws the
    periods as lattice points instead of squares.
    """
    base = top + cap
    h = w / 2
    els, x = [], x0
    gap, dgap = cap * 0.2, cap * 0.11

    def dotsq(x):
        if round_dots:
            d = w * 1.18
            els.append(f'<circle cx="{f(x + d / 2)}" cy="{f(base - d / 2)}" r="{f(d / 2)}" fill="{fg}"/>')
            return x + d
        els.append(f'<rect x="{f(x)}" y="{f(base - w)}" width="{f(w)}" height="{f(w)}" fill="{fg}"/>')
        return x + w

    # Q -- same construction as the mark, small, no lattice
    if q:
        rq = cap / 2 - h
        qx, qy = x + cap / 2, top + cap / 2
        els += mark_group(qx, qy, rq, w, cap * 0.2, fg, fg, lattice=False)[:3]
        x += cap + gap
    # U
    uw = cap * 0.78
    ur = (uw - w) / 2
    els.append(f'<path d="M{f(x + h)} {f(top)} V{f(base - h - ur)} A{f(ur)} {f(ur)} 0 0 0 '
               f'{f(x + uw - h)} {f(base - h - ur)} V{f(top)}" fill="none" stroke="{fg}" '
               f'stroke-width="{f(w)}"/>')
    x += uw + dgap
    x = dotsq(x) + dgap
    # I
    els.append(f'<path d="M{f(x + h)} {f(top)} V{f(base)}" stroke="{fg}" stroke-width="{f(w)}"/>')
    x += w + dgap
    x = dotsq(x) + dgap
    # R
    rb = (cap * 0.5 - w) / 2          # bowl radius on centreline
    rw = cap * 0.74
    bx = x + rw - h - rb
    els.append(f'<path d="M{f(x + h)} {f(base)} V{f(top + h)} H{f(bx)} A{f(rb)} {f(rb)} 0 0 1 '
               f'{f(bx)} {f(top + h + 2 * rb)} H{f(x + h)}" fill="none" stroke="{fg}" '
               f'stroke-width="{f(w)}" stroke-linejoin="miter"/>')
    els.append(f'<path d="M{f(bx - rb * 0.15)} {f(top + h + 2 * rb)} L{f(x + rw + 2)} {f(base + 4)}" '
               f'stroke="{fg}" stroke-width="{f(w)}"/>')
    x += rw + dgap
    x = dotsq(x) + dgap
    # K -- arm and leg are one stroke that turns inside the stem, so no seam shows
    kw = cap * 0.72
    o = w * 0.6                        # overshoot, clipped flat by the cap band
    els.append(f'<path d="M{f(x + h)} {f(top)} V{f(base)}" stroke="{fg}" stroke-width="{f(w)}"/>')
    els.append(f'<path d="M{f(x + kw + o * 0.6)} {f(top - o)} L{f(x + w)} {f(top + cap * 0.56)} '
               f'L{f(x + kw + o * 0.6)} {f(base + o)}" fill="none" stroke="{fg}" stroke-width="{f(w)}" '
               f'stroke-linejoin="miter" stroke-miterlimit="4"/>')
    x += kw + dgap
    x = dotsq(x)
    return els, x - x0


DESCRIPTOR = "QUANTUM INFRASTRUCTURE READINESS KIT"
MONO = "'JetBrains Mono', ui-monospace, Menlo, monospace"


def descriptor(x, y, width, size, fg, opacity=0.72):
    """Live-text descriptor, stretched to exactly `width` so it locks to the wordmark."""
    return (f'<text x="{f(x)}" y="{f(y)}" textLength="{f(width)}" lengthAdjust="spacing" '
            f'font-family="{MONO}" font-size="{f(size)}" font-weight="600" fill="{fg}" '
            f'opacity="{opacity}">{DESCRIPTOR}</text>')


def lattice_field(cx, cy, r, w, tail, W, H, fg, keep_out):
    """The lattice the lens is looking at, continued across the canvas.

    Same basis and origin as the mark's 3x3, so the field and the mark agree.
    Dots fade with distance from the lens; nothing is drawn under the ring,
    inside the counter (the mark's own 3x3 lives there), along the tail,
    or inside the keep-out rectangles (type).
    """
    s = r * 0.31
    sh = s * 0.36
    dot = r / 15 * 0.55
    outer = r + w / 2 + w * 0.55         # clears the ring
    ux, uy = math.cos(SEAM), math.sin(SEAM)
    out = []
    jr = int(H / s) + 2
    for j in range(-jr, jr + 1):
        for i in range(-int(W / s) - jr, int(W / s) + jr):
            x, y = cx + i * s + j * sh, cy + j * s
            if not (dot < x < W - dot and dot < y < H - dot):
                continue
            d = math.hypot(x - cx, y - cy)
            if d < outer:
                continue
            t = (x - cx) * ux + (y - cy) * uy             # distance along tail axis
            if 0 < t < r + tail + w and abs(-(x - cx) * uy + (y - cy) * ux) < w * 1.1:
                continue
            if any(a <= x <= c and b <= y <= e for a, b, c, e in keep_out):
                continue
            op = max(0.025, 0.16 * (1 - (d - outer) / (W * 0.42)))
            out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(dot)}" fill="{fg}" opacity="{op:.3f}"/>')
    return out


def svg(w, h, body, title, bg=None):
    bg_el = f'<rect width="{f(w)}" height="{f(h)}" fill="{bg}"/>' if bg else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(w)} {f(h)}" '
        f'width="{f(w)}" height="{f(h)}" role="img" aria-labelledby="t">\n'
        f'  <title id="t">{title}</title>\n'
        f'  <desc>R_q = Z_3329[X]/(X^256+1). k=3. b = As + e. Ink 0x0D01 = q(ML-KEM); '
        f'accent 0x7FE001 = q(ML-DSA).</desc>\n'
        f'  {bg_el}\n  ' + "\n  ".join(body) + "\n</svg>\n"
    )


def clipped(els, top, cap):
    """Wrap wordmark strokes in the cap-height clip (flat tops and baselines)."""
    cid = f"cap{top:g}"
    return [f'<clipPath id="{cid}"><rect x="0" y="{f(top)}" width="4000" height="{f(cap)}"/></clipPath>',
            f'<g clip-path="url(#{cid})">', *els, "</g>"]


def logo(x, top, cap, fg, accent=SIG):
    """Primary logo: the lens is the Q, at cap height. Returns (elements, width)."""
    w = cap * 0.175
    D = cap * 1.04                     # round-letter overshoot
    r = D / 2 - w / 2
    body = mark_group(x + D / 2, top + cap / 2, r, w, cap * 0.34, fg, accent, dot=r * 0.088)
    tx = x + D + cap * 0.17
    wm, ww = wordmark(tx, top, cap, w, fg, q=False, round_dots=True)
    return body + clipped(wm, top, cap), (tx - x) + ww, tx, ww


def logo_display(x, top, cap, fg, accent=SIG):
    """Display logo: oversized lens leads (1.55x cap), master-mark proportions."""
    w = cap * 0.175
    D = cap * 1.55
    r = D / 2 - w / 2
    cx, cy = x + D / 2, top + cap / 2
    body = mark_group(cx, cy, r, w, r * 26 / 36, fg, accent)
    tx = x + D + cap * 0.2
    wm, ww = wordmark(tx, top, cap, w, fg, q=False, round_dots=True)
    return body + clipped(wm, top, cap), (tx - x) + ww, tx, ww, (cx, cy, r, w)


THEMES = (("", INK, None), ("-dark", PAPER, INK))
FULL = "QU.I.R.K. — Quantum Infrastructure Readiness Kit"


def build():
    files = {}
    # 1. mark (icon) -- 120 x 120 artboard
    for sfx, fg, bg in THEMES:
        files[f"quirk-mark{sfx}.svg"] = svg(120, 120, mark_group(54, 54, 36, 10, 26, fg, SIG), "QU.I.R.K. mark", bg)
    files["quirk-mark-mono.svg"] = svg(120, 120, mark_group(54, 54, 36, 10, 26, INK, INK, ghost=False),
                                       "QU.I.R.K. mark (mono)")
    # 2. favicon: ring + tail + error point, no lattice
    for sfx, fg, bg in THEMES:
        files[f"quirk-favicon{sfx}.svg"] = svg(32, 32, mark_group(14.5, 14.5, 10, 4, 7.5, fg, SIG, lattice=False),
                                               "QU.I.R.K.", bg)
    # 3. primary logo, and primary logo + descriptor
    for sfx, fg, bg in THEMES:
        cap, top, pad = 120, 40, 40
        body, W, tx, ww = logo(pad, top, cap, fg)
        files[f"quirk-logo{sfx}.svg"] = svg(W + 2 * pad, 210, body, "QU.I.R.K.", bg)
        body, W, tx, ww = logo(pad, top, cap, fg)
        body.append(descriptor(tx, top + cap + 62, ww, 19.5, fg))
        files[f"quirk-logo-descriptor{sfx}.svg"] = svg(W + 2 * pad, 250, body, FULL, bg)
    # 4. display logo: oversized lens
    for sfx, fg, bg in THEMES:
        cap, top, pad = 120, 62, 40
        body, W, *_ = logo_display(pad, top, cap, fg)
        files[f"quirk-logo-display{sfx}.svg"] = svg(W + 2 * pad, 262, body, "QU.I.R.K.", bg)
    # 5. hero (16:9): display logo on the lattice field
    for sfx, fg, bg in (("", INK, PAPER), ("-dark", PAPER, INK)):
        W, H, cap = 1600, 900, 196
        _, lw, *_ = logo_display(0, 0, cap, fg)
        x0, top = (W - lw) / 2 + 20, H / 2 - cap / 2 - 24
        body, _, tx, ww, (cx, cy, r, w) = logo_display(x0, top, cap, fg)
        desc_y = top + cap + 54
        keep = [(tx - 40, top - 50, tx + ww + 40, desc_y + 30)]
        field = lattice_field(cx, cy, r, w, r * 26 / 36, W, H, fg, keep)
        files[f"quirk-hero{sfx}.svg"] = svg(
            W, H, field + body + [descriptor(tx + cap * 0.12, desc_y, ww - cap * 0.12, 25, fg)], FULL, bg)

    stale = {"quirk-lockup.svg", "quirk-lockup-dark.svg", "quirk-lockup-stacked.svg",
             "quirk-lockup-stacked-dark.svg", "quirk-wordmark.svg", "quirk-wordmark-dark.svg",
             "quirk-wordmark-lens.svg", "quirk-wordmark-lens-dark.svg"}
    for fn in stale:
        (OUT / fn).unlink(missing_ok=True)
    for fn, content in files.items():
        (OUT / fn).write_text(content)
        print("wrote", fn)


if __name__ == "__main__":
    build()
