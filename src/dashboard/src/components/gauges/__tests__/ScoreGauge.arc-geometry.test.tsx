import { render } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { ScoreGauge } from "../ScoreGauge"

// Arc GEOMETRY, not presence. The colour/numeral tests in ScoreGauge.test.tsx
// all passed while every gauge in the dashboard drew mirrored: the fill end
// point was reflected about the centre, so 20/100 rendered ~90% full, 23/25
// rendered ~2% full, and a perfect 25/25 rendered an EMPTY arc. These tests
// read the fill path's end point and assert where on the semicircle it lands.

// The fill is the second <path>; the first is the background track.
function fillEnd(container: HTMLElement) {
  const paths = container.querySelectorAll("svg path")
  const track = paths[0].getAttribute("d")!
  const fill = paths[1]?.getAttribute("d")
  const nums = (d: string) => d.match(/-?\d+(\.\d+)?/g)!.map(Number)
  // track: M startX startY A r r 0 0 1 endX endY
  const [startX, , r] = nums(track)
  const f = fill ? nums(fill) : null
  return { startX, r, endX: f ? f[f.length - 2] : null, endY: f ? f[f.length - 1] : null }
}

// Fraction of the semicircle's horizontal span the fill reaches (0 = left end, 1 = right end).
function horizontalReach(score: number, maxValue: number) {
  const { container } = render(<ScoreGauge score={score} maxValue={maxValue} label="x" />)
  const { startX, r, endX } = fillEnd(container)
  return (endX! - startX) / (2 * r)
}

// Expected reach for a fraction f along the arc: x = cx - r*cos(f*pi).
const expected = (f: number) => (1 - Math.cos(f * Math.PI)) / 2

describe("ScoreGauge arc geometry", () => {
  it.each([
    [20, 100],
    [23, 25],
    [11, 25],
    [50, 100],
    [78, 100],
  ])("fills %i/%i to the matching point on the arc", (score, maxValue) => {
    expect(horizontalReach(score, maxValue)).toBeCloseTo(expected(score / maxValue), 2)
  })

  it("a low score fills less of the arc than a high score", () => {
    expect(horizontalReach(20, 100)).toBeLessThan(horizontalReach(80, 100))
    expect(horizontalReach(11, 25)).toBeLessThan(horizontalReach(23, 25))
  })

  it("a perfect score reaches the right end of the arc (not an empty arc)", () => {
    expect(horizontalReach(25, 25)).toBeCloseTo(1, 2)
  })

  it("a score of 20/100 fills under a quarter of the horizontal span", () => {
    expect(horizontalReach(20, 100)).toBeLessThan(0.25)
  })
})
