// D-09 (WR-10): Module augmentation re-opens cytoscape's `use` signature to
// accept arbitrary extension objects without per-callsite casts.
//
// Sibling to cytoscape-extensions.d.ts (which declares the extension modules
// themselves). Kept in a separate file so the two concerns — extension module
// declarations vs. core API augmentation — stay independently auditable.

import "cytoscape"

declare module "cytoscape" {
  function use(extension: unknown): void
}
