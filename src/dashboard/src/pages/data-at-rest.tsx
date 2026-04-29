import { useMemo } from "react"
import { useScanData } from "@/hooks/useScanData"
import type { DarFinding } from "@/types/api"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { ScoreGauge } from "@/components/gauges/ScoreGauge"

function EmptyStateCard({ message }: { message: string }) {
  return (
    <Card>
      <CardContent className="py-8">
        <p className="text-muted-foreground text-sm">{message}</p>
      </CardContent>
    </Card>
  )
}

export function DataAtRestPage() {
  const { data, loading, error } = useScanData()

  const darFindings: DarFinding[] = useMemo(
    () => data?.dar_findings ?? [],
    [data],
  )
  const dbFindings = useMemo(
    () => darFindings.filter((f) => f.category === "database"),
    [darFindings],
  )
  const objFindings = useMemo(
    () => darFindings.filter((f) => f.category === "object_storage"),
    [darFindings],
  )
  const k8sFindings = useMemo(
    () => darFindings.filter((f) => f.category === "kubernetes"),
    [darFindings],
  )
  const vaultFindings = useMemo(
    () => darFindings.filter((f) => f.category === "vault"),
    [darFindings],
  )

  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    )
  }
  if (error) return <p className="text-muted-foreground text-sm">{error}</p>

  const darScore = data?.score.subscores.data_at_rest ?? 0

  return (
    <div className="space-y-6">
      <h1 style={{ fontSize: 20, fontWeight: 600 }}>Data at Rest</h1>

      <div>
        <ScoreGauge score={darScore} label="Data at Rest" size={120} />
      </div>

      <section aria-labelledby="dar-db-heading">
        <h2 id="dar-db-heading" style={{ fontSize: 16, fontWeight: 600 }} className="mb-3">
          Database Encryption
        </h2>
        {dbFindings.length === 0 ? (
          <EmptyStateCard message="No database endpoints scanned in this session — enable the DB scanner in your config or scan a database host." />
        ) : (
          <EmptyStateCard message={`Pending table render — ${dbFindings.length} finding(s)`} />
        )}
      </section>

      <section aria-labelledby="dar-obj-heading">
        <h2 id="dar-obj-heading" style={{ fontSize: 16, fontWeight: 600 }} className="mb-3">
          Object Storage
        </h2>
        {objFindings.length === 0 ? (
          <EmptyStateCard message="No object storage buckets scanned in this session — enable the object storage scanner or configure cloud credentials." />
        ) : (
          <EmptyStateCard message={`Pending table render — ${objFindings.length} finding(s)`} />
        )}
      </section>

      <section aria-labelledby="dar-k8s-heading">
        <h2 id="dar-k8s-heading" style={{ fontSize: 16, fontWeight: 600 }} className="mb-3">
          Kubernetes Secrets
        </h2>
        {k8sFindings.length === 0 ? (
          <EmptyStateCard message="No Kubernetes secrets scanned in this session — enable the Kubernetes scanner or configure cluster access." />
        ) : (
          <EmptyStateCard message={`Pending table render — ${k8sFindings.length} finding(s)`} />
        )}
      </section>

      <section aria-labelledby="dar-vault-heading">
        <h2 id="dar-vault-heading" style={{ fontSize: 16, fontWeight: 600 }} className="mb-3">
          Vault
        </h2>
        {vaultFindings.length === 0 ? (
          <EmptyStateCard message="No Vault mounts scanned in this session — enable the Vault connector or configure a Vault address." />
        ) : (
          <EmptyStateCard message={`Pending table render — ${vaultFindings.length} finding(s)`} />
        )}
      </section>
    </div>
  )
}
