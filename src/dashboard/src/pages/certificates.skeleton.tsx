import { Skeleton } from "@/components/ui/skeleton"

export function CertificatesSkeleton() {
  return (
    <div role="status" aria-label="Loading certificates" className="space-y-6">
      <span className="sr-only">Loading...</span>
      <Skeleton className="h-7 w-40" />
      {Array.from({ length: 3 }).map((_, section) => (
        <div key={section} className="space-y-2">
          <Skeleton className="h-5 w-48" />
          {Array.from({ length: 4 }).map((_, row) => (
            <Skeleton key={row} className="h-10 w-full" />
          ))}
        </div>
      ))}
    </div>
  )
}
