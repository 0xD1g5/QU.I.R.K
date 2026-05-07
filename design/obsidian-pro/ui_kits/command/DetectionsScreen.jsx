/* global React, Badge, Search, Select, Field, Button, Icon */
const { useState } = React;

const ROWS = [
  { cve: "CVE-2024-3400",  sev: "critical", hosts: 12, cvss: 10.0, status: "open",      title: "Mimikatz on SRV-DC01" },
  { cve: "CVE-2024-1086",  sev: "high",     hosts: 6,  cvss: 8.7,  status: "in review", title: "Lateral movement WKSTN-041" },
  { cve: "CVE-2024-21413", sev: "high",     hosts: 4,  cvss: 8.1,  status: "open",      title: "Suspicious PowerShell exec" },
  { cve: "CVE-2023-44487", sev: "medium",   hosts: 31, cvss: 5.4,  status: "patched",   title: "HTTP/2 rapid reset" },
  { cve: "CVE-2023-22515", sev: "critical", hosts: 2,  cvss: 9.8,  status: "open",      title: "Confluence privilege escalation" },
  { cve: "CVE-2024-23222", sev: "medium",   hosts: 8,  cvss: 6.3,  status: "in review", title: "WebKit type confusion" },
];

function DetectionsScreen({ onSelect }) {
  const [filter, setFilter] = useState("all");
  const [query,  setQuery]  = useState("");

  const visible = ROWS.filter(r =>
    (filter === "all" || r.sev === filter) &&
    (!query || r.cve.toLowerCase().includes(query.toLowerCase()) || r.title.toLowerCase().includes(query.toLowerCase()))
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--ds-s5)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 16, flexWrap: "wrap" }}>
        <div>
          <p className="section-eyebrow">02 / TRIAGE</p>
          <h1 style={{ fontSize: "var(--ds-fs-h1)", fontWeight: 700, marginTop: 4 }}>Detections</h1>
          <p style={{ fontSize: "var(--ds-fs-body)", color: "var(--ds-text-muted)", marginTop: 4 }}>
            {visible.length} of {ROWS.length} findings
          </p>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
          <div style={{ width: 220 }}>
            <Search value={query} onChange={setQuery} placeholder="CVE, host, asset…" />
          </div>
          <Field label="Severity">
            <Select value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="all">All severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
            </Select>
          </Field>
          <Button variant="primary" icon="download">Export</Button>
        </div>
      </div>

      <div className="ds-card" style={{ padding: 0, overflow: "hidden" }}>
        <table className="ds-table">
          <thead>
            <tr>
              <th className="sort">CVE <Icon name="chevrons-up-down" size={10} style={{ opacity: 0.4 }} /></th>
              <th>Title</th>
              <th className="sort">Severity</th>
              <th>Hosts</th>
              <th className="sort" style={{ textAlign: "right" }}>CVSS <Icon name="chevrons-up-down" size={10} style={{ opacity: 0.4 }} /></th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={r.cve} style={{ cursor: "pointer" }} onClick={() => onSelect(r)}>
                <td className="mono">{r.cve}</td>
                <td>{r.title}</td>
                <td><Badge tone={r.sev} dot>{r.sev}</Badge></td>
                <td>{r.hosts}</td>
                <td
                  className="num"
                  style={{
                    color: r.sev === "critical" ? "var(--ds-critical)"
                         : r.sev === "high"     ? "var(--ds-high)"
                         : "var(--ds-text)",
                    fontWeight: r.sev === "critical" || r.sev === "high" ? 700 : 400,
                  }}
                >{r.cvss.toFixed(1)}</td>
                <td>
                  <Badge tone={r.status === "patched" ? "ok" : r.status === "in review" ? "info" : "medium"}>
                    {r.status}
                  </Badge>
                </td>
                <td style={{ textAlign: "right" }}>
                  <Icon name="chevron-right" size={14} style={{ color: "var(--ds-text-faint)" }} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

window.DetectionsScreen = DetectionsScreen;
window.DETECTION_ROWS = ROWS;
