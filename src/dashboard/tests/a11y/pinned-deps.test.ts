import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"

// Phase 165 / A11Y-05 / 165-CONTEXT.md D-04 — the two npm inputs that decide
// what axe reports (@axe-core/puppeteer and puppeteer-core) must be pinned to
// exact, already-resolved versions with no ^ or ~ range, so a silent
// transitive upgrade cannot change the a11y gate's output out from under us.

const PACKAGE_JSON = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../package.json"), "utf-8"),
)

describe("pinned a11y-determining dependencies (A11Y-05 / D-04)", () => {
  it("pins @axe-core/puppeteer to the exact resolved version 4.11.3", () => {
    expect(PACKAGE_JSON.devDependencies["@axe-core/puppeteer"]).toBe("4.11.3")
  })

  it("pins puppeteer-core to the exact resolved version 24.43.1", () => {
    expect(PACKAGE_JSON.devDependencies["puppeteer-core"]).toBe("24.43.1")
  })

  it("does not allow a caret or tilde range prefix on either pin", () => {
    const axeCorePuppeteer = PACKAGE_JSON.devDependencies["@axe-core/puppeteer"]
    const puppeteerCore = PACKAGE_JSON.devDependencies["puppeteer-core"]
    expect(axeCorePuppeteer).not.toMatch(/^[\^~]/)
    expect(puppeteerCore).not.toMatch(/^[\^~]/)
  })
})
