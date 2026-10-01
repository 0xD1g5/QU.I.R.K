import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync } from "node:fs"
import path from "node:path"
import { VARIANTS, isPlaceholderJustification } from "./baseline-diff.mjs"
import { FIXTURE_HANDLERS } from "./fixture-handlers.mjs"

// Phase 221 / HARNESS-03 / 221-CONTEXT.md D-05, D-06. Run-time enumeration contract:
// every route in routes.json must carry exactly one variant decision (per-endpoint
// `variantMarkers`, or a written `variantInsensitive` reason), and the VARIANTS allowlist,
// npm scripts, CI steps and harness guards must not drift apart. Occurrence sets are derived
// at test time, never from a hand-listed array (mutation M5 targets the route decision).

const PACKAGE_JSON = JSON.parse(readFileSync(path.resolve(__dirname, "../../package.json"), "utf-8"))
const WORKFLOW_TEXT = readFileSync(
  path.resolve(__dirname, "../../../../.github/workflows/dashboard-quality.yml"),
  "utf-8",
)
const RUN_A11Y_SOURCE = readFileSync(path.resolve(__dirname, "run-a11y.mjs"), "utf-8")
const ROUTES: Array<Record<string, unknown> & { slug: string }> = JSON.parse(
  readFileSync(path.resolve(__dirname, "routes.json"), "utf-8"),
)
const NON_DEFAULT = VARIANTS.filter((v: string) => v !== "default")

describe("variant-contract (221-01)", () => {
  it("VARIANTS carries at least three entries (vacuity guard)", () => {
    expect(Array.isArray(VARIANTS)).toBe(true)
    expect(VARIANTS.length).toBeGreaterThanOrEqual(3)
  })

  it("routes.json carries at least 13 routes (vacuity guard)", () => {
    expect(ROUTES.length).toBeGreaterThanOrEqual(13)
  })

  it.each(NON_DEFAULT)("package.json declares a11y:check:%s and a11y:baseline:%s, each setting VITE_A11Y_FIXTURE_VARIANT=%s", (v) => {
    for (const kind of ["check", "baseline"]) {
      const script = PACKAGE_JSON.scripts[`a11y:${kind}:${v}`]
      expect(script, `missing npm script a11y:${kind}:${v}`).toBeTruthy()
      expect(script).toContain(`VITE_A11Y_FIXTURE_VARIANT=${v}`)
    }
  })

  it.each(NON_DEFAULT)("dashboard-quality.yml names both npm run a11y:check:%s and npm run a11y:baseline:%s", (v) => {
    expect(WORKFLOW_TEXT, `no "npm run a11y:check:${v}" step`).toContain(`npm run a11y:check:${v}`)
    expect(WORKFLOW_TEXT, `no "npm run a11y:baseline:${v}" step`).toContain(`npm run a11y:baseline:${v}`)
  })

  it.each(ROUTES.map((r) => r.slug))("route %s carries exactly one variant decision", (slug) => {
    const route = ROUTES.find((r) => r.slug === slug)!
    const markers = route.variantMarkers as Record<string, unknown> | undefined
    const insensitive = route.variantInsensitive
    const hasMarkers = markers !== undefined
    const hasInsensitive = insensitive !== undefined
    expect(
      hasMarkers !== hasInsensitive,
      `route "${slug}" must have exactly one of variantMarkers or variantInsensitive (D-06)`,
    ).toBe(true)
    if (hasMarkers) {
      expect(typeof markers).toBe("object")
      const entries = Object.entries(markers!)
      expect(entries.length, `route "${slug}" variantMarkers is empty`).toBeGreaterThan(0)
      for (const [handler, sel] of entries) {
        expect(typeof sel === "string" && sel.length > 0, `route "${slug}" marker for ${handler} is not a non-empty string`).toBe(true)
      }
    } else {
      expect(typeof insensitive).toBe("string")
      expect(
        isPlaceholderJustification(insensitive),
        `route "${slug}" variantInsensitive reason is a placeholder`,
      ).toBe(false)
    }
  })

  it("vite.config.ts is table-driven: imports fixture-handlers.mjs, tracks held responses, destroys them (221 D-03/D-08)", () => {
    const vite = readFileSync(path.resolve(__dirname, "../../vite.config.ts"), "utf-8")
    expect(vite).toContain("fixture-handlers.mjs")
    expect(vite).toContain("held")
    expect(vite).toContain("destroy")
  })

  it("run-a11y.mjs refuses a pre-existing server on the port (221 D-02)", () => {
    expect(RUN_A11Y_SOURCE).toContain("already answers before this sweep")
  })

  it("run-a11y.mjs checks the /__a11y-variant sentinel (221 D-02)", () => {
    expect(RUN_A11Y_SOURCE).toContain("__a11y-variant")
  })

  it("run-a11y.mjs applies renderStateViolations before the axe scan (221 D-05)", () => {
    const guard = RUN_A11Y_SOURCE.indexOf("renderStateViolations(")
    const axe = RUN_A11Y_SOURCE.indexOf("new AxePuppeteer(")
    expect(guard).toBeGreaterThan(-1)
    expect(axe).toBeGreaterThan(-1)
    expect(guard).toBeLessThan(axe)
  })

  it("run-a11y.mjs waits for the empty-state witness before the marker-absence probe (221 WR-02)", () => {
    const wait = RUN_A11Y_SOURCE.indexOf("await page.waitForSelector(sel, { timeout: 5_000 })")
    const absence = RUN_A11Y_SOURCE.indexOf("present[selector] = !!(await page.$(selector))")
    expect(wait, "no empty-state witness wait").toBeGreaterThan(-1)
    expect(absence).toBeGreaterThan(-1)
    expect(wait).toBeLessThan(absence)
    expect(RUN_A11Y_SOURCE).toContain("emptyWitnesses,")
  })

  it("run-a11y.mjs owns its preview by process group with strictPort (221 D-02)", () => {
    for (const needle of ["detached: true", "--strictPort", "process.kill(-", "SIGKILL"]) {
      expect(RUN_A11Y_SOURCE, `missing ${needle}`).toContain(needle)
    }
    expect(RUN_A11Y_SOURCE).not.toContain("previewProc.kill('SIGTERM')")
  })

  it("run-a11y.mjs navigates loading on 'load' and derives endpoints at run time (221 D-06/D-08)", () => {
    for (const needle of ["waitUntil", "'load'", "matchHandler", "does not declare"]) {
      expect(RUN_A11Y_SOURCE, `missing ${needle}`).toContain(needle)
    }
  })
})

// 221-03 / D-03: every fixture handler carries an explicit empty AND loading decision.
// Failure messages name the handler id (mutation M4: delete a handler's `empty` key).
type Handler = (typeof FIXTURE_HANDLERS)[number]
const decisionKinds = (d: unknown, keys: string[]): string[] =>
  d && typeof d === "object" ? keys.filter((k) => k in (d as object)) : []
const goodReason = (r: unknown): boolean =>
  typeof r === "string" && r.length >= 20 && !isPlaceholderJustification(r)

describe("fixture handler contract (221-03)", () => {
  it("FIXTURE_HANDLERS carries at least 12 handlers with unique ids (vacuity guard)", () => {
    expect(FIXTURE_HANDLERS.length).toBeGreaterThanOrEqual(12)
    const ids = FIXTURE_HANDLERS.map((h: Handler) => h.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it.each(FIXTURE_HANDLERS.map((h: Handler) => h.id))("handler %s has explicit empty and loading decisions", (id) => {
    const h = FIXTURE_HANDLERS.find((x: Handler) => x.id === id)!
    expect(h.default, `handler "${id}" has no default source`).toBeTruthy()
    const empty = decisionKinds(h.empty, ["body", "emptyFrom", "na"])
    expect(empty.length, `handler "${id}" must declare exactly one of empty.{body|emptyFrom|na}`).toBe(1)
    const loading = decisionKinds(h.loading, ["hold", "na"])
    expect(loading.length, `handler "${id}" must declare exactly one of loading.{hold|na}`).toBe(1)
    if ("na" in (h.empty as object)) {
      expect(goodReason((h.empty as { na: string }).na), `handler "${id}" empty.na is empty or a placeholder`).toBe(true)
    }
    if ("hold" in (h.loading as object)) {
      expect((h.loading as { hold: unknown }).hold, `handler "${id}" loading.hold must be true`).toBe(true)
    }
    if ("na" in (h.loading as object)) {
      expect(goodReason((h.loading as { na: string }).na), `handler "${id}" loading.na is empty or a placeholder`).toBe(true)
    }
    if (h.scope !== undefined) {
      expect(goodReason(h.scopeReason), `handler "${id}" scopeReason is empty or a placeholder`).toBe(true)
    }
  })

  const honouring = new Set(
    FIXTURE_HANDLERS.filter(
      (h: Handler) => decisionKinds(h.empty, ["body", "emptyFrom"]).length === 1 && decisionKinds(h.loading, ["hold"]).length === 1,
    ).map((h: Handler) => h.id),
  )
  const allIds = new Set(FIXTURE_HANDLERS.map((h: Handler) => h.id))

  it.each(ROUTES.map((r) => r.slug))("route %s variantMarkers keys are handlers that honour both variants", (slug) => {
    const route = ROUTES.find((r) => r.slug === slug)!
    const markers = (route.variantMarkers ?? {}) as Record<string, string>
    for (const id of Object.keys(markers)) {
      // 221-06: a route that retires its loading leg only needs the handler to honour empty.
      if ((route as { loadingRetired?: string }).loadingRetired && decisionKinds(FIXTURE_HANDLERS.find((h: Handler) => h.id === id)?.empty ?? {}, ["body", "emptyFrom"]).length === 1) continue
      expect(honouring.has(id), `route "${slug}" marks handler "${id}", which does not honour both empty and loading`).toBe(true)
    }
    const unmarked = (route.unmarkedEndpoints ?? {}) as Record<string, string>
    for (const id of Object.keys(unmarked)) {
      expect(allIds.has(id), `route "${slug}" unmarkedEndpoints names unknown handler "${id}"`).toBe(true)
    }
  })

  // 221 CR-01: a marker shared by two handlers on one route is satisfied by EITHER handler's
  // component, so the default leg cannot fail when one of them breaks (the /hardware
  // `.font-data` / `.divide-y.divide-border` defect). Selectors must be distinct per route.
  it.each(ROUTES.map((r) => r.slug))("route %s gives every handler a distinct marker selector", (slug) => {
    const route = ROUTES.find((r) => r.slug === slug)!
    const markers = (route.variantMarkers ?? {}) as Record<string, string>
    const bySelector = new Map<string, string[]>()
    for (const [id, sel] of Object.entries(markers)) bySelector.set(sel, [...(bySelector.get(sel) ?? []), id])
    for (const [sel, ids] of bySelector) {
      expect(ids.length, `route "${slug}": handlers ${ids.join(", ")} share marker "${sel}"`).toBe(1)
    }
  })

  // 221 CR-01: an identity-bearing `[data-a11y-marker="<id>"]` selector must name its own
  // handler id and be emitted by exactly one component, so it cannot be satisfied by another
  // endpoint's panel. Occurrences are scanned from src/ at test time, never hand-listed.
  const MARKER_ATTR = /^\[data-a11y-marker="([^"]+)"\]$/
  const srcRoot = path.resolve(__dirname, "../../src")
  const srcFiles: string[] = []
  const walk = (dir: string) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name)
      if (e.isDirectory()) { if (e.name !== "__tests__") walk(p) }
      else if (/\.(tsx|ts)$/.test(e.name) && !/\.test\.tsx?$/.test(e.name)) srcFiles.push(p)
    }
  }
  walk(srcRoot)
  const attrMarkers = ROUTES.flatMap((r) =>
    Object.entries((r.variantMarkers ?? {}) as Record<string, string>)
      .filter(([, sel]) => MARKER_ATTR.test(sel))
      .map(([id, sel]) => [r.slug, id, sel.match(MARKER_ATTR)![1]] as const),
  )

  it("at least one route uses an identity-bearing data-a11y-marker (vacuity guard)", () => {
    expect(attrMarkers.length).toBeGreaterThanOrEqual(2)
  })

  it.each(attrMarkers)("route %s marker for %s ([data-a11y-marker=%s]) is unique to one component", (slug, id, value) => {
    expect(value, `route "${slug}": data-a11y-marker value must equal the handler id`).toBe(id)
    const needle = `data-a11y-marker="${value}"`
    const hits = srcFiles.flatMap((f) => {
      const n = readFileSync(f, "utf-8").split(needle).length - 1
      return n > 0 ? [`${path.relative(srcRoot, f)} x${n}`] : []
    })
    expect(hits, `${needle} must be emitted exactly once in src/ (found: ${hits.join(", ") || "none"})`).toHaveLength(1)
    expect(hits[0].endsWith(" x1"), `${needle} emitted more than once in ${hits[0]}`).toBe(true)
  })
})
