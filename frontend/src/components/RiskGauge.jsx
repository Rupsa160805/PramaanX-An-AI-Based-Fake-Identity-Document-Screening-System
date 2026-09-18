// [FRONTEND-SAFE] Animated risk gauge — SVG arc, animates from 0 to actual score
// ONLY displays score/level from actual backend response. No fabrication.
import { useEffect, useRef, useState } from 'react'

const LEVEL_COLORS = {
  low: { arc: '#16865A', bg: '#E8F7F0', text: '#0E5C3A', label: 'LOW RISK' },
  medium: { arc: '#C98512', bg: '#FFF8EC', text: '#7A5010', label: 'MEDIUM RISK' },
  high: { arc: '#C83B3B', bg: '#FEF2F2', text: '#8B1A1A', label: 'HIGH RISK' },
  unknown: { arc: '#64748B', bg: '#F1F5F9', text: '#334155', label: 'UNKNOWN' },
}

export default function RiskGauge({ score, level }) {
  const [displayed, setDisplayed] = useState(0)
  const rafRef = useRef(null)
  const startTimeRef = useRef(null)
  const duration = 1200 // ms

  const safeLevel = LEVEL_COLORS[level] ? level : 'unknown'
  const colors = LEVEL_COLORS[safeLevel]
  const safeScore = typeof score === 'number' ? Math.max(0, Math.min(100, score)) : null

  useEffect(() => {
    if (safeScore === null) return
    // Cancel any ongoing animation
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    startTimeRef.current = null

    const animate = (timestamp) => {
      if (!startTimeRef.current) startTimeRef.current = timestamp
      const elapsed = timestamp - startTimeRef.current
      const progress = Math.min(elapsed / duration, 1)
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplayed(Math.round(eased * safeScore))
      if (progress < 1) rafRef.current = requestAnimationFrame(animate)
    }
    rafRef.current = requestAnimationFrame(animate)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [safeScore])

  // SVG arc geometry
  const cx = 100
  const cy = 100
  const r = 72
  const startAngle = -210 // degrees — 240° arc
  const totalArc = 240
  const pct = safeScore === null ? 0 : displayed / 100
  const arcAngle = pct * totalArc

  const toRad = (deg) => (deg * Math.PI) / 180
  const arcPath = (start, sweep) => {
    const startRad = toRad(start)
    const endRad = toRad(start + sweep)
    const x1 = cx + r * Math.cos(startRad)
    const y1 = cy + r * Math.sin(startRad)
    const x2 = cx + r * Math.cos(endRad)
    const y2 = cy + r * Math.sin(endRad)
    const largeArc = sweep > 180 ? 1 : 0
    return `M ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2}`
  }

  return (
    <div className={`risk-gauge risk-gauge--${safeLevel}`} role="img" aria-label={`Risk score ${safeScore ?? 'unavailable'}, level ${safeLevel}`}>
      <svg className="risk-gauge__svg" viewBox="0 0 200 175" xmlns="http://www.w3.org/2000/svg">
        {/* Background track */}
        <path
          d={arcPath(startAngle, totalArc)}
          fill="none"
          stroke={colors.bg}
          strokeWidth="14"
          strokeLinecap="round"
        />
        {/* Active arc */}
        {safeScore !== null && (
          <path
            d={arcPath(startAngle, arcAngle)}
            fill="none"
            stroke={colors.arc}
            strokeWidth="14"
            strokeLinecap="round"
          />
        )}
        {/* Score text */}
        <text x="100" y="105" textAnchor="middle" className="risk-gauge__score" fill={colors.text}>
          {safeScore === null ? '—' : displayed}
        </text>
        <text x="100" y="125" textAnchor="middle" className="risk-gauge__out-of" fill={colors.text}>
          {safeScore !== null ? '/ 100' : ''}
        </text>
      </svg>
      <div className={`risk-gauge__level risk-gauge__level--${safeLevel}`}>
        {colors.label}
      </div>
      <p className="risk-gauge__caption">Risk Assessment Score</p>
    </div>
  )
}
