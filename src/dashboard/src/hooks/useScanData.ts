import { useState, useEffect } from "react"
import type { ScanLatestResponse } from "@/types/api"

interface UseScanDataResult {
  data: ScanLatestResponse | null
  loading: boolean
  error: string | null
}

export function useScanData(): UseScanDataResult {
  const [data, setData] = useState<ScanLatestResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      try {
        setLoading(true)
        setError(null)
        const resp = await fetch("/api/scan/latest")
        if (!resp.ok) {
          if (resp.status === 404) {
            setError("No scan data available. Run a scan first: quirk scan <target>")
          } else {
            setError(`API error: ${resp.status} ${resp.statusText}`)
          }
          return
        }
        const json: ScanLatestResponse = await resp.json()
        if (!cancelled) {
          setData(json)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load scan data")
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
