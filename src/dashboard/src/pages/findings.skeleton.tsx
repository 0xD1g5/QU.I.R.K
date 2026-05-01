import { Skeleton } from "@/components/ui/skeleton"

export function FindingsSkeleton() {
  return (
    <div role="status" aria-label="Loading findings" className="space-y-6">
      <span className="sr-only">Loading...</span>
      <Skeleton className="h-7 w-32" />
      <div className="flex gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-9 w-32" />
        ))}
      </div>
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    </div>
  )
}
