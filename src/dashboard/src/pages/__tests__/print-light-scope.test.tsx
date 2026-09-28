/**
 * 213-06 (UIFIX-02, T-213-11) — proves the print surface's light-pinning
 * wrapper by rendering the real `PrintPage` component, across all three
 * return paths (loading, error, main), and settles RESEARCH's assumption
 * A3 ("wrapping the root in `className=\"light\"` is sufficient to pin
 * descendant var(--token) reads to light-theme values") as far as this
 * test environment honestly allows.
 *
 * IMPORTANT — what this file can and cannot prove, read before trusting any
 * green result here at face value:
 *
 * jsdom does NOT implement a CSS cascade/layout engine capable of resolving
 * `var(--token)` references sourced from a `<style>`-injected stylesheet.
 * `getComputedStyle()` on an element whose colour comes from a stylesheet
 * rule (rather than a literal inline style) returns the UNRESOLVED
 * `"var(--token)"` string, not the actual resolved colour — confirmed live
 * below in "jsdom does not resolve stylesheet-sourced var() references".
 * That means the strongest claim this suite can make about the PRINT_CSS
 * stylesheet rules (`.sev-CRITICAL`, `body,html`, etc.) is SOURCE-LEVEL:
 * that the rule text references the correct token name. It CANNOT verify
 * the rendered colour a real browser (or the PDF export's Chromium) would
 * paint. That gap is real, named, and owned by plan 213-09's human-UAT
 * two-PDF comparison (export once with the app left in dark mode, once in
 * light mode, and confirm the two PDFs are visually identical) — see this
 * plan's SUMMARY.md for the disclosure. This file does NOT weaken that gap
 * into a false-positive class-name check and call A3 settled; the one test
 * that touches the jsdom limitation is written so that a FUTURE jsdom/vitest
 * upgrade adding real stylesheet-cascade support would make it FAIL loudly
 * (it asserts the *unresolved* string comes back) — a deliberate trip-wire,
 * not a tautology, so whoever lands that upgrade is forced to replace it
 * with the real computed-value assertion this environment cannot yet make.
 */
import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, cleanup } from "@testing-library/react"

let scanDataReturn: { data: unknown; loading: boolean; error: string | null } = {
  data: null,
  loading: true,
  error: null,
}
let qrammReturn: {
  scoreResult: unknown
  complianceRows: unknown
  loading: boolean
  error: string | null
} = { scoreResult: null, complianceRows: null, loading: true, error: null }

vi.mock("@/hooks/useScanData", () => ({ useScanData: () => scanDataReturn }))
vi.mock("@/hooks/useQRAMMPrintData", () => ({ useQRAMMPrintData: () => qrammReturn }))

afterEach(() => {
  cleanup()
  document.body.removeAttribute("data-ready")
  scanDataReturn = { data: null, loading: true, error: null }
  qrammReturn = { scoreResult: null, complianceRows: null, loading: true, error: null }
})

describe("PrintPage — light-pinning wrapper covers all three return paths (T-213-11)", () => {
  it("wraps the loading path in the light-pinning quirk-print root", async () => {
    scanDataReturn = { data: null, loading: true, error: null }
    const { PrintPage } = await import("@/pages/print")
    const { container } = render(<PrintPage />)
    const root = container.firstElementChild as HTMLElement
    expect(root).not.toBeNull()
    expect(root.classList.contains("light")).toBe(true)
    expect(root.classList.contains("quirk-print")).toBe(true)
    expect(root.textContent).toContain("Loading scan data...")
  })

  it("wraps the error path in the light-pinning quirk-print root and drops the literal red colour", async () => {
    scanDataReturn = { data: null, loading: false, error: "scan fetch failed: 500" }
    const { PrintPage } = await import("@/pages/print")
    const { container } = render(<PrintPage />)
    const root = container.firstElementChild as HTMLElement
    expect(root).not.toBeNull()
    expect(root.classList.contains("light")).toBe(true)
    expect(root.classList.contains("quirk-print")).toBe(true)
    expect(root.textContent).toContain("scan fetch failed: 500")
    // The named CSS colour literal "red" must be gone from the error path —
    // D-14 obligation 2's one named-colour instance. It must be sourced from
    // a --print-* custom property, not a literal, and specifically the
    // theme-invariant critical token the rest of PRINT_CSS's critical/
    // vulnerable badges already use (consistency, not a fresh choice).
    expect(root.style.color).not.toBe("red")
    expect(root.style.color).toBe("var(--print-critical)")
  })

  it("wraps the main content path in the light-pinning quirk-print root alongside the injected PRINT_CSS style tag", async () => {
    scanDataReturn = {
      data: {
        meta: { scan_id: "1", scanned_at: null, total_endpoints: 0, total_findings: 0 },
        score: {
          score: null,
          rating: "UNKNOWN",
          rating_cap_reason: null,
          subscores: {
            hygiene: null,
            modern_tls: null,
            identity_trust: null,
            agility_signals: null,
            data_at_rest: null,
            data_in_motion: null,
          },
          drivers: [],
        },
        confidence: { confidence_score: 0, confidence_rating: "LOW", factor_breakdown: {} },
        findings: [],
        certificates: [],
        cbom_components: [],
        roadmap: { nodes: [], edges: [] },
        excluded_cert_count: 0,
        projected_score: null,
        identity_findings: [],
        motion_findings: [],
        dar_findings: [],
      },
      loading: false,
      error: null,
    }
    qrammReturn = { scoreResult: null, complianceRows: null, loading: false, error: null }
    const { PrintPage } = await import("@/pages/print")
    const { container } = render(<PrintPage />)
    // The style tag and the light-pinning content div are siblings inside
    // the same top-level fragment (print.tsx:428-433) — assert both exist
    // and that the content root (not the <style> tag) carries the classes.
    const styleEl = container.querySelector("style")
    expect(styleEl).not.toBeNull()
    const contentRoot = container.querySelector("div.light.quirk-print")
    expect(contentRoot).not.toBeNull()
  })
})

describe("PrintPage — light-scope token vacuity guard (D-05: this must be able to fail)", () => {
  it("the discriminating tokens this file's proof style rests on genuinely differ between :root and .light in the loaded stylesheet", () => {
    // Read the real source file, not a fixture — so a future edit that
    // accidentally collapses these values to be equal trips this guard.
    const cssPath = resolve(__dirname, "../../index.css")
    const css = readFileSync(cssPath, "utf8")
    const rootBlockMatch = css.match(/:root\s*\{([\s\S]*?)\n {2}\}/)
    const lightBlockMatch = css.match(/\.light\s*\{([\s\S]*?)\n {2}\}/)
    expect(rootBlockMatch).not.toBeNull()
    expect(lightBlockMatch).not.toBeNull()
    const rootBlock = rootBlockMatch![1]
    const lightBlock = lightBlockMatch![1]

    // --ds-text is the token print-light-scope reasoning depends on being
    // genuinely theme-dependent elsewhere in the dashboard (unlike the
    // --print-* family, which is deliberately invariant by 213-02 design).
    const rootDsText = rootBlock.match(/--ds-text:\s*([^;]+);/)?.[1]?.trim()
    const lightDsText = lightBlock.match(/--ds-text:\s*([^;]+);/)?.[1]?.trim()
    expect(rootDsText).toBeTruthy()
    expect(lightDsText).toBeTruthy()
    expect(rootDsText).not.toBe(lightDsText)

    // And the converse control: the --print-* family this plan actually
    // uses for the crux body,html rule IS deliberately identical in both
    // blocks (THEME_INVARIANT, per 213-02-SUMMARY.md) — assert that
    // invariance holds too, since the whole body,html fix depends on it.
    const rootPrintBg = rootBlock.match(/--print-bg:\s*([^;]+);/)?.[1]?.trim()
    const lightPrintBg = lightBlock.match(/--print-bg:\s*([^;]+);/)?.[1]?.trim()
    expect(rootPrintBg).toBeTruthy()
    expect(lightPrintBg).toBeTruthy()
    expect(rootPrintBg).toBe(lightPrintBg)
  })

  it("jsdom does not resolve stylesheet-sourced var() references — GAP, owner: 213-09 human-UAT two-PDF comparison", () => {
    // This is the documented reason A3 cannot be settled by a computed-style
    // assertion in this suite. It is written as a POSITIVE, falsifiable
    // claim about the current test environment's behaviour (not a weakened
    // presence check standing in for the real proof) — see the file-level
    // comment above.
    const originalClass = document.documentElement.className
    document.documentElement.className = "dark"
    const style = document.createElement("style")
    style.textContent = ":root{--probe-token:#f0f2f8}.light{--probe-token:#11141c}.probe{color:var(--probe-token)}"
    document.head.appendChild(style)
    const div = document.createElement("div")
    div.className = "light probe"
    document.body.appendChild(div)

    const computed = getComputedStyle(div).color

    // If this assertion ever starts failing, it means the test environment
    // gained real CSS custom-property resolution from stylesheets — replace
    // this whole test (and the GAP disclosure in 213-06-SUMMARY.md) with a
    // genuine computed-colour assertion (e.g. expect(computed).toBe("rgb(17, 20, 28)")).
    expect(computed).toBe("var(--probe-token)")

    document.head.removeChild(style)
    document.body.removeChild(div)
    document.documentElement.className = originalClass
  })
})
