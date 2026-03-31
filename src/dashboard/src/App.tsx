import { BrowserRouter, Routes, Route } from "react-router-dom"
import { ThemeProvider } from "@/components/theme-provider"
import { Sidebar } from "@/components/sidebar"
import { TooltipProvider } from "@/components/ui/tooltip"
import { PrintPage } from "@/pages/print"
import { ExecutivePage } from "@/pages/executive"
import { FindingsPage } from "@/pages/findings"
import { CertificatesPage } from "@/pages/certificates"
import { CbomPage } from "@/pages/cbom"
import { RoadmapPage } from "@/pages/roadmap"


export default function App() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="quirk-ui-theme">
      <TooltipProvider>
        <BrowserRouter>
          <div className="flex min-h-screen bg-background text-foreground">
            <Sidebar />
            {/* Main content offset by sidebar width */}
            <main className="flex-1 ml-12 lg:ml-60 min-h-screen overflow-auto">
              <div className="max-w-[1200px] mx-auto px-4 lg:px-8 py-6">
                <Routes>
                  <Route path="/" element={<ExecutivePage />} />
                  <Route path="/findings" element={<FindingsPage />} />
                  <Route path="/certificates" element={<CertificatesPage />} />
                  <Route path="/cbom" element={<CbomPage />} />
                  <Route path="/roadmap" element={<RoadmapPage />} />
                  <Route path="/print" element={<PrintPage />} />
                </Routes>
              </div>
            </main>
          </div>
        </BrowserRouter>
      </TooltipProvider>
    </ThemeProvider>
  )
}
