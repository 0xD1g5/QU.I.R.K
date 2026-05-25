import { BrowserRouter, Routes, Route } from "react-router-dom"
import { ThemeProvider } from "@/components/theme-provider"
import { AuthProvider, useAuth } from "@/context/AuthProvider"
import { ScanProvider } from "@/context/ScanProvider"
import { QRAMMProvider } from "@/context/QRAMMProvider"
import { Sidebar } from "@/components/sidebar"
import { TooltipProvider } from "@/components/ui/tooltip"
import { LoginPage } from "@/pages/login"
import { PrintPage } from "@/pages/print"
import { ExecutivePage } from "@/pages/executive"
import { FindingsPage } from "@/pages/findings"
import { IdentityPage } from "@/pages/identity"
import { MotionPage } from "@/pages/motion"
import { DataAtRestPage } from "@/pages/data-at-rest"
import { CertificatesPage } from "@/pages/certificates"
import { CbomPage } from "@/pages/cbom"
import { RoadmapPage } from "@/pages/roadmap"
import { TrendsPage } from "@/pages/trends"
import { OrgProfilePage } from "@/pages/qramm-profile"
import { AssessmentPage } from "@/pages/qramm-assessment"
import { SchedulesPage } from "@/pages/schedules"
import { ScanNewPage } from "@/pages/scan-new"
import { ScanJobPage } from "@/pages/scan-job"
import { ScanHistoryPage } from "@/pages/scan-history"
import { ComparePage } from "@/pages/compare"

/**
 * AppShell — AUTH-03 mount guard.
 *
 * Switches on AuthContext status:
 *   loading        → blank dark screen (no flash, no sidebar)
 *   unauthenticated → LoginPage (no sidebar, no routes)
 *   authenticated   → existing Sidebar + main routes tree (unchanged)
 *
 * Must be rendered inside AuthProvider (uses useAuth hook).
 * ScanProvider + QRAMMProvider are inside AuthProvider so their API calls
 * are already guarded by the auth gate.
 */
function AppShell() {
  const { status } = useAuth()

  if (status === "loading") {
    return <div className="min-h-screen bg-background" />
  }

  if (status === "unauthenticated") {
    return <LoginPage />
  }

  // status === "authenticated" — render full dashboard
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <Sidebar />
      {/* Main content offset by sidebar width */}
      <main className="flex-1 ml-12 lg:ml-60 min-h-screen overflow-auto">
        <div className="max-w-[1200px] mx-auto px-4 lg:px-8 py-6">
          <Routes>
            <Route path="/" element={<ExecutivePage />} />
            <Route path="/findings" element={<FindingsPage />} />
            <Route path="/identity" element={<IdentityPage />} />
            <Route path="/motion" element={<MotionPage />} />
            <Route path="/data-at-rest" element={<DataAtRestPage />} />
            <Route path="/certificates" element={<CertificatesPage />} />
            <Route path="/cbom" element={<CbomPage />} />
            <Route path="/roadmap" element={<RoadmapPage />} />
            <Route path="/trends" element={<TrendsPage />} />
            <Route path="/print" element={<PrintPage />} />
            <Route path="/qramm" element={<OrgProfilePage />} />
            <Route path="/qramm/assessment" element={<AssessmentPage />} />
            <Route path="/schedules" element={<SchedulesPage />} />
            <Route path="/scan/new" element={<ScanNewPage />} />
            <Route path="/scan/job/:jobId" element={<ScanJobPage />} />
            <Route path="/scans" element={<ScanHistoryPage />} />
            <Route path="/compare" element={<ComparePage />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="quirk-ui-theme">
      <AuthProvider>
        <ScanProvider>
          <QRAMMProvider>
            <TooltipProvider>
              <BrowserRouter>
                <AppShell />
              </BrowserRouter>
            </TooltipProvider>
          </QRAMMProvider>
        </ScanProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}
