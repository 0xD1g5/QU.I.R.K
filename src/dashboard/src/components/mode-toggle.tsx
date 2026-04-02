import { Moon, Sun, Monitor } from "lucide-react"
import { useTheme } from "@/components/use-theme"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

export function ModeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <div className="flex gap-1" role="group" aria-label="Color theme">
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={theme === "light" ? "secondary" : "ghost"}
            size="icon"
            onClick={() => setTheme("light")}
            aria-label="Light mode"
            className="h-8 w-8"
          >
            <Sun className="h-4 w-4" />
          </Button>
        </TooltipTrigger>
        <TooltipContent>Light</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={theme === "dark" ? "secondary" : "ghost"}
            size="icon"
            onClick={() => setTheme("dark")}
            aria-label="Dark mode"
            className="h-8 w-8"
          >
            <Moon className="h-4 w-4" />
          </Button>
        </TooltipTrigger>
        <TooltipContent>Dark</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={theme === "system" ? "secondary" : "ghost"}
            size="icon"
            onClick={() => setTheme("system")}
            aria-label="System theme"
            className="h-8 w-8"
          >
            <Monitor className="h-4 w-4" />
          </Button>
        </TooltipTrigger>
        <TooltipContent>System</TooltipContent>
      </Tooltip>
    </div>
  )
}
