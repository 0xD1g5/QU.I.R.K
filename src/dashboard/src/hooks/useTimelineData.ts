import { useState, useEffect } from "react"
import type { TrendTimeline } from "@/types/api"
import { fetchApi } from "@/lib/api"

interface UseTimelineDataResult {
  data: TrendTimeline | null
  loading: boolean
  error: string | null
}

export function useTimelineData(): UseTimelineDataResult {
  const [data, setData] = useState<TrendTimeline | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      try {
        setLoading(true)
        setError(null)
        const resp = await fetchApi("/api/trends/timeline?n=30")
        if (!resp.ok) {
          if (!cancelled) {
            if (resp.status === 401) {
              setError("Authentication required")
              return
            }
            if (resp.status === 403) {
              setError("Request blocked")
              return
            }
            if (resp.status === 429) {
              const retryAfter = resp.headers.get("Retry-After") ?? "60"
              setError(`Too many requests. Wait ${retryAfter} seconds and try again.`)
              return
            }
            setError(`API error: ${resp.status} ${resp.statusText}`)
          }
          return
        }
        const json: TrendTimeline = await resp.json()
        if (!cancelled) {
          setData(json)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load timeline")
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchData()
    return () => { cancelled = true }
  }, [])

  return { data, loading, error }
}
