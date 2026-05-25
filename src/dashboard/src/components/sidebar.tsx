// D-13 color audit (Phase 7): all component color tokens verified to use CSS variables.
// Hardcoded values found and resolved: ScoreGauge.tsx hsl() literals -> hsl(var(--token)) CSS variable refs;
// chart.tsx #ccc/#fff are CSS attribute selectors targeting Recharts internals (intentional one-off).
import { Link, useLocation, useNavigate } from "react-router-dom"
import {
  LayoutDashboard,
  AlertTriangle,
  Shield,
  Database,
  GitBranch,
  Fingerprint,
  TrendingUp,
  Activity,
  HardDrive,
  ClipboardList,
  Calendar,
  Scan,
  History,
  LogOut,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { ModeToggle } from "@/components/mode-toggle"
import { ScanSelector } from "@/components/ScanSelector"
import { useAuth } from "@/context/AuthProvider"

const NAV_ITEMS = [
  { path: "/", label: "Executive Summary", Icon: LayoutDashboard },
  { path: "/findings", label: "Findings", Icon: AlertTriangle },
  { path: "/identity", label: "Identity", Icon: Fingerprint },
  { path: "/motion", label: "Motion", Icon: Activity },
  { path: "/data-at-rest", label: "Data at Rest", Icon: HardDrive },
  { path: "/certificates", label: "Certificates", Icon: Shield },
  { path: "/cbom", label: "CBOM Viewer", Icon: Database },
  { path: "/roadmap", label: "Migration Roadmap", Icon: GitBranch },
  { path: "/trends", label: "Trends", Icon: TrendingUp },
  { path: "/scans", label: "Scan History", Icon: History },
  { path: "/schedules", label: "Schedules", Icon: Calendar },
  { path: "/qramm", label: "QRAMM Assessment", Icon: ClipboardList },
]

export function Sidebar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { logout } = useAuth()

  return (
    <aside
      className={cn(
        // 240px wide on desktop; 48px (icon-only) below 1024px
        "fixed left-0 top-0 h-full z-10",
        "w-12 lg:w-60",
        "flex flex-col",
        "bg-card border-r border-border",
      )}
    >
      {/* Logo / title */}
      <div className="flex items-center gap-2 px-3 lg:px-5 py-4 border-b border-border">
        {/* Full wordmark on wide sidebar */}
        <span className="text-accent font-black text-base hidden lg:block tracking-widest font-mono leading-none">
          QU.I.R.K.
        </span>
        {/* Monogram on narrow sidebar */}
        <span className="text-accent font-black text-lg lg:hidden font-mono leading-none">Q</span>
      </div>

      {/* New Scan CTA — above all nav items, below wordmark */}
      <div className="px-2 py-3 border-b border-border">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="default"
              className="w-full justify-start gap-3 min-h-[44px]"
              onClick={() => navigate("/scan/new")}
              aria-label="New Scan"
            >
              <Scan className="h-5 w-5 flex-shrink-0" />
              <span className="hidden lg:inline">New Scan</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right" className="lg:hidden">New Scan</TooltipContent>
        </Tooltip>
      </div>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col gap-1 py-4 px-2" aria-label="Dashboard navigation">
        {NAV_ITEMS.map(({ path, label, Icon }) => {
          const isActive = path === "/qramm"
            ? location.pathname.startsWith("/qramm")
            : location.pathname === path
          return (
            <Tooltip key={path}>
              <TooltipTrigger asChild>
                <Link
                  to={path}
                  aria-label={label}
                  className={cn(
                    "flex items-center gap-3 px-2 py-2 rounded-md text-sm transition-colors",
                    "min-h-[44px]", // accessibility touch target
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                    isActive
                      ? "text-foreground border-b-2 lg:border-b-0 lg:border-l-2 border-accent bg-accent/10"
                      : "text-muted-foreground hover:text-foreground hover:bg-accent/5",
                  )}
                >
                  <Icon className="h-5 w-5 flex-shrink-0" />
                  <span className="hidden lg:block">{label}</span>
                </Link>
              </TooltipTrigger>
              {/* Tooltip only visible in collapsed (icon-only) state */}
              <TooltipContent side="right" className="lg:hidden">
                {label}
              </TooltipContent>
            </Tooltip>
          )
        })}
      </nav>

      {/* Scan history selector — only shown when >1 scan exists */}
      <ScanSelector />

      {/* Theme toggle at bottom */}
      <div className="px-2 py-4 border-t border-border">
        <ModeToggle />
      </div>

      {/* Sign out control — below ModeToggle, pushed to bottom */}
      <Separator />
      <div className="px-2 py-2">
        {/* Collapsed (icon-only) state: icon Button with tooltip */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={logout}
              aria-label="Sign out"
              className="w-full lg:hidden"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right" className="lg:hidden">Sign out</TooltipContent>
        </Tooltip>
        {/* Expanded state: full-width ghost button with icon + label */}
        <Button
          variant="ghost"
          onClick={logout}
          className="w-full justify-start gap-2 hidden lg:flex"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </Button>
      </div>
    </aside>
  )
}
