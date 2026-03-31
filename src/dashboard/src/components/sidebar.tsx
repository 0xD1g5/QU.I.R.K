import { Link, useLocation } from "react-router-dom"
import {
  LayoutDashboard,
  AlertTriangle,
  Shield,
  Database,
  GitBranch,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { ModeToggle } from "@/components/mode-toggle"

const NAV_ITEMS = [
  { path: "/", label: "Executive Summary", Icon: LayoutDashboard },
  { path: "/findings", label: "Findings", Icon: AlertTriangle },
  { path: "/certificates", label: "Certificates", Icon: Shield },
  { path: "/cbom", label: "CBOM Viewer", Icon: Database },
  { path: "/roadmap", label: "Migration Roadmap", Icon: GitBranch },
]

export function Sidebar() {
  const location = useLocation()

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
      <div className="flex items-center gap-3 px-3 lg:px-5 py-5 border-b border-border">
        <span className="text-accent font-semibold text-sm hidden lg:block tracking-wide">
          QU.I.R.K.
        </span>
        <span className="text-accent font-semibold text-sm lg:hidden">Q</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col gap-1 py-4 px-2" aria-label="Dashboard navigation">
        {NAV_ITEMS.map(({ path, label, Icon }) => {
          const isActive = location.pathname === path
          return (
            <Tooltip key={path}>
              <TooltipTrigger asChild>
                <Link
                  to={path}
                  aria-label={label}
                  className={cn(
                    "flex items-center gap-3 px-2 py-2 rounded-md text-sm transition-colors",
                    "min-h-[44px]", // accessibility touch target
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

      {/* Theme toggle at bottom */}
      <div className="px-2 py-4 border-t border-border">
        <ModeToggle />
      </div>
    </aside>
  )
}
