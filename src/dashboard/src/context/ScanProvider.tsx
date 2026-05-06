import { useState } from "react"
import type { ReactNode } from "react"
import { ScanContext } from "./ScanContext"

export function ScanProvider({ children }: { children: ReactNode }) {
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null)
  return (
    <ScanContext.Provider value={{ selectedScanId, setSelectedScanId }}>
      {children}
    </ScanContext.Provider>
  )
}
