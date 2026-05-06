import { useMemo } from "react"
import { useScanData } from "@/hooks/useScanData"
import type { MotionFinding } from "@/types/api"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { EmptyStateCard } from "@/components/EmptyStateCard"

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-[hsl(0_72%_51%)] text-white",
  HIGH:     "bg-[hsl(24_95%_53%)] text-white",
  MEDIUM:   "bg-[hsl(38_92%_50%)] text-black",
  LOW:      "bg-[hsl(213_94%_68%)] text-black",
  INFO:     "bg-[hsl(240_5%_46%)] text-white",
}

const EMAIL_PROTOS = new Set([
  "SMTP-STARTTLS", "SMTPS", "IMAP-STARTTLS", "IMAPS", "POP3-STARTTLS", "POP3S",
])

function isEmailProtocol(protocol?: string): boolean {
  return EMAIL_PROTOS.has(protocol ?? "")
}

function getBrokerFamily(protocol: string): "Kafka" | "AMQP" | "Redis" | "Cloud" | null {
  if (protocol.startsWith("KAFKA-")) return "Kafka"
  if (protocol.startsWith("AMQP-") || protocol.startsWith("AMQPS")) return "AMQP"
  if (protocol.startsWith("REDIS-")) return "Redis"
  if (protocol.startsWith("HTTPS/")) return "Cloud"
  return null
}

const SEV_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4 } as const

function EmailTable({ findings }: { findings: MotionFinding[] }) {
  const rows = [...findings].sort(
    (a, b) =>
      (SEV_ORDER[a.severity as keyof typeof SEV_ORDER] ?? 99) -
      (SEV_ORDER[b.severity as keyof typeof SEV_ORDER] ?? 99) ||
      (a.port ?? 0) - (b.port ?? 0),
  )

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead scope="col" className="text-xs font-semibold">Port</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Protocol</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">TLS Version</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Cipher Suite</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Cert Expiry</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Quantum Risk</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Warning</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((f, i) => (
              <TableRow key={`${f.host}-${f.port}-${i}`} className="hover:bg-accent/5">
                <TableCell className="text-sm">{f.port}</TableCell>
                <TableCell className="text-sm">
                  <div className="flex items-center gap-2">
                    {f.severity && (
                      <Badge className={`${SEVERITY_STYLES[f.severity] ?? ""} font-semibold text-xs`}>
                        {f.severity}
                      </Badge>
                    )}
                    <span>{f.protocol}</span>
                  </div>
                </TableCell>
                <TableCell className="text-sm font-mono">
                  {f.plaintext_exposed ? "" : (f.tls_version ?? "")}
                </TableCell>
                <TableCell className="text-sm font-mono">
                  {f.plaintext_exposed ? "" : (f.cipher_suite ?? "")}
                </TableCell>
                <TableCell className="text-sm">
                  {f.cert_not_after
                    ? new Date(f.cert_not_after).toLocaleDateString("en-US", { dateStyle: "medium" })
                    : ""}
                </TableCell>
                <TableCell className="text-sm">{f.quantum_risk ?? ""}</TableCell>
                <TableCell className="text-sm">
                  {f.starttls_warning && (
                    <Badge className="bg-[hsl(38_92%_50%)] text-black text-xs">⚠ STARTTLS</Badge>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

function BrokerGroupedSections({ findings }: { findings: MotionFinding[] }) {
  const FAMILIES: Array<"Kafka" | "AMQP" | "Redis" | "Cloud"> = ["Kafka", "AMQP", "Redis", "Cloud"]
  const grouped = useMemo(() => {
    const m: Record<string, MotionFinding[]> = { Kafka: [], AMQP: [], Redis: [], Cloud: [] }
    for (const f of findings) {
      const fam = getBrokerFamily(f.protocol ?? "")
      if (fam) m[fam].push(f)
    }
    return m
  }, [findings])

  return (
    <div className="space-y-4">
      {FAMILIES.filter(fam => grouped[fam].length > 0).map(fam => {
        const rows = grouped[fam]
        const plaintextCount = rows.filter(r => r.plaintext_exposed).length
        const pillClass = plaintextCount > 0
          ? "bg-[hsl(24_95%_53%)] text-white"
          : "bg-[hsl(213_94%_68%)] text-black"
        return (
          <Card key={fam}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                {fam} · {rows.length} endpoint(s) · {plaintextCount} plaintext
                <Badge className={`${pillClass} text-xs`}>
                  {plaintextCount > 0 ? "AT RISK" : "OK"}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col" className="text-xs font-semibold">Host</TableHead>
                    <TableHead scope="col" className="text-xs font-semibold">Port</TableHead>
                    <TableHead scope="col" className="text-xs font-semibold">Protocol</TableHead>
                    <TableHead scope="col" className="text-xs font-semibold">TLS Version</TableHead>
                    <TableHead scope="col" className="text-xs font-semibold">Cipher Suite</TableHead>
                    <TableHead scope="col" className="text-xs font-semibold">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((r, i) => {
                    const proto = r.protocol ?? ""
                    const cloudSuffix = proto.includes("/") ? proto.split("/")[1] : null
                    return (
                      <TableRow key={`${r.host}-${r.port}-${i}`} className="hover:bg-accent/5">
                        <TableCell className="text-sm">{r.host}</TableCell>
                        <TableCell className="text-sm">{r.port}</TableCell>
                        <TableCell className="text-sm">{proto}</TableCell>
                        <TableCell className="text-sm font-mono">
                          {r.plaintext_exposed ? "" : (r.tls_version ?? "")}
                        </TableCell>
                        <TableCell className="text-sm font-mono">
                          {r.plaintext_exposed ? "" : (r.cipher_suite ?? "")}
                        </TableCell>
                        <TableCell className="text-sm">
                          <div className="flex items-center gap-2">
                            {r.plaintext_exposed && (
                              <Badge className="bg-[hsl(24_95%_53%)] text-white text-xs">
                                ☠ PLAINTEXT
                              </Badge>
                            )}
                            {cloudSuffix && (
                              <Badge className="bg-[hsl(213_94%_68%)] text-black text-xs">
                                ☁ {cloudSuffix}
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}

export function MotionPage() {
  const { data, loading, error } = useScanData()

  const motionFindings: MotionFinding[] = useMemo(
    () => data?.motion_findings ?? [],
    [data],
  )
  const emailFindings = useMemo(
    () => motionFindings.filter(f => isEmailProtocol(f.protocol)),
    [motionFindings],
  )
  const brokerFindings = useMemo(
    () => motionFindings.filter(f => getBrokerFamily(f.protocol ?? "") !== null),
    [motionFindings],
  )

  if (loading) {
    return (
      <div role="status" aria-label="Loading motion" className="space-y-6">
        <span className="sr-only">Loading...</span>
        {Array.from({ length: 3 }).map((_, s) => (
          <div key={s} className="space-y-2">
            <Skeleton className="h-5 w-48" />
            {Array.from({ length: 4 }).map((_, r) => (
              <Skeleton key={r} className="h-10 w-full" />
            ))}
          </div>
        ))}
      </div>
    )
  }
  if (error) return <p className="text-muted-foreground text-sm">{error}</p>

  return (
    <div className="space-y-6">
      <h1 style={{ fontSize: 20, fontWeight: 600 }}>Data in Motion</h1>

      <section aria-labelledby="email-section-heading">
        <h2
          id="email-section-heading"
          style={{ fontSize: 16, fontWeight: 600 }}
          className="mb-3"
        >
          Email Protocols
        </h2>
        {emailFindings.length === 0 ? (
          <EmptyStateCard message="No email endpoints scanned in this session — enable the email scanner in your config or scan a mail server." />
        ) : (
          <EmailTable findings={emailFindings} />
        )}
      </section>

      <section aria-labelledby="broker-section-heading">
        <h2
          id="broker-section-heading"
          style={{ fontSize: 16, fontWeight: 600 }}
          className="mb-3"
        >
          Message Brokers
        </h2>
        {brokerFindings.length === 0 ? (
          <EmptyStateCard message="No broker endpoints scanned in this session — enable the broker scanner in your config or scan a message broker host." />
        ) : (
          <BrokerGroupedSections findings={brokerFindings} />
        )}
      </section>
    </div>
  )
}
