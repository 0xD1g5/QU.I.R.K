// Phase 184.3-05 (SCORE-03) — the single module that owns frontend timestamp DISPLAY POLICY.
//
// Once the API serialization boundary stamps an offset (`+00:00`, D-02/D-03), the Date constructor
// parses every instant correctly on its own — this module does not exist to fix the parse. It
// exists because CONTEXT.md D-08 requires exactly one place where timezone, zone label, locale,
// and format are decided, rather than the sibling-drift split (ScanDateBadge.tsx / ScanSelector.tsx
// each hand-rolling an identical formatter) that SC-4 exists to close. D-12 is the default
// behavior — browser-local WITH an explicit short zone label (e.g. "Sep 4, 2026 11:12 AM EDT") —
// and D-13 is the override: passing `{ timeZone: "UTC" }` yields the labeled-UTC form the Python
// report renderers already emit ("%Y-%m-%d %H:%M UTC"), so `/print` and the four export paths can
// agree with the interactive dashboard on the same convention.
//
// `toDate` is the sole permitted Date-constructor-with-an-argument call site in `src/dashboard/src/` once
// plans 06/07 migrate every other call site onto this module — the plan-10 vitest source-scan
// gate (D-09) enforces that at run time rather than via a hand-maintained list.

export type DateInput = string | number | Date | null | undefined

export interface DateTimeOptions {
  /** IANA zone name, e.g. "UTC". Undefined lets Intl resolve the browser/ambient zone (D-12). */
  timeZone?: string
  /** Defaults to "en-US", matching every call site this module replaces. */
  locale?: string
}

/** Em dash — matches lib/cert-parse.ts's null-placeholder convention. */
export const EMPTY_PLACEHOLDER = "—"

const DEFAULT_LOCALE = "en-US"

/**
 * Parse a `DateInput` into a `Date`, or `null` when the value is absent or unparseable.
 *
 * - `null` / `undefined` / `""` → `null`
 * - `Date` instances are returned unchanged
 * - `number` is treated as epoch milliseconds
 * - `string` is parsed via the Date constructor — the ONE permitted Date-constructor-with-an-
 *   argument call site in `src/dashboard/src/`; every other timestamp parse in the codebase must
 *   go through this function (enforced by the plan-10 vitest run-time source scan, D-09)
 * - Any value producing `Number.isNaN(d.getTime())` → `null` (never a silently-broken Date)
 */
export function toDate(value: DateInput): Date | null {
  if (value === null || value === undefined || value === "") return null
  const d = value instanceof Date ? value : new Date(value) // sole permitted Date-constructor-with-argument call
  return Number.isNaN(d.getTime()) ? null : d
}

/**
 * "Sep 4, 2026 11:12 AM EDT" — date + time-of-day + a short zone label.
 *
 * The zone label is D-12's requirement: it makes a screenshot reconcilable against a client's
 * own logs regardless of which browser/OS timezone rendered it. `opts.timeZone` overrides the
 * ambient zone — passing `"UTC"` yields the labeled-UTC form D-13 aligns `/print` to.
 * Returns `EMPTY_PLACEHOLDER` for null/undefined/unparseable input — never the string
 * `"Invalid Date"`.
 */
export function formatScanDateTime(value: DateInput, opts?: DateTimeOptions): string {
  const d = toDate(value)
  if (!d) return EMPTY_PLACEHOLDER
  return new Intl.DateTimeFormat(opts?.locale ?? DEFAULT_LOCALE, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short", // D-12: the single option that delivers the short zone label
    timeZone: opts?.timeZone,
  }).format(d)
}

/**
 * Numeric locale date + time + short zone label — the toLocale-string-method replacement for
 * compact surfaces (tables, badges). Same zone-label and override semantics as `formatScanDateTime`.
 * Returns `EMPTY_PLACEHOLDER` for null/undefined/unparseable input.
 */
export function formatDateTimeShort(value: DateInput, opts?: DateTimeOptions): string {
  const d = toDate(value)
  if (!d) return EMPTY_PLACEHOLDER
  return new Intl.DateTimeFormat(opts?.locale ?? DEFAULT_LOCALE, {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short", // D-12: the short zone label, same as formatScanDateTime
    timeZone: opts?.timeZone,
  }).format(d)
}

/**
 * "Sep 4, 2026" — a date derived from an INSTANT (e.g. a scan timestamp), rendered in the
 * resolved zone. No zone label: since no time-of-day is shown, a label would be noise rather
 * than disambiguating information. Returns `EMPTY_PLACEHOLDER` for null/undefined/unparseable
 * input.
 */
export function formatInstantDate(value: DateInput, opts?: DateTimeOptions): string {
  const d = toDate(value)
  if (!d) return EMPTY_PLACEHOLDER
  return new Intl.DateTimeFormat(opts?.locale ?? DEFAULT_LOCALE, {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: opts?.timeZone,
  }).format(d)
}

/**
 * For DATE-ONLY API fields (`cert_not_after`, `eol_date` — typed `Optional[str]` in schemas.py,
 * deliberately NOT instants; RESEARCH Pitfall 1). ALWAYS formats with `timeZone: "UTC"` so that
 * formatting in the browser's local zone can never shift the displayed calendar day backward
 * across a local-midnight boundary (e.g. "2027-01-01" must render as "Jan 1, 2027", never
 * "Dec 31, 2026" under America/New_York). No zone label — this is a fixed policy, not a caller
 * choice, so there is deliberately no `opts` parameter to override it.
 */
export function formatDateOnly(value: DateInput): string {
  const d = toDate(value)
  if (!d) return EMPTY_PLACEHOLDER
  return new Intl.DateTimeFormat(DEFAULT_LOCALE, {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC", // calendar-day-shift guard — see doc comment above
  }).format(d)
}

/**
 * "just now" / "5 min ago" / "3 days ago" — falls back to `formatInstantDate` beyond ~30 days.
 * `now` defaults to the current clock reading (via `Date.now()`, not the Date constructor —
 * exempt from the D-09 no-argument-constructor gate regardless). Returns `EMPTY_PLACEHOLDER` for
 * null/undefined/unparseable input.
 */
export function formatRelative(value: DateInput, now?: Date): string {
  const d = toDate(value)
  if (!d) return EMPTY_PLACEHOLDER
  const referenceMs = now ? now.getTime() : Date.now()
  const diffMs = referenceMs - d.getTime()
  const diffSec = Math.round(diffMs / 1000)
  const diffMin = Math.round(diffSec / 60)
  const diffHour = Math.round(diffMin / 60)
  const diffDay = Math.round(diffHour / 24)

  if (diffSec < 30) return "just now"
  if (diffMin < 60) return `${diffMin} min ago`
  if (diffHour < 24) return `${diffHour} hr ago`
  if (diffDay < 30) return `${diffDay} day${diffDay === 1 ? "" : "s"} ago`
  return formatInstantDate(d)
}
