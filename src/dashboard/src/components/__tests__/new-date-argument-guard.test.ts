import { describe, it, expect } from "vitest"
import { readFileSync, existsSync, globSync, readdirSync, statSync } from "node:fs"
import path from "node:path"

// Phase 184.3-10 (SCORE-03, D-09) -- the frontend twin of
// `tests/test_timestamp_serialization_gate.py` (plan 09). CLAUDE.md's "GSD state.* Verb
// Integrity" TOOL-04 section states the rule this gate exists to apply here: an enumeration of
// known offense/exemption sites that is hand-written and never regenerated is NOT a safeguard --
// it is decoration that reads as protection. 182-07's precedent (a hand-derived enumeration
// missing an instance inside the very command handler it audited) and plan 09's own construction
// (plan 03's hand-derived `scan.py` list missing a third real identity site, found only because
// plan 09's gate re-derives its occurrence set from source) are why this gate walks
// `src/dashboard/src/**/*.{ts,tsx}` at TEST-RUN time via `globSync`/`readdirSync`, never a
// hand-written file list.
//
// Why a naive `grep "new Date("` would false-positive into uselessness: three call sites read
// the ambient clock with a bare, no-argument `new Date()` -- `QRAMMProvider.tsx:81`,
// `certificates.tsx:21`, `executive.tsx:138` (per D-09/CONTEXT.md). A substring grep flags all
// three, and the only way to keep the gate green is to allowlist them by name -- which is exactly
// the file-list-that-drifts failure this gate exists to prevent. This gate instead distinguishes
// them by ARGUMENT PRESENCE, a structural property of the call syntax itself: `new Date()` and
// `new Date( )` (whitespace only) are auto-exempt by construction, with no allowlist entry
// possible or needed for them. Only `new Date(<something>)` -- an attempt to PARSE a value, which
// is where the 4-hour-skew defect this phase fixes actually lived -- is in scope.
//
// The one legitimate argument-bearing call site is `lib/datetime.ts::toDate` -- the sole
// permitted `new Date(value)` in `src/dashboard/src/` once plans 06/07 migrated every component
// and page site onto it (184.3-06-SUMMARY.md, 184.3-07-SUMMARY.md). Any OTHER argument-bearing
// site must either be exempted by living in `lib/datetime.ts` itself, or carry an inline
// disposition comment containing the literal marker string defined below
// (`DISPOSITION_MARKER`), on the offending line or the line immediately above it -- mirroring the
// "identity, not instant" inline-comment convention plan 09's pytest gate recognizes. As of this
// plan, the real tree needs ZERO such comments (the four `cert_not_after`/`eol_date` date-only
// sites from plan 07 call `formatDateOnly(...)`, not `new Date(...)`, directly) -- but a future
// legitimate site should write:
//
//   // new Date argument disposition (SCORE-03/D-09): <reason>
//
// KNOWN CI LIMITATION (state honestly, do not paper over): the `Linux Full Suite` CI job never
// installs Node/npm for `src/dashboard/` (CLAUDE.md's UAT Corpus Integrity Gate section,
// `docs/uat-coverage-gaps.md`). `VITEST_TOOLCHAIN_AVAILABLE` is `False` in that job, so this gate
// substitute-checks by FILE EXISTENCE there, not by execution. A local `npx vitest run` pass is
// NOT the same guarantee as a passing CI job -- this gate is not CI-enforced today.

/** The literal marker a legitimate future argument-bearing `new Date(` call must carry, on its
 * own line or the line immediately above, to be exempted without living in `lib/datetime.ts`. */
export const DISPOSITION_MARKER = "new Date argument disposition (SCORE-03/D-09):"

/** Root of the frontend source tree this gate scans. */
const SRC_ROOT = path.resolve(__dirname, "../../")

/** The one file permitted to contain an argument-bearing `new Date(` call. Relative to SRC_ROOT,
 * posix-separated (matches `globSync`'s return convention). */
const DATETIME_MODULE_RELPATH = "lib/datetime.ts"

/**
 * Detects an argument-bearing `new Date(` call: requires a non-`)`, non-whitespace character
 * after the opening paren, tolerating whitespace (including newlines) in between. This is what
 * makes `new Date()` and `new Date( )` NOT match (the next non-whitespace char after `(` is `)`,
 * which the character class excludes), while `new Date(\n  value\n)` DOES match (whitespace,
 * including the newline, is skipped before the class is tested against `v`).
 */
const NEW_DATE_ARG_RE = /new Date\(\s*[^)\s]/g

export interface Offender {
  relPath: string
  line: number
  snippet: string
}

/**
 * Pure detector: given a file's CONTENTS and its path relative to `SRC_ROOT`, returns every
 * argument-bearing `new Date(` call not exempted by file identity or by an adjacent disposition
 * comment. This is the SAME function both the real-tree scan (below) and every synthetic case in
 * this file's second half call -- a synthetic case that reimplements the regex would prove
 * nothing about the gate.
 */
export function findNewDateArgumentOffenders(contents: string, relPath: string): Offender[] {
  const normalizedRelPath = relPath.split(path.sep).join("/")
  if (normalizedRelPath === DATETIME_MODULE_RELPATH) return []

  const offenders: Offender[] = []
  const lines = contents.split("\n")

  NEW_DATE_ARG_RE.lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = NEW_DATE_ARG_RE.exec(contents)) !== null) {
    const upToMatch = contents.slice(0, match.index)
    const lineNumber = upToMatch.split("\n").length // 1-based
    const currentLine = lines[lineNumber - 1] ?? ""
    const precedingLine = lineNumber >= 2 ? (lines[lineNumber - 2] ?? "") : ""

    if (currentLine.includes(DISPOSITION_MARKER) || precedingLine.includes(DISPOSITION_MARKER)) {
      continue
    }

    offenders.push({ relPath: normalizedRelPath, line: lineNumber, snippet: currentLine.trim() })
  }

  return offenders
}

/**
 * True when a path (relative to SRC_ROOT, posix-separated) is structurally excluded from the
 * scan: test files and `__tests__` directories. Mirrors the pytest gate's `quirk/` vs `tests/`
 * split (CONTEXT.md's "Claude's Discretion" note on vitest gate glob scope) -- excluded
 * STRUCTURALLY by the glob/filter, not as a per-file exception list.
 */
function isExcludedFromScan(relPath: string): boolean {
  const normalized = relPath.split(path.sep).join("/")
  if (normalized.includes("/__tests__/") || normalized.startsWith("__tests__/")) return true
  if (/\.test\.tsx?$/.test(normalized)) return true
  return false
}

/** Hand-rolled recursive walk, used only if `fs.globSync` is unavailable (pre-Node 22). Verified
 * present on node v26.7.0 (2026-09-05) -- this is a documented fallback, not the primary path. */
function walkRecursive(dir: string, root: string = dir): string[] {
  const out: string[] = []
  for (const entry of readdirSync(dir)) {
    const abs = path.join(dir, entry)
    const stat = statSync(abs)
    if (stat.isDirectory()) {
      out.push(...walkRecursive(abs, root))
    } else if (/\.(ts|tsx)$/.test(entry)) {
      out.push(path.relative(root, abs).split(path.sep).join("/"))
    }
  }
  return out
}

/**
 * Enumerates every non-excluded `.ts`/`.tsx` file under `SRC_ROOT`, relative-path,
 * posix-separated. Never a hand-written list -- this is the run-time re-derivation TOOL-04
 * requires. Prefers `fs.globSync` (Node 22+, confirmed on node v26.7.0); falls back to
 * `readdirSync` walk if unavailable in whatever Node runs this suite.
 */
export function enumerateProductionFiles(): string[] {
  let all: string[]
  if (typeof globSync === "function") {
    all = globSync("**/*.{ts,tsx}", { cwd: SRC_ROOT }).map((p) => p.split(path.sep).join("/"))
  } else {
    // Documented fallback -- see walkRecursive's comment.
    all = walkRecursive(SRC_ROOT)
  }
  return all.filter((p) => !isExcludedFromScan(p))
}

/**
 * Disposition ledger for argument-bearing `new Date(` sites that cannot use the inline-comment
 * mechanism (e.g. because the site is intentionally hard to annotate in place). Currently EMPTY:
 * the post-plan-07 tree needs no ledger entries -- the only argument-bearing call left outside
 * `lib/datetime.ts` was closed by plans 06/07's migration, and the four `cert_not_after`/
 * `eol_date` date-only sites call `formatDateOnly(...)`, which contains no `new Date(` of its
 * own. Kept as a live, validated mechanism (not deleted) because a future site may need it, and
 * the validator plus the synthetic-entry tests below prove the mechanism works even at zero
 * real entries.
 *
 * Key shape: "<relPath>:<line>" (or a stable nearby identifier). Value: a non-blank reason.
 */
export const DISPOSITIONS: Record<string, string> = {}

export interface LedgerProblem {
  key: string
  reason: string
}

/**
 * Validates the disposition ledger: every entry must have a non-blank reason, and every entry's
 * file must still exist (staleness check -- mirrors the pytest gate's ledger validator and avoids
 * the line-number-fragility class `tests/test_skip_registry.py` is documented to suffer from).
 */
export function validateDispositionLedger(ledger: Record<string, string>): LedgerProblem[] {
  const problems: LedgerProblem[] = []
  for (const [key, reason] of Object.entries(ledger)) {
    if (!reason || !reason.trim()) {
      problems.push({ key, reason: "blank reason" })
      continue
    }
    const relPath = key.split(":")[0]
    const abs = path.resolve(SRC_ROOT, relPath)
    if (!existsSync(abs)) {
      problems.push({ key, reason: `stale -- ${relPath} does not exist under ${SRC_ROOT}` })
    }
  }
  return problems
}

/** Runs the full real-tree scan: every production file, every offender, disposition-suppressed
 * or ledger-suppressed callers excluded. */
function scanRealTree(): Offender[] {
  const offenders: Offender[] = []
  for (const relPath of enumerateProductionFiles()) {
    const abs = path.resolve(SRC_ROOT, relPath)
    const contents = readFileSync(abs, "utf8")
    for (const offender of findNewDateArgumentOffenders(contents, relPath)) {
      if (`${offender.relPath}:${offender.line}` in DISPOSITIONS) continue
      offenders.push(offender)
    }
  }
  return offenders
}

describe("new Date argument guard (SCORE-03, D-09)", () => {
  it("reports zero offenders against the real tree", () => {
    const offenders = scanRealTree()
    const message = offenders
      .map((o) => `${o.relPath}:${o.line}: ${o.snippet}`)
      .join("\n")
    expect(offenders, `Undispositioned argument-bearing new Date( calls found:\n${message}`).toHaveLength(0)
  })

  it("has a valid disposition ledger (non-blank reasons, no stale file references)", () => {
    const problems = validateDispositionLedger(DISPOSITIONS)
    expect(problems, JSON.stringify(problems)).toHaveLength(0)
  })

  it("proves the ledger validator actually fires, via a synthetic entry", () => {
    const blankReason = validateDispositionLedger({ "lib/datetime.ts:1": "" })
    expect(blankReason).toHaveLength(1)
    expect(blankReason[0].reason).toBe("blank reason")

    const staleFile = validateDispositionLedger({
      "lib/this-file-does-not-exist-anywhere.ts:1": "a perfectly good reason",
    })
    expect(staleFile).toHaveLength(1)
    expect(staleFile[0].reason).toContain("stale")
  })

  it("excludes __tests__ directories and *.test.ts(x) files structurally, not by allowlist", () => {
    const files = enumerateProductionFiles()
    expect(files.some((f) => f.includes("__tests__"))).toBe(false)
    expect(files.some((f) => /\.test\.tsx?$/.test(f))).toBe(false)
    // Sanity: the enumeration is not accidentally empty.
    expect(files).toContain(DATETIME_MODULE_RELPATH)
    expect(files.length).toBeGreaterThan(10)
  })
})

// ---------------------------------------------------------------------------------------------
// Task 2: synthetic proof the detector fires on every shape in the plan's <behavior> block, all
// driven through the SAME `findNewDateArgumentOffenders` / `validateDispositionLedger` functions
// the real scan above uses. No case here reimplements the regex.
// ---------------------------------------------------------------------------------------------

describe("findNewDateArgumentOffenders (synthetic proof, Task 2)", () => {
  it("reports an argument-bearing call outside lib/datetime.ts", () => {
    const src = `const scannedAt = new Date(someIso)\n`
    const offenders = findNewDateArgumentOffenders(src, "pages/example.tsx")
    expect(offenders).toHaveLength(1)
    expect(offenders[0].line).toBe(1)
  })

  it("does NOT report a no-argument clock read", () => {
    const src = `const now = new Date()\n`
    expect(findNewDateArgumentOffenders(src, "pages/example.tsx")).toHaveLength(0)
  })

  it("does NOT report a whitespace-only-paren call", () => {
    const src = `const now = new Date( )\n`
    expect(findNewDateArgumentOffenders(src, "pages/example.tsx")).toHaveLength(0)
  })

  it("reports a multi-line argument call -- the regex is not defeated by formatting", () => {
    const src = `const scannedAt = new Date(\n  someIso\n)\n`
    const offenders = findNewDateArgumentOffenders(src, "pages/example.tsx")
    expect(offenders).toHaveLength(1)
    expect(offenders[0].line).toBe(1) // line of the `new Date(` call itself
  })

  it("suppresses a reported call whose OWN line carries the disposition marker", () => {
    const src = `const x = new Date(someIso) // ${DISPOSITION_MARKER} synthetic test reason\n`
    expect(findNewDateArgumentOffenders(src, "pages/example.tsx")).toHaveLength(0)
  })

  it("suppresses a reported call whose PRECEDING line carries the disposition marker", () => {
    const src = `// ${DISPOSITION_MARKER} synthetic test reason\nconst x = new Date(someIso)\n`
    expect(findNewDateArgumentOffenders(src, "pages/example.tsx")).toHaveLength(0)
  })

  it("does NOT suppress a call whose marker is two lines away (not adjacent)", () => {
    const src = `// ${DISPOSITION_MARKER} synthetic test reason\n\nconst x = new Date(someIso)\n`
    expect(findNewDateArgumentOffenders(src, "pages/example.tsx")).toHaveLength(1)
  })

  it("exempts lib/datetime.ts entirely, even for an argument-bearing call", () => {
    const src = `const d = new Date(value) // sole permitted call\n`
    expect(findNewDateArgumentOffenders(src, "lib/datetime.ts")).toHaveLength(0)
  })

  it("ledger validator reports a blank-reason entry", () => {
    const problems = validateDispositionLedger({ "lib/datetime.ts:44": "   " })
    expect(problems).toHaveLength(1)
    expect(problems[0].reason).toBe("blank reason")
  })

  it("ledger validator reports a stale (nonexistent-file) entry", () => {
    const problems = validateDispositionLedger({
      "pages/this-file-was-deleted.tsx:12": "some historical reason",
    })
    expect(problems).toHaveLength(1)
    expect(problems[0].reason).toContain("stale")
  })

  it("ledger validator passes a well-formed entry pointing at a real file", () => {
    const problems = validateDispositionLedger({
      [`${DATETIME_MODULE_RELPATH}:44`]: "a perfectly good synthetic reason",
    })
    expect(problems).toHaveLength(0)
  })
})
