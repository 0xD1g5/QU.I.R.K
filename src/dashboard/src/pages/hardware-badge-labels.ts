import type { HardwareFinding } from "@/types/api"

// Phase 216 HARNESS-02/D-08 — these five label functions were moved verbatim
// out of hardware.tsx into this pure module so
// tests/a11y/badge-variant-coverage.test.ts can import and call them
// directly, mechanically deriving the reachable keys of SNMP_STYLES,
// BRIDGE_STYLES, MODBUS_STYLES and BACNET_STYLES instead of the test having
// to declare that key set by hand (216-CONTEXT.md D-08, RESEARCH Open
// Question 1). They are not exported from hardware.tsx itself because
// eslint.config.js enables reactRefresh.configs.vite, whose
// only-export-components rule fires on any page file that exports a
// non-component alongside its component export — splitting this module out
// avoids that rule rather than fighting it.

// Maps a raw probe_state wire value to the verbatim UI-SPEC label. Returns
// "—" (never attempted) for null/undefined, mirroring snmpLabel's raw-fallback
// convention. identifiedLabel is column-specific ("Modbus" or "BACnet").
export function probeStateLabel(rawState: string | null | undefined, identifiedLabel: string): string {
  if (!rawState) return "—"
  switch (rawState) {
    case "identified":
      return identifiedLabel
    case "no_response":
      return "No response"
    case "no_match":
      return "No match"
    case "aborted_anomalous_response":
      return "Probe aborted"
    default:
      return rawState
  }
}

export function modbusLabel(f: HardwareFinding): string {
  return probeStateLabel(f.modbus_probe_state, "Modbus")
}

export function bacnetLabel(f: HardwareFinding): string {
  return probeStateLabel(f.bacnet_probe_state, "BACnet")
}

// Maps the raw wire bridge_status to the verbatim UI-SPEC label. Returns ""
// for null/absent (not a detected bridge pair) — the table cell renders a
// muted em-dash for that case, matching the existing SNMP-column convention.
export function bridgeLabel(f: HardwareFinding): string {
  switch (f.bridge_status) {
    case "upstream_mitigated":
      return "SNMP-confirmed"
    case "partial_only":
      return "Partial (assumed)"
    default:
      return ""
  }
}

// Maps the raw wire snmp_version to the verbatim UI-SPEC label. Returns "—"
// (never attempted) for null/undefined; mirrors quirk/reports/html_renderer.py
// and docx_renderer.py's `_snmp_badge_label` raw-fallback so an unmapped state
// (e.g. "v3-protocol-mismatch") renders its raw value rather than going blank.
export function snmpLabel(f: HardwareFinding): string {
  const raw = f.snmp_version
  if (!raw) return "—"
  switch (raw) {
    case "v3 auth+priv":
      return "v3 auth+priv"
    case "v3 noAuthNoPriv":
      return "v3 noAuthNoPriv"
    case "v2c":
      return "v2c"
    case "v3-failed-fell-back":
      return "v3 failed → v2c"
    case "none":
      return "No SNMP"
    default:
      return raw
  }
}
