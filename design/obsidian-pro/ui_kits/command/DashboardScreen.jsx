/* global React, Stat, Badge, Icon */

function DashboardScreen() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--ds-s6)" }}>
      <div>
        <p className="section-eyebrow">01 / OVERVIEW</p>
        <h1 style={{ fontSize: "var(--ds-fs-h1)", fontWeight: 700, marginTop: 4 }}>Security posture</h1>
        <p style={{ fontSize: "var(--ds-fs-body)", color: "var(--ds-text-muted)", marginTop: 4 }}>
          Last updated <span className="mono">2 min ago</span> · 843 assets monitored across 4 environments
        </p>
      </div>

      {/* Layer 1 — glanceable metrics */}
      <div className="ds-grid-4">
        <Stat label="Coverage"   value="98.2"  unit="%" delta="↑ 0.4%"   deltaTone="ok" />
        <Stat label="Detections" value="247"           delta="↓ 12%"    deltaTone="high" />
        <Stat label="MTTR"       value="4.2"  unit="h" delta="↓ 18min"  deltaTone="ok" />
        <Stat label="Critical"   value="3"            delta="needs action" critical />
      </div>

      {/* Hero KPI — Quantum Readiness */}
      <div className="ds-card" style={{ padding: "var(--ds-s5)" }}>
        <div style={{ display: "flex", alignItems: "flex-end", gap: "var(--ds-s5)" }}>
          <div style={{ flex: 1 }}>
            <p className="section-eyebrow">Hero metric</p>
            <p className="metric metric--lg metric--accent" style={{ marginTop: 4 }}>72</p>
            <p style={{ fontSize: 12, color: "var(--ds-ok)", marginTop: 4 }}>↑ 8 points from last assessment</p>
          </div>
          <div style={{ flex: 2, maxWidth: 320 }}>
            <p className="section-eyebrow" style={{ marginBottom: 6 }}>Target: 85 by Q4</p>
            <div style={{ height: 6, background: "var(--ds-bg-elevated)", borderRadius: 100, overflow: "hidden" }}>
              <div style={{ height: "100%", width: "72%", background: "var(--ds-accent)", borderRadius: 100 }} />
            </div>
          </div>
        </div>
      </div>

      {/* Layer 2 — recent activity */}
      <div className="ds-card" style={{ padding: 0 }}>
        <div style={{ padding: "var(--ds-s4)", borderBottom: "1px solid var(--ds-border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <p className="h3" style={{ fontSize: "var(--ds-fs-h3)", fontWeight: 600 }}>Recent detections</p>
          <button className="ds-btn ds-btn--ghost ds-btn--sm">View all <Icon name="arrow-right" size={12} /></button>
        </div>
        <table className="ds-table">
          <thead><tr><th>Detection</th><th>Severity</th><th>Asset</th><th>When</th></tr></thead>
          <tbody>
            <tr><td>Mimikatz on SRV-DC01</td><td><Badge tone="critical" dot>critical</Badge></td><td className="mono">SRV-DC01</td><td className="dim">3 min ago</td></tr>
            <tr><td>Lateral movement detected</td><td><Badge tone="high" dot>high</Badge></td><td className="mono">WKSTN-041</td><td className="dim">12 min ago</td></tr>
            <tr><td>Suspicious PowerShell exec</td><td><Badge tone="high" dot>high</Badge></td><td className="mono">LAPTOP-099</td><td className="dim">38 min ago</td></tr>
            <tr><td>Outbound to known C2</td><td><Badge tone="medium" dot>medium</Badge></td><td className="mono">SRV-WEB02</td><td className="dim">1h ago</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

window.DashboardScreen = DashboardScreen;
