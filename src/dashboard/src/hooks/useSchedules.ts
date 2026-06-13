import { useState, useEffect, useCallback } from "react"
import { fetchApi } from "@/lib/api"

export interface Schedule {
  id: number
  name: string
  cron_expr: string
  target: string
  profile: string | null
  enabled: boolean
  last_run_at: string | null
  next_run_at: string | null
  last_run_status: "pending" | "running" | "completed" | "failed" | null
  created_at: string
}

export interface ScheduleListResponse {
  schedules: Schedule[]
}

export interface UseSchedulesResult {
  data: ScheduleListResponse | null
  loading: boolean
  error: string | null
  patchEnabled: (id: number, enabled: boolean) => Promise<void>
  deleteSchedule: (id: number) => Promise<void>
  refetch: () => void
}

export function useSchedules(): UseSchedulesResult {
  const [data, setData] = useState<ScheduleListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [fetchCount, setFetchCount] = useState(0)

  useEffect(() => {
    let cancelled = false

    // Clear stale data synchronously before initiating new fetch (HOOK-01 pattern)
    setData(null)
    setLoading(true)
    setError(null)

    async function fetchData() {
      try {
        const resp = await fetchApi("/api/schedules")
        if (!resp.ok) {
          if (!cancelled) {
            if (resp.status === 401) {
              setError("Authentication required")
            } else if (resp.status === 403) {
              setError("Request blocked")
            } else {
              setError(`API error: ${resp.status} ${resp.statusText}`)
            }
          }
          return
        }
        const json: ScheduleListResponse = await resp.json()
        if (!cancelled) {
          setData(json)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load schedules")
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchData()
    return () => {
      cancelled = true
    }
  }, [fetchCount])

  const refetch = useCallback(() => {
    setFetchCount((c) => c + 1)
  }, [])

  /**
   * Toggle the enabled state for a schedule.
   * Optimistic update: flip local state before PATCH returns; revert on failure.
   * Phase 62 Pitfall 6 pattern.
   */
  const patchEnabled = useCallback(async (id: number, enabled: boolean) => {
    // Optimistic flip
    setData((prev) => {
      if (!prev) return prev
      return {
        schedules: prev.schedules.map((s) =>
          s.id === id ? { ...s, enabled } : s
        ),
      }
    })

    try {
      const resp = await fetchApi(`/api/schedules/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      })
      if (!resp.ok) {
        // Revert optimistic update on failure
        setData((prev) => {
          if (!prev) return prev
          return {
            schedules: prev.schedules.map((s) =>
              s.id === id ? { ...s, enabled: !enabled } : s
            ),
          }
        })
      }
    } catch {
      // Revert optimistic update on network error
      setData((prev) => {
        if (!prev) return prev
        return {
          schedules: prev.schedules.map((s) =>
            s.id === id ? { ...s, enabled: !enabled } : s
          ),
        }
      })
    }
  }, [])

  /**
   * Delete a schedule by id.
   * Removes from local data on success; leaves row on failure.
   */
  const deleteSchedule = useCallback(async (id: number) => {
    const resp = await fetchApi(`/api/schedules/${id}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    })
    if (!resp.ok) {
      throw new Error(`Delete failed: ${resp.status} ${resp.statusText}`)
    }
    setData((prev) => {
      if (!prev) return prev
      return {
        schedules: prev.schedules.filter((s) => s.id !== id),
      }
    })
  }, [])

  return { data, loading, error, patchEnabled, deleteSchedule, refetch }
}
