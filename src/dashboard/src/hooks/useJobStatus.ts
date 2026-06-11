/**
 * Phase 65 UI-SCAN-02: polling hook for /api/jobs/{job_id}.
 *
 * Polls every 3000ms (CONTEXT.md D-07). Stops on terminal status
 * (completed | failed | cancelled). On completed with scan_run_id,
 * fetches result-summary to check endpoint_count before navigating.
 * If endpoint_count === 0, stays on scan-job with zeroResult=true.
 * If endpoint_count > 0 (or summary fetch fails), navigates to dashboard.
 *
 * Cancellation-safe per Phase 62 HOOK-01 pattern: let cancelled = false +
 * return () => { cancelled = true } in useEffect cleanup.
 *
 * Phase 121 PORT-09/10: zero-result detection via GET /api/jobs/{id}/result-summary.
 */
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { fetchApi } from "@/lib/api"
import { useSelectedScan } from "@/hooks/useSelectedScan"
import type { JobStatus } from "@/types/api"

export type JobStatusResult =
  | { kind: "loading" }
  | { kind: "not_found" }
  | { kind: "error"; message: string }
  | { kind: "ok"; data: JobStatus; zeroResult: boolean }

const TERMINAL = new Set(["completed", "failed", "cancelled"])
const POLL_INTERVAL_MS = 3000

export function useJobStatus(jobId: string): JobStatusResult {
  const [result, setResult] = useState<JobStatusResult>({ kind: "loading" })
  const [trackedJobId, setTrackedJobId] = useState(jobId)
  const navigate = useNavigate()
  const { setSelectedScanId } = useSelectedScan()

  // Reset to loading when the polled job changes. React-endorsed "adjust state
  // when a prop changes" render-phase pattern (https://react.dev/learn/you-might-not-need-an-effect)
  // — avoids calling setState inside the effect (react-hooks/set-state-in-effect)
  // while still preventing a flash of the previous job's status before the new poll resolves.
  if (jobId !== trackedJobId) {
    setTrackedJobId(jobId)
    setResult({ kind: "loading" })
  }

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | null = null

    async function poll() {
      if (cancelled) return
      try {
        const resp = await fetchApi(`/api/jobs/${jobId}`)
        if (cancelled) return
        if (resp.status === 404) {
          setResult({ kind: "not_found" })
          return
        }
        if (!resp.ok) {
          setResult({ kind: "error", message: `API error: ${resp.status} ${resp.statusText}` })
          if (!cancelled) timer = setTimeout(poll, POLL_INTERVAL_MS)
          return
        }
        const data: JobStatus = await resp.json()
        if (cancelled) return
        // Set initial ok state (zeroResult=false until summary check below)
        setResult({ kind: "ok", data, zeroResult: false })

        if (data.status === "completed" && data.scan_run_id) {
          // Phase 121: fetch result-summary before navigating to detect zero-endpoint scans
          let endpointCount = 1 // fail-safe: assume non-zero if fetch fails
          try {
            const summaryResp = await fetchApi(`/api/jobs/${jobId}/result-summary`)
            if (cancelled) return
            if (summaryResp.ok) {
              const summary: { endpoint_count: number } = await summaryResp.json()
              if (cancelled) return
              endpointCount = summary.endpoint_count
            }
          } catch {
            // fail-safe: treat fetch error as non-zero (navigate to dashboard)
          }
          if (cancelled) return
          if (endpointCount === 0) {
            // Zero endpoints: stay on scan-job with zero-result message
            setResult({ kind: "ok", data, zeroResult: true })
            return
          }
          // Non-zero: navigate to dashboard as normal
          setSelectedScanId(data.scan_run_id)
          navigate("/")
          return
        }
        if (!TERMINAL.has(data.status)) {
          timer = setTimeout(poll, POLL_INTERVAL_MS)
        }
      } catch (err) {
        if (cancelled) return
        setResult({ kind: "error", message: err instanceof Error ? err.message : "Network error" })
        if (!cancelled) timer = setTimeout(poll, POLL_INTERVAL_MS)
      }
    }

    poll()

    return () => {
      cancelled = true
      if (timer !== null) {
        clearTimeout(timer)
      }
    }
  }, [jobId, navigate, setSelectedScanId])

  return result
}
