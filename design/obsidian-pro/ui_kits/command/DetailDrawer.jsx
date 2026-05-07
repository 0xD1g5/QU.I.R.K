/* global React, Badge, Button, Icon */

function DetailDrawer({ row, onClose }) {
  if (!row) return null;
  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 200, animation: "fadeIn .18s ease" }} />
      <aside style={{
        position: "fixed", top: 0, right: 0, width: 460, maxWidth: "100vw", height: "100vh",
        background: "var(--ds-bg-base)", borderLeft: "1px solid var(--ds-border)",
        boxShadow: "0 8px 32px rgba(0,0,0,.4)", zIndex: 201,
        display: "flex", flexDirection: "column",
        animation: "slideIn .25s ease",
      }}>
        <div style={{ padding: "var(--ds-s4)", borderBottom: "1px solid var(--ds-border)", display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
          <div>
            <p className="section-eyebrow">03 / DETAIL</p>
            <p className="mono" style={{ fontSize: 12, color: "var(--ds-text-muted)", marginTop: 2 }}>{row.cve}</p>
            <p style={{ fontSize: "var(--ds-fs-h2)", fontWeight: 600, marginTop: 4 }}>{row.title}</p>
          </div>
          <button onClick={onClose} className="ds-btn ds-btn--ghost ds-btn--sm" aria-label="Close"><Icon name="x" size={14} /></button>
        </div>

        <div style={{ padding: "var(--ds-s4)", display: "flex", flexDirection: "column", gap: "var(--ds-s4)", flex: 1, overflowY: "auto" }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Badge tone={row.sev} dot>{row.sev}</Badge>
            <Badge tone={row.status === "patched" ? "ok" : row.status === "in review" ? "info" : "medium"}>{row.status}</Badge>
            <Badge tone="accent">● live</Badge>
          </div>

          <div className="ds-grid-2">
            <div>
              <p className="ds-label">CVSS</p>
              <p className="metric metric--sm" style={{ color: row.sev === "critical" ? "var(--ds-critical)" : row.sev === "high" ? "var(--ds-high)" : "var(--ds-text)", marginTop: 4 }}>{row.cvss.toFixed(1)}</p>
            </div>
            <div>
              <p className="ds-label">Affected hosts</p>
              <p className="metric metric--sm" style={{ marginTop: 4 }}>{row.hosts}</p>
            </div>
          </div>

          <div>
            <p className="ds-label" style={{ marginBottom: 8 }}>Description</p>
            <p style={{ fontSize: "var(--ds-fs-body)", color: "var(--ds-text)", lineHeight: 1.55 }}>
              An out-of-bounds write vulnerability in the GlobalProtect feature of PAN-OS allows an unauthenticated attacker to execute arbitrary code with root privileges on the firewall.
            </p>
          </div>

          <div>
            <p className="ds-label" style={{ marginBottom: 8 }}>Affected hosts</p>
            <div style={{ background: "var(--ds-bg-surface)", border: "1px solid var(--ds-border)", borderRadius: "var(--ds-r-md)", overflow: "hidden" }}>
              {["SRV-DC01.corp.local", "SRV-DC02.corp.local", "FW-EDGE-01"].map((h) => (
                <div key={h} style={{ padding: "8px 12px", borderBottom: "1px solid var(--ds-border-subtle)", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12 }}>
                  <span className="mono">{h}</span>
                  <Badge tone="medium">unpatched</Badge>
                </div>
              ))}
            </div>
          </div>

          <div>
            <p className="ds-label" style={{ marginBottom: 8 }}>Timeline</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                { t: "09:42:18Z", ev: "Initial detection on SRV-DC01" },
                { t: "09:43:02Z", ev: "Lateral movement to SRV-DC02" },
                { t: "09:44:51Z", ev: "EDR isolated affected hosts" },
              ].map((e) => (
                <div key={e.t} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                  <span className="mono" style={{ fontSize: 11, color: "var(--ds-text-faint)", minWidth: 80 }}>{e.t}</span>
                  <span style={{ fontSize: 12 }}>{e.ev}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div style={{ padding: "var(--ds-s4)", borderTop: "1px solid var(--ds-border)", display: "flex", gap: 8 }}>
          <Button variant="primary" icon="search-check" onClick={onClose}>Investigate</Button>
          <Button variant="secondary" icon="user-plus" onClick={onClose}>Assign</Button>
          <Button variant="ghost" onClick={onClose}>Dismiss</Button>
        </div>
      </aside>
    </>
  );
}

window.DetailDrawer = DetailDrawer;
