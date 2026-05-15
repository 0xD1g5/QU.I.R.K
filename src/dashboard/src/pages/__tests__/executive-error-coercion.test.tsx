import { describe, it, expect } from "vitest"
import { coerceErrorDetail } from "@/pages/executive"

// D-02 (WR-06): defensive coercion of unknown response body shapes
// to a non-undefined, non-throwing string suitable for surfacing
// to operators in the executive PDF error UI.

describe("coerceErrorDetail — D-02 (WR-06) defensive body.detail coercion", () => {
  it("returns body.detail when it is a string ({detail: 'rate limited'})", () => {
    expect(coerceErrorDetail({ detail: "rate limited" })).toBe("rate limited")
  })

  it("returns String(body) when body is a raw string", () => {
    expect(coerceErrorDetail("oops")).toBe("oops")
  })

  it("returns 'Unknown error' when body is null or undefined", () => {
    expect(coerceErrorDetail(null)).toBe("Unknown error")
    expect(coerceErrorDetail(undefined)).toBe("Unknown error")
  })

  it("falls back to String(body) when body.detail is non-string (e.g. number)", () => {
    // Not a string detail -> guard fails, fallback applies. We just
    // require the result to be a non-empty string and NOT equal to the
    // numeric detail (i.e. we do not naively coerce number-as-detail).
    const out = coerceErrorDetail({ detail: 500 })
    expect(typeof out).toBe("string")
    expect(out.length).toBeGreaterThan(0)
    expect(out).not.toBe("500")
  })

  it("returns String(body) when body is an empty object (no detail)", () => {
    const out = coerceErrorDetail({})
    expect(typeof out).toBe("string")
    expect(out.length).toBeGreaterThan(0)
  })
})
