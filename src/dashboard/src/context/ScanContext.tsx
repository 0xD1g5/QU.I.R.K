import { createContext } from "react"

interface ScanContextValue {
  selectedScanId: string | null  // null = always load latest
  setSelectedScanId: (id: string | null) => void
}

export const ScanContext = createContext<ScanContextValue>({
  selectedScanId: null,
  setSelectedScanId: () => {},
})
