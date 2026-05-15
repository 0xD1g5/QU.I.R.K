import { describe, it, expect } from "vitest"
import { extractCN, parseDistinguishedName } from "@/lib/cert-parse"

// D-08 (WR-09): Subject/Issuer CN regex must handle RFC-2253 escaped commas.
// Regex: /CN=((?:[^,\\]|\\.)*)(,|$)/ + .replace(/\\(.)/g, '$1') post-processing.
// Anchors only to CN= (not OU=, O=, etc.).

describe("extractCN — D-08 RFC-2253-aware CN extraction", () => {
  it.each([
    ["CN=plain", "plain"],
    ["CN=plain,O=Corp", "plain"],
    ["CN=O\\,reilly", "O,reilly"],
    ["CN=Smith\\, John,O=Acme", "Smith, John"],
    ["CN=alpha\\\\beta,O=Acme", "alpha\\beta"],
  ])("extractCN(%j) → %j", (input, expected) => {
    expect(extractCN(input)).toBe(expected)
  })

  it.each([
    [null],
    [undefined],
    [""],
  ])("extractCN(%j) → em-dash sentinel", (input) => {
    expect(extractCN(input as string | null | undefined)).toBe("—")
  })

  it("passthrough on no CN= match", () => {
    expect(extractCN("O=Corp")).toBe("O=Corp")
  })

  it("regex anchors to CN= and not OU= (passthrough when CN absent)", () => {
    // OU=CNothing has no CN= prefix; helper must NOT match the CN inside OU=
    expect(extractCN("OU=CNothing")).toBe("OU=CNothing")
  })

  it("parseDistinguishedName exposes CN slot", () => {
    const parsed = parseDistinguishedName("CN=Smith\\, John,O=Acme")
    expect(parsed.CN).toBe("Smith, John")
  })
})
