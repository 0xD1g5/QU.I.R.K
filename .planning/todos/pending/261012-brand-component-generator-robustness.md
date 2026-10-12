---
type: todo
created: 2026-10-12
source: Phase 223 code review (223-REVIEW.md WR-02..04, IN-01..05)
priority: low
area: scripts/build_brand_component.py, scripts/build_brand_rasters.py, tests
status: pending
resolves_phase: null
---

# Brand component generator robustness (Phase 223 review residue)

**Owner phase:** unassigned

None of these bite with today's committed brand SVGs; they bite on the next source edit.
WR-01 (login logo centred) was fixed in Phase 223 itself.

- [ ] **WR-02** `scripts/build_brand_component.py:63-68` slices the source SVG by line position
      (`lines[3:-1]`). A trailing blank line copies `</svg>` into the TSX body (invalid TSX, drift gate passes
      after regen, only the dashboard build catches it); a two-line-shorter header silently drops the first
      drawn element. Parse the root element instead of slicing.
- [ ] **WR-03** `:57-58,75-76` only `cap…` ids are uniquified; a second clipPath collides inside one SVG and
      any other id collides when the logo is mounted twice — contrary to the script docstring.
- [ ] **WR-04** `:55,77` validation lets `style=`, `class=`, `xlink:href` and lowercase `#0d0124` through;
      fail loudly in the generator.
- [ ] IN-01 `pack_ico` silently encodes sizes >256 as 256 — reject instead.
- [ ] IN-02 unused `SIGNAL` constant.
- [ ] IN-03 comments in `tests/browser_e2e_harness.py` / KBD-01 tests still say the mount guard only passes
      above 1024 px; the glyph shares role+name, so it passes at any width.
- [ ] IN-04 UAT-7-23 locates logo/glyph by `data-brand-variant` rather than role+name.
- [ ] IN-05 ICO structure test checks width only; the byte check skips without resvg-py locally.
