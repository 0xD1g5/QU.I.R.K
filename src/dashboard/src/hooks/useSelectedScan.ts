import { useContext } from "react"
import { ScanContext } from "@/context/ScanContext"

export function useSelectedScan() {
  return useContext(ScanContext)
}
