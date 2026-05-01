import { Skeleton } from "@/components/ui/skeleton"

export function PageSpinner({ ariaLabel = "Loading dashboard" }: { ariaLabel?: string }) {
  return (
    <div role="status" aria-label={ariaLabel} className="space-y-6">
      <span className="sr-only">Loading...</span>
      <div className="flex flex-wrap gap-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-32 w-32 rounded-full" />
        ))}
      </div>
      <Skeleton className="h-48 w-full" />
    </div>
  )
}
