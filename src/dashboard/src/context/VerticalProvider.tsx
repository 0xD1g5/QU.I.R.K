/**
 * VerticalProvider — mirrors AuthProvider pattern.
 *
 * On mount, fetches GET /api/config (an unauth route) to determine the active vertical.
 * Exposes the resolved VerticalDescriptor via useVertical().
 *
 * Defaults to "general" while loading and on any fetch failure, so the dashboard
 * is always in a valid state and general installs see no healthcare UI.
 */
import { createContext, useContext, useEffect, useState } from "react"
import type { ReactNode } from "react"
import { getVertical } from "@/lib/verticals"
import type { VerticalDescriptor } from "@/lib/verticals"

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const VerticalContext = createContext<VerticalDescriptor>(getVertical("general"))

export function useVertical(): VerticalDescriptor {
  return useContext(VerticalContext)
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function VerticalProvider({ children }: { children: ReactNode }) {
  const [descriptor, setDescriptor] = useState<VerticalDescriptor>(
    getVertical("general"),
  )

  useEffect(() => {
    fetch("/api/config")
      .then((res) => res.json())
      .then((data: { vertical?: string }) => {
        setDescriptor(getVertical(data.vertical ?? "general"))
      })
      .catch(() => {
        // Network error or parse failure — stay on general
        setDescriptor(getVertical("general"))
      })
  }, [])

  return (
    <VerticalContext.Provider value={descriptor}>
      {children}
    </VerticalContext.Provider>
  )
}
