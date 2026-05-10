import { useState } from "react"
import { AlertTriangle } from "lucide-react"
import { Link } from "react-router-dom"
import { useTrendsData } from "@/hooks/useTrendsData"

/**
 * Phase 64 TREND-02: Regression alert chip.
 *
 * Renders on the dashboard home (ExecutivePage) above the score gauge
 * when the latest scan regressed (score drop >= 5 pts OR new HIGH/CRITICAL
 * findings). Reads the existing /api/trends response — no new API call.
 *
 * Dismissal is per-session and stored in localStorage under
 * `quirk.dismissed_regression.<session_ts>`. A new scan with a different
 * session_ts produces a fresh chip even after a prior dismissal.
 *
 * IMPORTANT: dismissal state is computed at render time from `data`
 * (not from useState initial value) to avoid stale-on-mount pitfall —
 * useState initial runs once at mount when data is still null, so
 * `localStorage.getItem(`quirk.dismissed_regression.${null}`)` would
 * always be null and the chip would never recognise prior dismissal.
 */
export function RegressionAlertChip() {
  const { data, loading } = useTrendsData()
  const [manuallyDismissed, setManuallyDismissed] = useState(false)

  if (loading || !data || manuallyDismissed) return null

  const sessionTs = data.current_session_ts ?? null

  // Render-time localStorage check (NOT useState initial — Pitfall 4)
  const isDismissed = sessionTs
    ? !!localStorage.getItem(`quirk.dismissed_regression.${sessionTs}`)
    : false
  if (isDismissed) return null

  const isRegression =
    (data.score_delta !== null && data.score_delta <= -5) ||
    data.new_high > 0
  if (!isRegression) return null

  function handleDismiss() {
    if (sessionTs) {
      localStorage.setItem(`quirk.dismissed_regression.${sessionTs}`, "1")
    }
    setManuallyDismissed(true)
  }

  const message =
    data.score_delta !== null && data.score_delta <= -5
      ? `Score dropped ${Math.abs(data.score_delta)} pts.`
      : `${data.new_high} new HIGH/CRITICAL finding(s) detected.`

  return (
    <div
      className="flex items-center gap-2 rounded-md border border-destructive bg-destructive/10 px-4 py-2 mb-8"
      role="alert"
    >
      <AlertTriangle className="h-4 w-4 text-destructive shrink-0" aria-hidden="true" />
      <span className="text-sm flex-1">
        {message}{" "}
        <Link to="/trends" className="text-primary underline">
          View trends →
        </Link>
      </span>
      <button
        type="button"
        onClick={handleDismiss}
        aria-label="Dismiss regression alert"
        className="text-muted-foreground hover:text-foreground ml-2"
      >
        ×
      </button>
    </div>
  )
}
