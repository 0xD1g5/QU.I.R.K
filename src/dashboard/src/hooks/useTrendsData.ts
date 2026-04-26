import { useState, useEffect } from "react"
import type { TrendReport } from "@/types/api"

interface UseTrendsDataResult {
  data: TrendReport | null
  loading: boolean
  error: string | null
}

export function useTrendsData(): UseTrendsDataResult {
  const [data, setData] = useState<TrendReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      try {
        setLoading(true)
        setError(null)
        const resp = await fetch("/api/trends")
        if (!resp.ok) {
          if (!cancelled) {
            setError(`API error: ${resp.status} ${resp.statusText}`)
          }
          return
        }
        const json: TrendReport = await resp.json()
        if (!cancelled) {
          setData(json)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load trend data")
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

  return { data, loading, error }
}
