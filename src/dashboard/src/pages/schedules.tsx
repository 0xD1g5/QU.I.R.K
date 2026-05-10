import { useState } from "react"
import { Trash2 } from "lucide-react"
import { useSchedules, type Schedule } from "@/hooks/useSchedules"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { EmptyStateCard } from "@/components/EmptyStateCard"

// ---------- Cron-to-human helper ----------

/**
 * Translate common 5-field cron expressions to human-readable text.
 * Handles daily, weekly, and hourly patterns; falls back to raw expr.
 * No third-party library — per UI-SPEC Copywriting section.
 */
function cronToHuman(expr: string): string {
  const parts = expr.trim().split(/\s+/)
  if (parts.length !== 5) return expr
  const [min, hour, dom, month, dow] = parts
  // Every N hours: "0 */N * * *"
  if (dom === "*" && month === "*" && dow === "*" && hour.startsWith("*/") && min === "0") {
    const n = hour.slice(2)
    return `Every ${n} hour${n === "1" ? "" : "s"}`
  }
  // Daily at hour: "M H * * *"
  if (dom === "*" && month === "*" && dow === "*" && /^\d+$/.test(hour) && /^\d+$/.test(min)) {
    return `Daily at ${hour.padStart(2, "0")}:${min.padStart(2, "0")} UTC`
  }
  // Weekly on specific day: "M H * * D" (D: 0=Sun, 1=Mon, ..., 6=Sat)
  const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
  if (dom === "*" && month === "*" && /^\d$/.test(dow) && /^\d+$/.test(hour) && /^\d+$/.test(min)) {
    const dayName = DAY_NAMES[parseInt(dow, 10)] ?? `day ${dow}`
    return `Every ${dayName} at ${hour.padStart(2, "0")}:${min.padStart(2, "0")} UTC`
  }
  return expr
}

// ---------- Status badge ----------

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-[var(--ds-text-faint)] text-white",
  running: "bg-[var(--ds-high)] text-white",
  completed: "bg-[var(--ds-ok)] text-white",
  failed: "bg-[var(--ds-critical)] text-white",
}

function StatusBadge({ status }: { status: Schedule["last_run_status"] }) {
  if (!status) {
    return (
      <Badge className="bg-[hsl(var(--muted))] text-muted-foreground text-xs">
        Never run
      </Badge>
    )
  }
  return (
    <Badge className={`${STATUS_STYLES[status] ?? ""} text-xs`}>
      {status}
    </Badge>
  )
}

// ---------- Loading skeleton ----------

function SchedulesSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex gap-4 py-3 border-b border-border items-center">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-24 font-mono" />
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-6 w-10" />
          <Skeleton className="h-8 w-8 rounded-md" />
        </div>
      ))}
    </div>
  )
}

// ---------- Page component ----------

export function SchedulesPage() {
  const { data, loading, error, patchEnabled, deleteSchedule } = useSchedules()
  const [addSheetOpen, setAddSheetOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<Schedule | null>(null)
  const [pendingPatch, setPendingPatch] = useState<Set<number>>(new Set())
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [deleteInFlight, setDeleteInFlight] = useState(false)

  async function handleToggle(id: number, enabled: boolean) {
    setPendingPatch((prev) => new Set(prev).add(id))
    try {
      await patchEnabled(id, enabled)
    } finally {
      setPendingPatch((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  async function handleDelete(schedule: Schedule) {
    setDeleteError(null)
    setDeleteInFlight(true)
    try {
      await deleteSchedule(schedule.id)
      setDeleteTarget(null)
    } catch {
      setDeleteError("Failed to delete schedule. Try again.")
    } finally {
      setDeleteInFlight(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Scheduled Scans</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Recurring scans managed by <code className="font-mono">quirk scheduler run</code>.
            Toggles take effect on the next scheduler loop (&le; 60 s).
          </p>
        </div>
        <Button variant="default" onClick={() => setAddSheetOpen(true)}>
          Add Schedule
        </Button>
      </div>

      {/* Content area */}
      {loading ? (
        <SchedulesSkeleton />
      ) : error ? (
        <EmptyStateCard message="Failed to load schedules. Check that the dashboard API is reachable." />
      ) : !data?.schedules?.length ? (
        <EmptyStateCard
          message={'No schedules yet. Register a schedule using the CLI: quirk schedule add --name <X> --cron <expr> --target <Y>'}
        />
      ) : (
        <div className="rounded-md border border-border">
          <Table>
            <caption className="sr-only">Scheduled scans</caption>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs font-semibold">Name</TableHead>
                <TableHead className="text-xs font-semibold">Target</TableHead>
                <TableHead className="text-xs font-semibold">Cron</TableHead>
                <TableHead className="text-xs font-semibold">Next Run</TableHead>
                <TableHead className="text-xs font-semibold">Last Run</TableHead>
                <TableHead className="text-xs font-semibold">Enabled</TableHead>
                <TableHead className="text-xs font-semibold sr-only">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.schedules.map((schedule) => (
                <TableRow key={schedule.id}>
                  <TableCell className="text-sm font-medium text-foreground py-3">
                    {schedule.name}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground py-3">
                    {schedule.target}
                  </TableCell>
                  <TableCell className="py-3">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="font-mono text-sm text-foreground cursor-default">
                          {schedule.cron_expr}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>
                        {cronToHuman(schedule.cron_expr)}
                      </TooltipContent>
                    </Tooltip>
                  </TableCell>
                  <TableCell className="py-3">
                    {schedule.next_run_at ? (
                      <span className="font-mono text-sm text-muted-foreground">
                        {new Date(schedule.next_run_at).toLocaleString()}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="py-3">
                    <div className="flex flex-col gap-1">
                      {schedule.last_run_at ? (
                        <span className="font-mono text-sm text-muted-foreground">
                          {new Date(schedule.last_run_at).toLocaleString()}
                        </span>
                      ) : (
                        <span className="text-muted-foreground text-sm">—</span>
                      )}
                      <StatusBadge status={schedule.last_run_status} />
                    </div>
                  </TableCell>
                  <TableCell className="py-3">
                    <div className="flex items-center min-h-[44px]">
                      <Switch
                        checked={schedule.enabled}
                        disabled={pendingPatch.has(schedule.id)}
                        onCheckedChange={(v) => handleToggle(schedule.id, v)}
                        aria-label={`${schedule.name} — ${schedule.enabled ? "enabled" : "disabled"}`}
                      />
                    </div>
                  </TableCell>
                  <TableCell className="py-3">
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Delete ${schedule.name}`}
                      onClick={() => {
                        setDeleteTarget(schedule)
                        setDeleteError(null)
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Add Schedule Sheet */}
      <Sheet open={addSheetOpen} onOpenChange={setAddSheetOpen}>
        <SheetContent>
          <SheetHeader>
            <SheetTitle>Add a Schedule</SheetTitle>
          </SheetHeader>
          <div className="mt-4 space-y-4 text-sm text-muted-foreground">
            <p>
              Schedules are managed via the CLI. Run the command below to create a new recurring scan:
            </p>
            <pre className="bg-muted rounded-md p-4 font-mono text-sm overflow-x-auto whitespace-pre-wrap">
              {`quirk schedule add --name "weekly-prod" --cron "0 2 * * 1" --target prod.example.com --profile balanced`}
            </pre>
          </div>
        </SheetContent>
      </Sheet>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete schedule?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            This will permanently remove &apos;{deleteTarget?.name}&apos;.
            Running or pending dispatches will not be interrupted.
          </p>
          {deleteError && (
            <p className="text-sm text-destructive">{deleteError}</p>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteTarget(null)}
              disabled={deleteInFlight}
            >
              Keep Schedule
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteTarget && handleDelete(deleteTarget)}
              disabled={deleteInFlight}
            >
              Delete Schedule
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
