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


def mark_group(cx, cy, r, w, tail_len, fg, accent, lattice=True, ghost=True):
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
    dot = w * 0.24
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

def wordmark(x0, top, cap, w, fg):
    """'QU.I.R.K.' as stroked paths. Returns (elements, width)."""
    base = top + cap
    h = w / 2
    els, x = [], x0
    gap, dgap = cap * 0.2, cap * 0.11

    def dotsq(x):
        els.append(f'<rect x="{f(x)}" y="{f(base - w)}" width="{f(w)}" height="{f(w)}" fill="{fg}"/>')
        return x + w

    # Q -- same construction as the mark, small, no lattice
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
    # K
    kw = cap * 0.72
    els.append(f'<path d="M{f(x + h)} {f(top)} V{f(base)}" stroke="{fg}" stroke-width="{f(w)}"/>')
    els.append(f'<path d="M{f(x + kw + 2)} {f(top - 3)} L{f(x + w)} {f(top + cap * 0.6)}" '
               f'stroke="{fg}" stroke-width="{f(w)}"/>')
    els.append(f'<path d="M{f(x + w + cap * 0.17)} {f(top + cap * 0.44)} L{f(x + kw + 2)} {f(base + 4)}" '
               f'stroke="{fg}" stroke-width="{f(w)}"/>')
    x += kw + dgap
    x = dotsq(x)
    return els, x - x0


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


def build():
    files = {}
    # 1. mark, light + dark (120 x 120 artboard)
    for name, fg, bg in (("mark", INK, None), ("mark-dark", PAPER, INK)):
        body = mark_group(54, 54, 36, 10, 26, fg, SIG)
        files[f"quirk-{name}.svg"] = svg(120, 120, body, "QU.I.R.K. mark", bg)

    # 2. mono mark (single colour -- print, emboss, 3D print, laser)
    body = mark_group(54, 54, 36, 10, 26, INK, INK, ghost=False)
    files["quirk-mark-mono.svg"] = svg(120, 120, body, "QU.I.R.K. mark (mono)")

    # 3. favicon / small sizes: no lattice, just ring + tail + error dot
    body = mark_group(14.5, 14.5, 10, 4, 7.5, INK, SIG, lattice=False)
    files["quirk-favicon.svg"] = svg(32, 32, body, "QU.I.R.K.", None)
    body = mark_group(14.5, 14.5, 10, 4, 7.5, PAPER, SIG, lattice=False)
    files["quirk-favicon-dark.svg"] = svg(32, 32, body, "QU.I.R.K.", INK)

    # 4. horizontal lockup
    for name, fg, bg in (("lockup", INK, None), ("lockup-dark", PAPER, INK)):
        body = mark_group(64, 64, 36, 10, 26, fg, SIG)
        cap, top = 40, 44
        clip = f'<clipPath id="cap"><rect x="0" y="{top}" width="2000" height="{cap}"/></clipPath>'
        wm, ww = wordmark(136, top, cap, 7, fg)
        body += [clip, '<g clip-path="url(#cap)">', *wm, "</g>"]
        W = 136 + ww + 28
        files[f"quirk-{name}.svg"] = svg(W, 136, body, "QU.I.R.K. — Quantum Infrastructure Readiness Kit", bg)

    for fn, content in files.items():
        (OUT / fn).write_text(content)
        print("wrote", fn)


if __name__ == "__main__":
    build()
