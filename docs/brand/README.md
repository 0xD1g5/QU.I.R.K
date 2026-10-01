# QU.I.R.K. brand mark

A Q drawn as a scanner lens over a lattice. Every element encodes a post-quantum concept.

| Element | Encodes |
|---|---|
| Ring is a 256-gon, vertices at (2k+1)·π/256 | Roots of X²⁵⁶+1, the ring R_q of ML-KEM (FIPS 203) and ML-DSA (FIPS 204) |
| Ring is two halves joined only by the tail | Hybrid key exchange (X25519MLKEM768): two secrets, one KDF |
| 3×3 sheared dot lattice | ML-KEM-768 public matrix A (k = 3), shown in a skewed "bad" basis |
| Centre point offset from its node (faint ring = true node) | Learning With Errors, b = As + e. The error is the quirk |
| Ink `#0D0124` | 0x0D01 = 3329, the ML-KEM modulus q |
| Signal `#7FE001` | 0x7FE001 = 8,380,417, the ML-DSA modulus q |

## Files

| File | Use |
|---|---|
| `quirk-mark.svg` / `quirk-mark-dark.svg` | Full mark, 48 px and up |
| `quirk-mark-mono.svg` | Single colour: print, emboss, laser, 3D print |
| `quirk-favicon.svg` / `quirk-favicon-dark.svg` | Below 48 px (no lattice) |
| `quirk-lockup.svg` / `quirk-lockup-dark.svg` | Mark + wordmark |
| `brand-sheet.html` | Interactive construction guide |

## Rules

- Clear space: one ring stroke width (10 units on the 120 grid) on every side.
- Signal is used once, on the error point only.
- Don't hand-edit the SVGs. Change `build_logo.py` and run `python3 docs/brand/build_logo.py` (stdlib only).

Not encoded: SLH-DSA (FIPS 205), FN-DSA, HQC.
