interface ScoreGaugeProps {
  score: number          // 0..maxValue (default range: 0-100)
  label: string
  size?: number          // diameter in px; default 120 (sub-gauge), 160 (overall)
  strokeColor?: string   // CSS color string; defaults to score-based color
  isOverall?: boolean    // true = accent stroke, larger label
  maxValue?: number      // upper bound of the score range; default 100
}

function _gaugeColor(fraction: number): string {
  if (fraction >= 0.8) return "hsl(var(--quantum-safe))"       // Green 500 — quantum-safe
  if (fraction >= 0.5) return "hsl(var(--quantum-at-risk))"    // Amber 500 — at risk
  return "hsl(var(--quantum-vulnerable))"                       // Red 600 — vulnerable
}

export function ScoreGauge({ score, label, size = 120, strokeColor, isOverall = false, maxValue = 100 }: ScoreGaugeProps) {
  const cx = size / 2
  const cy = size / 2
  const radius = size / 2 - 12   // stroke-width padding
  const strokeWidth = isOverall ? 10 : 8

  // Normalized fraction (0.0-1.0) — drives arc fill and color
  const fraction = Math.max(0, Math.min(1, score / maxValue))

  // Arc: starts at bottom-left (-180deg), sweeps clockwise to bottom-right (0deg)
  // Using polar path: startAngle = 180deg, endAngle = 0deg (semicircle)
  const startX = cx - radius
  const startY = cy
  const endX = cx + radius
  const endY = cy
  // For colored fill arc
  const fillEndAngle = Math.PI - fraction * Math.PI  // from left to fill point
  const fillEndX = cx + radius * Math.cos(fillEndAngle) * -1
  const fillEndY = cy - radius * Math.sin(fillEndAngle)

  // Suppress unused variable warning
  void endX
  void endY

  const color = strokeColor ?? (isOverall ? "hsl(var(--accent))" : _gaugeColor(fraction))

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size / 2 + 20 }}>
        <svg width={size} height={size / 2 + strokeWidth} style={{ overflow: "visible" }}>
          {/* Background track */}
          <path
            d={`M ${startX} ${startY} A ${radius} ${radius} 0 0 1 ${endX} ${endY}`}
            fill="none"
            stroke="hsl(var(--border))"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          {/* Colored fill arc */}
          {score > 0 && (
            <path
              d={`M ${startX} ${startY} A ${radius} ${radius} 0 0 1 ${fillEndX} ${fillEndY}`}
              fill="none"
              stroke={color}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
            />
          )}
          {/* Score number — clamped to maxValue so arc and numeral agree */}
          <text
            x={cx}
            y={cy - 2}
            textAnchor="middle"
            dominantBaseline="middle"
            fill="currentColor"
            fontSize={isOverall ? 28 : 20}
            fontWeight={600}
            fontFamily="Inter, sans-serif"
          >
            {Math.min(score, maxValue)}
          </text>
        </svg>
      </div>
      <span
        className="text-muted-foreground"
        style={{ fontSize: 12, fontWeight: 600, textAlign: "center" }}
      >
        {label}
      </span>
    </div>
  )
}
