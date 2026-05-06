import { Skeleton } from "@/components/ui/skeleton"

export function CbomSkeleton() {
  return (
    <div role="status" aria-label="Loading CBOM" className="space-y-6">
      <span className="sr-only">Loading...</span>
      <Skeleton className="h-7 w-32" />
      <div className="flex gap-2">
        <Skeleton className="h-9 w-24" />
        <Skeleton className="h-9 w-24" />
      </div>
      <Skeleton className="h-9 w-full max-w-md" />
      <Skeleton className="h-[60vh] w-full" />
    </div>
  )
}
