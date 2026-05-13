import { useParams, useNavigate, Link } from "react-router-dom"
import { CheckCircle2 } from "lucide-react"
import { useJobStatus } from "@/hooks/useJobStatus"
import { fetchApi } from "@/lib/api"
import { PageSpinner } from "@/components/PageSpinner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"

const STAGE_DISPLAY_NAMES: Record<string, string> = {
  discovery: "Discovery",
  tls: "TLS",
  ssh: "SSH",
  api: "API",
  identity: "Identity",
  data_at_rest: "Data at Rest",
  reports: "Reports",
}

const STAGE_ORDER = ["discovery", "tls", "ssh", "api", "identity", "data_at_rest", "reports"]

const STATUS_BADGE_CLASS: Record<string, string> = {
  queued: "bg-[var(--ds-text-faint)] text-white border-transparent",
  running: "bg-[var(--ds-high)] text-white border-transparent",
  completed: "bg-[var(--ds-ok)] text-white border-transparent",
  failed: "bg-[var(--ds-critical)] text-white border-transparent",
  cancelled: "bg-[var(--ds-text-faint)] text-white border-transparent",
}

const STATUS_LABEL: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
}

export function ScanJobPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const result = useJobStatus(jobId ?? "")

  const handleCancel = async () => {
    if (!jobId) return
    try {
      const resp = await fetchApi(`/api/jobs/${jobId}`, { method: "DELETE" })
      if (resp.status === 204 || resp.ok) {
        navigate("/scan/new", { state: { cancelled: true } })
      }
    } catch {
      // surface error inline; do not block UI
    }
  }

  if (result.kind === "loading") {
    return <PageSpinner ariaLabel="Loading scan status" />
  }

  if (result.kind === "not_found") {
    return (
      <Card className="max-w-[640px] mx-auto mt-16 px-6 py-6">
        <h1 className="text-xl font-semibold">Scan not found</h1>
        <p className="text-sm text-muted-foreground mt-2">
          This scan job does not exist or has expired.{" "}
          <Link to="/scan/new" className="text-primary underline underline-offset-4">
            Return to New Scan
          </Link>
          .
        </p>
      </Card>
    )
  }

  if (result.kind === "error") {
    return (
      <Card className="max-w-[640px] mx-auto mt-16 px-6 py-6">
        <p className="text-sm text-destructive">{result.message}</p>
      </Card>
    )
  }

  const { data } = result

  return (
    <Card className="max-w-[640px] mx-auto mt-16 px-6 py-6">
      {/* Header row */}
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-xl font-semibold">Scan Progress</h1>
        <Badge className={STATUS_BADGE_CLASS[data.status] ?? ""}>
          {STATUS_LABEL[data.status] ?? data.status}
        </Badge>
      </div>

      <p className="font-mono text-sm text-muted-foreground mt-1">Job ID: {data.job_id}</p>

      <Separator className="my-4" />

      {/* Stage indicator */}
      <div role="list" className="flex items-end justify-between gap-1 mb-4">
        {STAGE_ORDER.map((stage, index) => {
          const stageNum = index + 1
          const isCompleted = data.stage_index > stageNum
          const isCurrent = data.stage_index === stageNum
          const stageLabel = STAGE_DISPLAY_NAMES[stage] ?? stage
          const stageState = isCompleted ? "completed" : isCurrent ? "current" : "upcoming"

          return (
            <div
              key={stage}
              role="listitem"
              aria-label={`Stage ${stageNum}: ${stageLabel}, ${stageState}`}
              className="flex flex-col items-center gap-1 flex-1 min-w-0"
            >
              {/* Dot */}
              <div
                className={[
                  "w-5 h-5 rounded-full flex items-center justify-center",
                  isCompleted
                    ? "bg-[var(--ds-ok)]"
                    : isCurrent
                    ? "bg-primary animate-pulse"
                    : "bg-[var(--ds-border)]",
                ].join(" ")}
              >
                {isCompleted && (
                  <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                )}
              </div>
              {/* Label */}
              <span
                className={[
                  "text-[10px] text-center leading-tight truncate w-full text-center",
                  isCompleted || isCurrent
                    ? "text-foreground font-medium"
                    : "text-muted-foreground",
                ].join(" ")}
              >
                {stageLabel}
              </span>
            </div>
          )
        })}
      </div>

      {/* Progress bar */}
      <Progress
        value={(data.stage_index / data.stage_total) * 100}
        className="w-full mt-4"
        aria-label="Scan progress"
        aria-valuenow={data.stage_index}
        aria-valuemax={data.stage_total}
      />

      <p className="text-sm font-medium mt-2">
        Stage {data.stage_index} of 7 — {STAGE_DISPLAY_NAMES[data.current_stage ?? ""] ?? "—"}
      </p>

      <Separator className="my-4" />

      {/* Metadata row */}
      <div className="flex flex-col gap-1 text-sm text-muted-foreground">
        {data.started_at && (
          <span>Started: {data.started_at}</span>
        )}
        <span>
          Job ID: <span className="font-mono">{data.job_id.slice(0, 8)}…</span>
        </span>
      </div>

      {/* Conditional action blocks */}
      {data.status === "running" && (
        <div className="mt-4">
          <Button
            variant="destructive"
            className="w-full"
            aria-label={`Cancel scan job ${data.job_id}`}
            onClick={handleCancel}
          >
            Cancel scan
          </Button>
        </div>
      )}

      {data.status === "failed" && (
        <div className="mt-4 space-y-3">
          <h2 className="text-base font-semibold text-destructive">Scan failed</h2>
          <pre className="whitespace-pre-wrap text-sm text-muted-foreground bg-muted rounded-md p-3">
            {data.error_message}
          </pre>
          <Link to="/scan/new" className="text-sm text-primary underline underline-offset-4">
            Return to New Scan
          </Link>
        </div>
      )}

      {data.status === "cancelled" && (
        <div className="mt-4">
          <p className="text-sm text-muted-foreground">
            Scan cancelled.{" "}
            <Link to="/scan/new" className="text-primary underline underline-offset-4">
              Start a new scan
            </Link>
            .
          </p>
        </div>
      )}
    </Card>
  )
}
