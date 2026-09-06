import { describe, it, expect } from "vitest"
import { readFileSync, existsSync } from "node:fs"
import path from "node:path"

// Phase 165 / A11Y-05 / 165-CONTEXT.md D-04 — the two npm inputs that decide
// what axe reports (@axe-core/puppeteer and puppeteer-core) must be pinned to
// exact, already-resolved versions with no ^ or ~ range, so a silent
// transitive upgrade cannot change the a11y gate's output out from under us.
//
// Phase 185 D-07/D-09 — the CI Chrome BINARY itself is now ALSO pinned (not just
// the npm packages that drive it), to a concrete version in
// `.github/workflows/dashboard-quality.yml`. This supersedes Phase 165 D-04's
// "unpinned Chrome, mitigated by jitter-tolerant counts" justification: D-06 keeps
// exact-integer counts with no tolerance band, so the pin is what makes that
// comparison sound. Asserted below by reading the raw workflow YAML as text (no
// YAML parser dependency — see 185-RESEARCH.md Pitfall 4). The LOCAL Puppeteer
// `channel: 'chrome'` launch path in run-a11y.mjs stays unpinned per D-08.

const PACKAGE_JSON = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../package.json"), "utf-8"),
)

const WORKFLOW_PATH = path.resolve(
  __dirname,
  "../../../../.github/workflows/dashboard-quality.yml",
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

describe("pinned CI Chrome version (Phase 185 D-07 / D-09)", () => {
  // Guard against a vacuous pass if the relative path from this file up to the
  // workflow file ever breaks (e.g. the test file moves).
  it("resolves the workflow file and it is non-empty", () => {
    expect(existsSync(WORKFLOW_PATH)).toBe(true)
    const contents = readFileSync(WORKFLOW_PATH, "utf-8")
    expect(contents.length).toBeGreaterThan(0)
  })

  const WORKFLOW_TEXT = existsSync(WORKFLOW_PATH)
    ? readFileSync(WORKFLOW_PATH, "utf-8")
    : ""

  it("never floats on a channel name (stable/beta/dev/canary/latest)", () => {
    expect(WORKFLOW_TEXT).not.toMatch(
      /chrome-version:\s*['"]?(stable|beta|dev|canary|latest)\b/i,
    )
  })

  it("every chrome-version occurrence is a concrete MAJOR.MINOR.BUILD.PATCH pin", () => {
    const matches = [
      ...WORKFLOW_TEXT.matchAll(/chrome-version:\s*['"]?([^'"\s#]+)/g),
    ].map((m) => m[1])
    expect(matches.length).toBeGreaterThan(0)
    for (const version of matches) {
      expect(version).toMatch(/^\d+\.\d+\.\d+\.\d+$/)
    }
  })

  // As of Phase 185 there are THREE browser-actions/setup-chrome usages in this
  // workflow -- the `a11y` job, the `a11y-regenerate-baselines` job, and the
  // `e2e-smoke` job (a third usage discovered during 185-02 execution that
  // 185-RESEARCH.md/185-CONTEXT.md did not anticipate). All three must agree so
  // an enforcement run, a baseline-regeneration run, and the E2E smoke run never
  // silently disagree on which Chrome build produced their results. This count
  // is intentionally NOT the specific version string (D-09 forbids hardcoding
  // the version itself), only the count and mutual equality -- if a fourth job
  // adds its own setup-chrome step, this test's count assertion will correctly
  // fail until that job is included in the same pin.
  it("every chrome-version occurrence agrees on the same pinned value", () => {
    const matches = [
      ...WORKFLOW_TEXT.matchAll(/chrome-version:\s*['"]?([^'"\s#]+)/g),
    ].map((m) => m[1])
    expect(matches.length).toBe(3)
    const distinct = new Set(matches)
    expect(distinct.size).toBe(1)
  })
})
