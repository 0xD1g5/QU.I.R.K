import { Info } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { formatScoreNumber } from "@/lib/utils"
import type { FindingStoryline } from "@/types/api"

// Phase 202-04 / STORY-01, STORY-02 (D-01, D-07) — the drawer's narrative
// section and theme score-lift attribution block, plus their loading and
// error states. All eight 202-UI-SPEC.md State Matrix rows (S1-S6, S8; S7
// never mounts this component and is covered in 202-06 instead) are
// implemented here so 202-06 only has to mount <StorylineSections>.
//
// D-01's honest theme framing is enforced structurally, not by convention:
// `theme_score_lift` is NEVER divided by any count (Invariant 3), the `+N`
// glyph and its "when all N findings..." condition live in one <p> with no
// intervening block element (Invariant 1), and the mandatory disclaimer is
// co-present with every rendered lift number across all eight states
// (Invariant 2). See finding-storyline-sections.test.tsx for the mechanical
// enforcement of all three.

interface StorylineSectionsProps {
  data: FindingStoryline | null
  loading: boolean
  error: string | null
  onRetry: () => void
}

// Verbatim from findings.tsx:234 — match exactly, do not invent a heading
// treatment for these new sections.
const SECTION_LABEL_CLASS = "text-xs font-semibold text-muted-foreground uppercase mb-1"
const ATTRIBUTION_PANEL_CLASS = "rounded-lg border border-border bg-card p-4 space-y-2"

function PositionSentence({
  position,
  count,
}: {
  position: number | null
  count: number
}) {
  // A4: position is a locator, not a value — its absence is a silent
  // omission, never a replacement sentence.
  if (position == null) return null
  return (
    <p className="text-sm text-muted-foreground">
      This finding is {position} of {count} in the theme.
    </p>
  )
}

function ClosureSentence({
  closed,
  count,
}: {
  closed: number | null
  count: number
}) {
  // Independently suppressible from PositionSentence — item_progress()
  // returns closure counts unconditionally, with no notion of position.
  if (closed == null) return null
  return (
    <p className="text-sm text-muted-foreground">
      {closed} of {count} findings in this theme are verified closed.
    </p>
  )
}

function Disclaimer() {
  return (
    <div className="flex items-start gap-1">
      <Info className="h-3 w-3 text-muted-foreground" aria-hidden="true" />
      <p className="text-xs text-muted-foreground">
        This is the theme&apos;s total lift, not this finding&apos;s individual
        contribution. Resolving this finding alone does not yield the full
        amount.
      </p>
    </div>
  )
}

function NarrativeSection({ narrative }: { narrative: string | null }) {
  return (
    <div>
      <p className={SECTION_LABEL_CLASS}>Storyline</p>
      {narrative != null ? (
        <p className="text-sm text-foreground break-words">{narrative}</p>
      ) : (
        // A5 (D-07): the common path, not a fallback. Most findings carry no
        // algorithm keyword — this is real, first-class copy.
        <p className="text-sm text-muted-foreground break-words">
          No catalog narrative exists for this finding type yet — the
          Description and Remediation fields above are the available
          guidance.
        </p>
      )}
    </div>
  )
}

function AttributionPanel({ data }: { data: FindingStoryline | null }) {
  if (data == null) return null

  const {
    theme_slug,
    theme_title,
    theme_score_lift,
    theme_finding_count,
    theme_closed_count,
    finding_position,
  } = data

  return (
    <div className={ATTRIBUTION_PANEL_CLASS}>
      <p className={SECTION_LABEL_CLASS}>Score-lift attribution</p>
      {theme_slug == null ? (
        // A1: not mapped to any remediation theme. No theme line, no
        // number, no position, no closure, no disclaimer.
        <p className="text-sm text-muted-foreground">
          Not mapped to a remediation theme — no score-lift attribution
          exists for this finding.
        </p>
      ) : (
        <>
          <p className="text-sm break-words">
            <span className="text-muted-foreground">Remediation theme: </span>
            <span className="font-semibold">{theme_title}</span>
          </p>
          {theme_finding_count == null || theme_finding_count === 0 ? (
            // A3: constituent counts unavailable. The lift WAS modelled —
            // only the count is missing — so this is a distinct string from
            // A2, never a reuse of it. Never render "1 of 0"/"1 of null"/
            // "0 of 0": no position or closure sentence renders here.
            <p className="text-sm text-muted-foreground">
              The theme&apos;s constituent findings could not be counted in
              this scan, so the lift cannot be stated with its condition.
            </p>
          ) : theme_score_lift == null ? (
            // A2: theme known, lift unmodellable. Position/closure still
            // render if their own fields are available — the lift being
            // unmodellable says nothing about the constituent counts.
            <>
              <p className="text-sm text-muted-foreground">
                Score lift could not be modelled for this theme in this scan.
              </p>
              <PositionSentence
                position={finding_position}
                count={theme_finding_count}
              />
              <ClosureSentence
                closed={theme_closed_count}
                count={theme_finding_count}
              />
            </>
          ) : (
            // S1/S5: full lift sentence. Invariant 1 — the accented `+N`
            // span and its "pts when all N findings..." condition share one
            // <p> with no block-level element between them. theme_score_lift
            // is compared with `== null`, never truthiness, so a real 0
            // still renders "+0 pts ...".
            <>
              <p className="text-sm text-muted-foreground">
                <span
                  style={{ fontSize: 20, fontWeight: 600, color: "var(--ds-ok)" }}
                >
                  +{formatScoreNumber(theme_score_lift)}
                </span>{" "}
                pts when all {theme_finding_count} findings in this theme are
                resolved
              </p>
              <PositionSentence
                position={finding_position}
                count={theme_finding_count}
              />
              <ClosureSentence
                closed={theme_closed_count}
                count={theme_finding_count}
              />
              <Disclaimer />
            </>
          )}
        </>
      )}
    </div>
  )
}

export function StorylineSections({
  data,
  loading,
  error,
  onRetry,
}: StorylineSectionsProps) {
  // S8 wins over everything — a failed fetch and a genuine absence are
  // different facts and must read differently. No absence string ever
  // appears in this branch.
  if (error != null) {
    return (
      <div role="status" className="space-y-3">
        <div>
          <p className={SECTION_LABEL_CLASS}>Storyline</p>
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={onRetry}
            disabled={loading}
            aria-busy={loading}
          >
            Retry storyline
          </Button>
        </div>
      </div>
    )
  }

  if (loading && data == null) {
    return (
      <div role="status" className="space-y-4">
        <span className="sr-only">Loading storyline…</span>
        <div>
          <p className={SECTION_LABEL_CLASS}>Storyline</p>
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        </div>
        <div className={ATTRIBUTION_PANEL_CLASS}>
          <p className={SECTION_LABEL_CLASS}>Score-lift attribution</p>
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-full" />
        </div>
      </div>
    )
  }

  // The narrative section and the attribution panel are evaluated
  // INDEPENDENTLY — neither may short-circuit the other. That independence
  // is S6, and it is the whole reason the UI-SPEC calls S6 load-bearing.
  return (
    <div className="space-y-4">
      <NarrativeSection narrative={data?.narrative ?? null} />
      <AttributionPanel data={data} />
    </div>
  )
}
