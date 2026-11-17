// Phase 235.3 COVTRUTH-04 / D-09 — phase record -> empty-state text.
import { describe, it, expect } from "vitest"
import {
  emptyStateFor,
  humanSkipReason,
  isPhaseError,
  phaseRecordText,
  COVERAGE_SKIP_ADVISORY_CATEGORIES,
} from "../coverage-reason"
import type { ScanCoverageResponse, ScanCoveragePhase } from "@/types/api"

function phase(over: Partial<ScanCoveragePhase>): ScanCoveragePhase {
  return {
    phase_name: "db_scanning",
    label: "Database",
    status: "ran",
    reason: null,
    detail: null,
    duration_sec: 1,
    ...over,
  }
}

function cov(phases: ScanCoveragePhase[], recorded = true): ScanCoverageResponse {
  return { recorded, ran: 0, skipped: 0, phases }
}

// UI review fix 2: a machine code followed by a colon (`unexpected_response:`,
// `auth-failed:`), in either spelling.
const RAW_KIND_TOKEN = /\b[a-z]+[-_][a-z]+(?:[-_][a-z]+)*:/

describe("emptyStateFor", () => {
  it("returns the fallback when there is no coverage", () => {
    expect(emptyStateFor(undefined, ["db_scanning"], "FALLBACK")).toBe("FALLBACK")
    expect(emptyStateFor(null, ["db_scanning"], "FALLBACK")).toBe("FALLBACK")
  })

  it("returns the fallback when coverage was not recorded", () => {
    expect(emptyStateFor(cov([phase({})], false), ["db_scanning"], "FALLBACK")).toBe("FALLBACK")
  })

  it("returns the fallback for a disabled-by-config phase", () => {
    const c = cov([phase({ status: "skipped", reason: "disabled-by-config" })])
    expect(emptyStateFor(c, ["db_scanning"], "FALLBACK")).toBe("FALLBACK")
  })

  it("names a missing-credentials skip with its label and detail", () => {
    const c = cov([
      phase({
        phase_name: "s3_scanning",
        label: "Object storage",
        status: "skipped",
        reason: "missing-credentials",
        detail: "1 of 1 targets had no credentials",
      }),
    ])
    expect(emptyStateFor(c, ["s3_scanning"], "FALLBACK")).toBe(
      "Skipped: missing credentials (Object storage) — 1 of 1 targets had no credentials",
    )
  })

  it("explains an internal-target-refused skip as server policy", () => {
    const c = cov([
      phase({ phase_name: "jwt_scanning", label: "JWT", status: "skipped", reason: "internal-target-refused" }),
    ])
    expect(emptyStateFor(c, ["jwt_scanning"], "F")).toContain("internal targets refused by server policy")
  })

  it("mentions only the skipped phase when one of two phases ran", () => {
    const c = cov([
      phase({ phase_name: "s3_scanning", label: "S3" }),
      phase({ phase_name: "blob_scanning", label: "Blob", status: "skipped", reason: "auth-failed" }),
    ])
    const text = emptyStateFor(c, ["s3_scanning", "blob_scanning"], "F")
    expect(text).toContain("credentials rejected (Blob)")
    expect(text).not.toContain("S3")
  })

  it("reports a ran phase with no rows as Ran, 0 results", () => {
    expect(emptyStateFor(cov([phase({})]), ["db_scanning"], "F")).toBe("Ran, 0 results (Database)")
  })

  it("names a phase that raised as failed, never as no target answered", () => {
    // C-WR-04: PhaseRecorder.record_failed writes reason "failed" with the
    // exception text when the phase itself raised.
    const c = cov([
      phase({ status: "skipped", reason: "failed", detail: "ModuleNotFoundError: No module named 'psycopg2'" }),
    ])
    const text = emptyStateFor(c, ["db_scanning"], "F")
    expect(text).toBe(
      "Failed: the scanner stopped with an error (Database) — ModuleNotFoundError: No module named 'psycopg2'",
    )
    expect(text).not.toContain("no target answered")
    expect(text).not.toContain("Skipped")
  })

  it("keeps no target answered for the every-target-unreachable failed row", () => {
    const c = cov([
      phase({
        status: "skipped",
        reason: "failed",
        detail: "2 of 2 targets did not answer: db1:5432 (unreachable: timed out), db2:5432 (unreachable)",
      }),
    ])
    expect(emptyStateFor(c, ["db_scanning"], "F")).toBe(
      "Skipped: no target answered (Database) — 2 of 2 targets did not answer: db1:5432 (timed out), db2:5432 (unreachable)",
    )
  })

  it("returns the fallback when a listed phase is absent from the record", () => {
    expect(emptyStateFor(cov([phase({})]), ["db_scanning", "vault_scanning"], "FALLBACK")).toBe("FALLBACK")
  })
})

describe("humanSkipReason", () => {
  it("maps the four reasons with bespoke wording and keeps the rest", () => {
    // Without the detail the two "failed" writers cannot be told apart, so the
    // bare wording claims no cause (C-WR-04).
    expect(humanSkipReason("failed")).toBe("failed or no target answered")
    expect(humanSkipReason("auth-failed")).toBe("credentials rejected")
    expect(humanSkipReason("missing-extra")).toBe("missing-extra")
    expect(humanSkipReason(null)).toBe("unclassified")
  })

  it("explains an unexpected-response skip without the raw slug", () => {
    // Phase 238 D-10 / UI-SPEC U3: the detail carries the underscore kind, never the slug.
    expect(humanSkipReason("unexpected-response")).toBe(
      "a target answered with something other than the expected document",
    )
    const record = {
      label: "SAML",
      reason: "unexpected-response",
      detail:
        "1 of 1 targets answered with something other than the expected document: https://idp.example/metadata (unexpected_response: not SAML metadata (HTML page))",
    }
    const text = phaseRecordText(record)
    expect(text).toBe(
      "Skipped (SAML) — 1 of 1 targets answered with something other than the expected document: https://idp.example/metadata (not SAML metadata (HTML page))",
    )
    expect(text).not.toContain("unexpected-response")
    expect(text).not.toContain("unexpected_response")
    expect(text).not.toMatch(RAW_KIND_TOKEN)
    expect(text.split("answered with something other than the expected document").length - 1).toBe(1)
    expect(isPhaseError(record)).toBe(false)
  })

  it("strips every per-target outcome code from a phase record sentence", () => {
    // UI review fix 1/2 (237 lesson 2): `<kind>: ` inside the per-target
    // parentheses is a machine code, so no user-facing sentence shows it.
    const record = {
      label: "JWT",
      reason: "auth-failed",
      detail:
        "2 of 4 targets failed authentication (2 more did not answer for other reasons): https://a.example (auth_failed: HTTP 401: configured credentials rejected), https://b.example (missing_credentials), https://c.example (unexpected_response: HTTP 404), https://d.example (unreachable: timed out)",
    }
    const text = phaseRecordText(record)
    expect(text).toBe(
      "Skipped: credentials rejected (JWT) — 2 of 4 targets failed authentication (2 more did not answer for other reasons): https://a.example (HTTP 401: configured credentials rejected), https://b.example (missing credentials), https://c.example (HTTP 404), https://d.example (timed out)",
    )
    expect(text).not.toMatch(RAW_KIND_TOKEN)
    for (const kind of ["auth_failed", "missing_credentials", "unexpected_response", "unreachable:"]) {
      expect(text).not.toContain(kind)
    }
  })
})

describe("COVERAGE_SKIP_ADVISORY_CATEGORIES", () => {
  it("contains exactly the seven Python categories", () => {
    expect([...COVERAGE_SKIP_ADVISORY_CATEGORIES].sort()).toEqual(
      [
        "auth_failed",
        "internal_target_refused",
        "missing_binary",
        "missing_credentials",
        "missing_extra",
        "targets_unreachable",
        "unexpected_response",
      ],
    )
  })
})
