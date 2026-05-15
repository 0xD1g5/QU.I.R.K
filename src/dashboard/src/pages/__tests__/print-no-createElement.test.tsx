import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"

// D-28 (IN-06): print.tsx must use JSX <style>{PRINT_CSS}</style>
// instead of React.createElement("style", ...) per RESEARCH Pattern 7.
describe("print.tsx — D-28 (IN-06) JSX style element replaces createElement", () => {
  const SRC = readFileSync(path.resolve(__dirname, "../print.tsx"), "utf-8")

  it('does not call createElement("style", ...) anywhere', () => {
    expect(SRC).not.toMatch(/createElement\(\s*["']style["']/)
  })

  it("renders PRINT_CSS via a JSX <style> element", () => {
    expect(SRC).toMatch(/<style>\s*\{\s*PRINT_CSS\s*\}\s*<\/style>/)
  })

  it("preserves the BR-05 cleanup effect from Phase 62 (D-32 do-not-touch)", () => {
    // Phase 62 BR-05 cleanup must remain in the cleanup return
    expect(SRC).toMatch(/document\.body\.removeAttribute\(['"]data-ready['"]\)/)
  })
})
