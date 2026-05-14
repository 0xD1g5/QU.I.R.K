import { useState, useEffect } from "react"
import type { CompareResponse } from "@/types/api"
import { fetchApi } from "@/lib/api"

interface UseCompareDataResult {
  data: CompareResponse | null
  loading: boolean
  error: string | null
}

export function useCompareData(
  scanA: string | null,
  scanB: string | null,
): UseCompareDataResult {
  const [data, setData] = useState<CompareResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!scanA || !scanB) return
    let cancelled = false
    setData(null)
    setLoading(true)
    setError(null)

    async function fetchCompare() {
      try {
        const resp = await fetchApi(
          `/api/compare?a=${encodeURIComponent(scanA!)}&b=${encodeURIComponent(scanB!)}`,
        )
        if (!resp.ok) {
          if (!cancelled) {
            if (resp.status === 401) { if (!cancelled) setError("Authentication required"); return }
            if (resp.status === 403) { if (!cancelled) setError("Request blocked"); return }
            if (resp.status === 429) {
              const retryAfter = resp.headers.get("Retry-After") ?? "60"
              if (!cancelled) setError(`Too many requests. Wait ${retryAfter} seconds and try again.`)
              return
            }
            if (resp.status === 400) {
              const body = await resp.json().catch(() => ({}))
              if (!cancelled) setError((body as { detail?: string })?.detail ?? "Bad request")
              return
            }
            if (!cancelled) setError(`API error: ${resp.status} ${resp.statusText}`)
          }
          return
        }
        const result: CompareResponse = await resp.json()
        if (!cancelled) setData(result)
      } catch (err) {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load comparison")
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchCompare()
    return () => { cancelled = true }
  }, [scanA, scanB])

  return { data, loading, error }
}
