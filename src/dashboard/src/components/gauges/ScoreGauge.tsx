interface ScoreGaugeProps {
  score: number          // 0-100
  label: string
  size?: number          // diameter in px; default 120 (sub-gauge), 160 (overall)
  strokeColor?: string   // CSS color string; defaults to score-based color
  isOverall?: boolean    // true = accent stroke, larger label
}

function _gaugeColor(score: number): string {
  if (score >= 80) return "hsl(142 71% 45%)"   // Green 500 — quantum-safe
  if (score >= 50) return "hsl(38 92% 50%)"    // Amber 500 — at risk
  return "hsl(0 72% 51%)"                       // Red 600 — vulnerable
}

export function ScoreGauge({ score, label, size = 120, strokeColor, isOverall = false }: ScoreGaugeProps) {
  const cx = size / 2
  const cy = size / 2
  const radius = size / 2 - 12   // stroke-width padding
  const strokeWidth = isOverall ? 10 : 8
  const circumference = Math.PI * radius  // half circle arc
  const fillLength = (score / 100) * circumference

  // Arc: starts at bottom-left (-180deg), sweeps clockwise to bottom-right (0deg)
  // Using polar path: startAngle = 180deg, endAngle = 0deg (semicircle)
  const startX = cx - radius
  const startY = cy
  const endX = cx + radius
  const endY = cy
  // For colored fill arc
  const fillEndAngle = Math.PI - (score / 100) * Math.PI  // from left to fill point
  const fillEndX = cx + radius * Math.cos(fillEndAngle) * -1
  const fillEndY = cy - radius * Math.sin(fillEndAngle)

  // Suppress unused variable warning
  void circumference
  void fillLength
  void endX
  void endY

  const color = strokeColor ?? (isOverall ? "hsl(210 100% 56%)" : _gaugeColor(score))

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size / 2 + 20 }}>
        <svg width={size} height={size / 2 + strokeWidth} style={{ overflow: "visible" }}>
          {/* Background track */}
          <path
            d={`M ${startX} ${startY} A ${radius} ${radius} 0 0 1 ${endX} ${endY}`}
            fill="none"
            stroke="hsl(240 6% 17%)"
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
          {/* Score number */}
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
            {score}
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
