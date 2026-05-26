import { useState, useEffect } from "react"
import type { MergeLatestData } from "@/types/api"
import { fetchApi } from "@/lib/api"

interface UseMergeLatestResult {
  merge: MergeLatestData | null
  loading: boolean
  error: string | null
}

export function useMergeLatest(): UseMergeLatestResult {
  const [merge, setMerge] = useState<MergeLatestData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    // Clear stale data synchronously before initiating new fetch.
    setMerge(null)
    setLoading(true)
    setError(null)

    const url = "/api/merge/latest"

    async function fetchData() {
      try {
        const resp = await fetchApi(url)
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
            setError(`Failed to fetch ${url}: ${resp.status} ${resp.statusText}`)
          }
          return
        }
        const json = await resp.json()
        if (!cancelled) {
          setMerge(json.merge ?? null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            `Failed to fetch ${url}: ${err instanceof Error ? err.message : String(err)}`,
          )
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
  }, [])

  return { merge, loading, error }
}
