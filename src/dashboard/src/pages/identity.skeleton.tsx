import { Skeleton } from "@/components/ui/skeleton"

export function IdentitySkeleton() {
  return (
    <div role="status" aria-label="Loading identity" className="space-y-6">
      <span className="sr-only">Loading...</span>
      <Skeleton className="h-7 w-32" />
      <div className="grid gap-4 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full" />
        ))}
      </div>
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    </div>
  )
}
