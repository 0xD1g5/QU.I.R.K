import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { ScoreGauge } from "../ScoreGauge"

// Helper: find the colored fill path (has a quantum CSS-var stroke, not the border token)
function getColoredPath(container: HTMLElement): SVGPathElement | null {
  return container.querySelector('path[stroke^="hsl(var(--quantum"]')
}

describe("ScoreGauge", () => {
  it("renders green when subscore equals its category max (25/25)", () => {
    const { container } = render(<ScoreGauge score={25} maxValue={25} label="Hygiene" />)
    const fill = getColoredPath(container)
    expect(fill).not.toBeNull()
    expect(fill!.getAttribute("stroke")).toBe("hsl(var(--quantum-safe))")
    expect(screen.getByText("25")).toBeTruthy()
  })

  it("renders red when subscore is low (3/25)", () => {
    const { container } = render(<ScoreGauge score={3} maxValue={25} label="Agility" />)
    const fill = getColoredPath(container)
    expect(fill).not.toBeNull()
    expect(fill!.getAttribute("stroke")).toBe("hsl(var(--quantum-vulnerable))")
    expect(screen.getByText("3")).toBeTruthy()
  })

  it("renders amber at overall=79 and green at the >= 0.8 boundary (overall=80), default maxValue", () => {
    // Amber: 79/100 = 0.79 fraction (< 0.8 threshold)
    const { container: container79 } = render(<ScoreGauge score={79} label="Overall Readiness" />)
    const fill79 = getColoredPath(container79)
    expect(fill79).not.toBeNull()
    expect(fill79!.getAttribute("stroke")).toBe("hsl(var(--quantum-at-risk))")

    // Green: 80/100 = 0.80 fraction (>= 0.8 threshold)
    const { container: container80 } = render(<ScoreGauge score={80} label="Overall Readiness" />)
    const fill80 = getColoredPath(container80)
    expect(fill80).not.toBeNull()
    expect(fill80!.getAttribute("stroke")).toBe("hsl(var(--quantum-safe))")
  })

  it("renders red for a legacy caller passing score=25 with NO maxValue (25/100 = 0.25 < 0.5)", () => {
    // Proves default maxValue=100 behavior is unchanged — 25 out of 100 is red
    const { container } = render(<ScoreGauge score={25} label="Legacy" />)
    const fill = getColoredPath(container)
    expect(fill).not.toBeNull()
    expect(fill!.getAttribute("stroke")).toBe("hsl(var(--quantum-vulnerable))")
  })
})
