/**
 * Phase 65 UI-SCAN-02: polling hook for /api/jobs/{job_id}.
 *
 * Polls every 3000ms (CONTEXT.md D-07). Stops on terminal status
 * (completed | failed | cancelled). On completed with scan_run_id,
 * calls setSelectedScanId + navigate("/").
 *
 * Cancellation-safe per Phase 62 HOOK-01 pattern: let cancelled = false +
 * return () => { cancelled = true } in useEffect cleanup.
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
  | { kind: "ok"; data: JobStatus }

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
        setResult({ kind: "ok", data })

        if (data.status === "completed" && data.scan_run_id) {
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
