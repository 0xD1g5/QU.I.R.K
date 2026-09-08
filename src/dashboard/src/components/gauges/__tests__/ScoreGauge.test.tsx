import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { ScoreGauge } from "../ScoreGauge"
import bands from "@/lib/severity-bands.json"

// Helper: find the colored fill path (has a quantum CSS-var stroke, not the border token)
function getColoredPath(container: HTMLElement): SVGPathElement | null {
  return container.querySelector('path[stroke^="hsl(var(--quantum"]')
}

// Covers GAUGE-01/02/03 (per-subscore color thresholds, overall-score boundaries,
// integer value display) plus SCORE-07 / Phase 188 (single-producer band
// thresholds). REWRITTEN for Phase 188: the prior version pinned fraction-space
// boundaries (a seventy-nine/eighty-hundredths pair, plus an implicit >= 0.5
// assumption) that stopped being true the moment ScoreGauge started reading
// thresholds from severity-bands.json
// instead of its own literals — every boundary below is derived from that
// import, never typed as a literal, so a stale hardcoded value cannot pass.
//
// Deliberate visual change (flag for human UAT — see 188-VALIDATION.md):
// green now begins at score 70 (was 80, an implicit 0.8 fraction cutoff) and
// red now begins below score 35 (was below 50, an implicit 0.5 cutoff).
describe("ScoreGauge", () => {
  it("renders green when subscore equals its category max (25/25 -> 100 in score-space)", () => {
    const { container } = render(<ScoreGauge score={25} maxValue={25} label="Hygiene" />)
    const fill = getColoredPath(container)
    expect(fill).not.toBeNull()
    expect(fill!.getAttribute("stroke")).toBe("hsl(var(--quantum-safe))")
    expect(screen.getByText("25")).toBeTruthy()
  })

  it("renders red when subscore is low (3/25 -> 12 in score-space, below FAIR)", () => {
    const { container } = render(<ScoreGauge score={3} maxValue={25} label="Agility" />)
    const fill = getColoredPath(container)
    expect(fill).not.toBeNull()
    expect(fill!.getAttribute("stroke")).toBe("hsl(var(--quantum-vulnerable))")
    expect(screen.getByText("3")).toBeTruthy()
  })

  it("renders safe at the GOOD boundary and at-risk just below it, default maxValue", () => {
    const goodThreshold = bands.band_thresholds.GOOD

    // At-risk: one point below GOOD's threshold (MODERATE band)
    const { container: containerBelow } = render(
      <ScoreGauge score={goodThreshold - 1} label="Overall Readiness" />
    )
    const fillBelow = getColoredPath(containerBelow)
    expect(fillBelow).not.toBeNull()
    expect(fillBelow!.getAttribute("stroke")).toBe("hsl(var(--quantum-at-risk))")

    // Safe: exactly at GOOD's threshold
    const { container: containerAt } = render(
      <ScoreGauge score={goodThreshold} label="Overall Readiness" />
    )
    const fillAt = getColoredPath(containerAt)
    expect(fillAt).not.toBeNull()
    expect(fillAt!.getAttribute("stroke")).toBe("hsl(var(--quantum-safe))")
  })

  it("renders vulnerable below the FAIR boundary and at-risk at the FAIR boundary, default maxValue", () => {
    const fairThreshold = bands.band_thresholds.FAIR

    // Vulnerable: one point below FAIR's threshold (POOR band, the implicit floor)
    const { container: containerBelow } = render(
      <ScoreGauge score={fairThreshold - 1} label="Overall Readiness" />
    )
    const fillBelow = getColoredPath(containerBelow)
    expect(fillBelow).not.toBeNull()
    expect(fillBelow!.getAttribute("stroke")).toBe("hsl(var(--quantum-vulnerable))")

    // At-risk: exactly at FAIR's threshold
    const { container: containerAt } = render(
      <ScoreGauge score={fairThreshold} label="Overall Readiness" />
    )
    const fillAt = getColoredPath(containerAt)
    expect(fillAt).not.toBeNull()
    expect(fillAt!.getAttribute("stroke")).toBe("hsl(var(--quantum-at-risk))")
  })

  it("renders vulnerable for a legacy caller passing a low score with NO maxValue", () => {
    // Proves default maxValue=100 behavior is unchanged — well below FAIR is vulnerable
    const belowFair = bands.band_thresholds.FAIR - 10
    const { container } = render(<ScoreGauge score={belowFair} label="Legacy" />)
    const fill = getColoredPath(container)
    expect(fill).not.toBeNull()
    expect(fill!.getAttribute("stroke")).toBe("hsl(var(--quantum-vulnerable))")
  })

  it("isOverall still overrides the color with hsl(var(--accent)) regardless of score", () => {
    const { container } = render(
      <ScoreGauge score={10} label="Overall Readiness" isOverall />
    )
    const fill = container.querySelector('path[stroke="hsl(var(--accent))"]')
    expect(fill).not.toBeNull()
  })

  it("an explicit strokeColor prop wins over both isOverall and the band color", () => {
    const { container } = render(
      <ScoreGauge score={90} label="Overall Readiness" isOverall strokeColor="hsl(var(--custom))" />
    )
    const fill = container.querySelector('path[stroke="hsl(var(--custom))"]')
    expect(fill).not.toBeNull()
  })
})
