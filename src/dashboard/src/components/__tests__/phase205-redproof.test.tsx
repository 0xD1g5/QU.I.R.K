/**
 * TEMPORARY — Phase 205 plan 205-04 red-proof (GUARD-02, ROADMAP criterion 4).
 *
 * This file exists to prove that the vitest substitute-execution leg in
 * tests/test_uat_disposition_integrity.py actually EXECUTES cited vitest tests
 * in CI, rather than merely checking that the file and title exist.
 *
 * The distinction matters: the always-on existence leg
 * (find_unresolvable_vitest_refs) already rejects a missing file or a missing
 * title by pure source-text inspection. So breaking a FILENAME would turn CI
 * red for the old reason and prove nothing new. This test therefore exists,
 * carries a title that is cited verbatim in docs/UAT-SERIES.md, and FAILS —
 * which only an executing leg can detect.
 *
 * IT IS REVERTED IMMEDIATELY AFTER THE CI RUN IS CAPTURED. If you are reading
 * this on a branch that is not mid-red-proof, it should not be here: delete it
 * and remove the citation from docs/UAT-SERIES.md.
 *
 * Evidence recorded in .planning/phases/205-guard-integrity/205-RED-PROOF.md
 */
import { describe, it, expect } from "vitest";

describe("phase205 red proof", () => {
  it("deliberately fails to prove the vitest execution leg runs in CI", () => {
    // An existing file with a matching title that nonetheless fails.
    // Only execution catches this; existence-checking cannot.
    expect(1).toBe(2);
  });
});
