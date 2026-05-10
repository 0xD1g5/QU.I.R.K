import { useState, useEffect } from "react"
import type { ScanSession } from "@/types/api"
import { fetchApi } from "@/lib/api"

interface UseScanListResult {
  sessions: ScanSession[]
  loading: boolean
  error: string | null
}

export function useScanList(): UseScanListResult {
  const [sessions, setSessions] = useState<ScanSession[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function fetchSessions() {
      try {
        const resp = await fetchApi("/api/scans")
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
        const data: ScanSession[] = await resp.json()
        if (!cancelled) setSessions(data)
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load scan list")
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchSessions()
    return () => { cancelled = true }
  }, [])

  return { sessions, loading, error }
}
