import { createContext, useContext, useState } from "react"
import type { ReactNode } from "react"

interface ScanContextValue {
  selectedScanId: string | null  // null = always load latest
  setSelectedScanId: (id: string | null) => void
}

const ScanContext = createContext<ScanContextValue>({
  selectedScanId: null,
  setSelectedScanId: () => {},
})

export function ScanProvider({ children }: { children: ReactNode }) {
  const [selectedScanId, setSelectedScanId] = useState<string | null>(null)
  return (
    <ScanContext.Provider value={{ selectedScanId, setSelectedScanId }}>
      {children}
    </ScanContext.Provider>
  )
}

export function useSelectedScan() {
  return useContext(ScanContext)
}
