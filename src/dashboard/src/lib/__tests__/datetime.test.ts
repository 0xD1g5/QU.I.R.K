// Phase 184.3-05 (SCORE-03, D-08/D-12/D-13) — TZ-pinned contract tests for lib/datetime.ts.
//
// Every rendered-text assertion below uses toContain/toMatch, never a full-string toBe() on
// Intl output. Intl.DateTimeFormat's exact punctuation and spacing (comma placement, narrow
// no-break spaces before AM/PM, etc.) vary across ICU versions and Node builds — a brittle
// full-string assertion is how this suite would end up disabled instead of fixed the next time
// the CI runner's Node/ICU version changes. We assert on the wall-clock digits and the zone
// token separately instead.

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import {
  toDate,
  formatScanDateTime,
  formatDateTimeShort,
  formatInstantDate,
  formatDateOnly,
  formatAxisTick,
  formatRelative,
  EMPTY_PLACEHOLDER,
} from "../datetime"

describe("datetime.ts — America/New_York ambient zone", () => {
  beforeEach(() => vi.stubEnv("TZ", "America/New_York"))
  afterEach(() => vi.unstubAllEnvs())

  it("formatScanDateTime renders the wall-clock hour 11:12 and zone token EDT for an offset-bearing instant", () => {
    const out = formatScanDateTime("2026-09-04T15:12:58+00:00")
    expect(out).toContain("11:12")
    expect(out).not.toContain("3:12")
    expect(out).toMatch(/EDT/)
  })

  it("formatScanDateTime with timeZone: UTC override renders 3:12 and zone token UTC", () => {
    const out = formatScanDateTime("2026-09-04T15:12:58+00:00", { timeZone: "UTC" })
    expect(out).toContain("3:12")
    expect(out).toMatch(/UTC/)
  })

  it("formatDateOnly renders Jan 1, 2027 (not Dec 31, 2026) for a date-only field — the calendar-day-shift regression the fixed-UTC policy prevents", () => {
    // Under America/New_York, midnight UTC on 2027-01-01 is still 2026-12-31 local. formatDateOnly
    // must NOT format in the ambient/local zone for date-only fields, or the calendar day shown to
    // the operator shifts backward by one day relative to the value stored/reported by the API.
    const out = formatDateOnly("2027-01-01")
    expect(out).toContain("Jan 1, 2027")
    expect(out).not.toContain("Dec 31, 2026")
  })

  it("formatInstantDate renders Sep 4, 2026 with no zone token", () => {
    const out = formatInstantDate("2026-09-04T15:12:58+00:00")
    expect(out).toContain("Sep 4, 2026")
    expect(out).not.toMatch(/EDT|UTC|GMT/)
  })

  it("formatRelative with an explicit now 5 minutes later renders a string containing 5 and min", () => {
    const input = "2026-09-04T15:12:58+00:00"
    const now = new Date("2026-09-04T15:17:58+00:00")
    const out = formatRelative(input, now)
    expect(out).toContain("5")
    expect(out).toMatch(/min/)
  })
})

describe("datetime.ts — UTC ambient zone (proves default follows ambient zone, not a hard-coded one)", () => {
  beforeEach(() => vi.stubEnv("TZ", "UTC"))
  afterEach(() => vi.unstubAllEnvs())

  it("formatScanDateTime renders 3:12 and zone token UTC when the ambient zone itself is UTC", () => {
    const out = formatScanDateTime("2026-09-04T15:12:58+00:00")
    expect(out).toContain("3:12")
    expect(out).toMatch(/UTC/)
  })
})

describe("datetime.ts — null / undefined / unparseable handling", () => {
  it("toDate returns null for null, undefined and empty string", () => {
    expect(toDate(null)).toBeNull()
    expect(toDate(undefined)).toBeNull()
    expect(toDate("")).toBeNull()
  })

  it("toDate returns null for an unparseable string (NaN guard)", () => {
    expect(toDate("not-a-date")).toBeNull()
  })

  it("formatScanDateTime returns the em-dash placeholder for an unparseable string, never the literal 'Invalid Date'", () => {
    const out = formatScanDateTime("not-a-date")
    expect(out).toBe(EMPTY_PLACEHOLDER)
    expect(out).not.toContain("Invalid Date")
  })

  it("every formatter returns the em-dash placeholder for null/undefined input", () => {
    expect(formatScanDateTime(null)).toBe(EMPTY_PLACEHOLDER)
    expect(formatDateTimeShort(undefined)).toBe(EMPTY_PLACEHOLDER)
    expect(formatInstantDate(null)).toBe(EMPTY_PLACEHOLDER)
    expect(formatDateOnly(undefined)).toBe(EMPTY_PLACEHOLDER)
    expect(formatRelative(null)).toBe(EMPTY_PLACEHOLDER)
  })
})

describe("datetime.ts — formatDateTimeShort", () => {
  beforeEach(() => vi.stubEnv("TZ", "America/New_York"))
  afterEach(() => vi.unstubAllEnvs())

  it("renders a numeric date, time and short zone label", () => {
    const out = formatDateTimeShort("2026-09-04T15:12:58+00:00")
    expect(out).toContain("11:12")
    expect(out).toMatch(/EDT/)
  })
})

describe("datetime.ts — formatAxisTick (plan 184.3-07, dense chart-axis ticks)", () => {
  beforeEach(() => vi.stubEnv("TZ", "America/New_York"))
  afterEach(() => vi.unstubAllEnvs())

  it("renders a compact numeric date+time with NO zone label", () => {
    const out = formatAxisTick("2026-09-04T15:12:58+00:00")
    expect(out).toContain("11:12")
    expect(out).not.toContain("3:12")
    expect(out).not.toMatch(/EDT|UTC/)
  })

  it("returns the em-dash placeholder for null/undefined/unparseable input", () => {
    expect(formatAxisTick(null)).toBe(EMPTY_PLACEHOLDER)
    expect(formatAxisTick(undefined)).toBe(EMPTY_PLACEHOLDER)
    expect(formatAxisTick("not-a-date")).toBe(EMPTY_PLACEHOLDER)
  })
})
