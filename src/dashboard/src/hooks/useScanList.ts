import { useState, useEffect } from "react"
import type { ScanSession } from "@/types/api"

interface UseScanListResult {
  sessions: ScanSession[]
  loading: boolean
}

export function useScanList(): UseScanListResult {
  const [sessions, setSessions] = useState<ScanSession[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function fetchSessions() {
      try {
        const resp = await fetch("/api/scans")
        if (resp.ok) {
          const data: ScanSession[] = await resp.json()
          if (!cancelled) setSessions(data)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchSessions()
    return () => { cancelled = true }
  }, [])

  return { sessions, loading }
}
