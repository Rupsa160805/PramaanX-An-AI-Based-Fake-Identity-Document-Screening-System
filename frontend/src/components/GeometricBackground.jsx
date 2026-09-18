// [FRONTEND-SAFE] Indian geometric background — purely decorative, aria-hidden
// Inspired by jaali/mandala geometry. Extremely subtle, slow animation.
// Respects prefers-reduced-motion.

export default function GeometricBackground({ variant = 'default' }) {
  return (
    <div className={`geo-bg geo-bg--${variant}`} aria-hidden="true">
      <svg
        className="geo-bg__svg"
        viewBox="0 0 800 800"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMidYMid slice"
      >
        {/* Outer concentric ring */}
        <circle cx="400" cy="400" r="380" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.4" />
        <circle cx="400" cy="400" r="320" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.35" />
        <circle cx="400" cy="400" r="260" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.3" />
        <circle cx="400" cy="400" r="200" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.25" />
        <circle cx="400" cy="400" r="140" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.2" />
        <circle cx="400" cy="400" r="80" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.15" />

        {/* 24-spoke radial lines — Ashoka Chakra geometry inspiration */}
        {Array.from({ length: 24 }, (_, i) => {
          const angle = (i * 15 * Math.PI) / 180
          const x1 = 400 + 90 * Math.cos(angle)
          const y1 = 400 + 90 * Math.sin(angle)
          const x2 = 400 + 370 * Math.cos(angle)
          const y2 = 400 + 370 * Math.sin(angle)
          return (
            <line
              key={i}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="currentColor"
              strokeWidth="0.4"
              opacity={i % 3 === 0 ? '0.35' : '0.15'}
            />
          )
        })}

        {/* Jaali octagonal pattern nodes */}
        {Array.from({ length: 8 }, (_, i) => {
          const angle = (i * 45 * Math.PI) / 180
          const cx = 400 + 260 * Math.cos(angle)
          const cy = 400 + 260 * Math.sin(angle)
          return (
            <g key={i}>
              <circle cx={cx} cy={cy} r="16" fill="none" stroke="currentColor" strokeWidth="0.5" opacity="0.3" />
              <circle cx={cx} cy={cy} r="5" fill="currentColor" opacity="0.2" />
            </g>
          )
        })}

        {/* Inner diamond / rangoli cross */}
        <polygon
          points="400,220 440,400 400,580 360,400"
          fill="none"
          stroke="currentColor"
          strokeWidth="0.4"
          opacity="0.2"
        />
        <polygon
          points="220,400 400,440 580,400 400,360"
          fill="none"
          stroke="currentColor"
          strokeWidth="0.4"
          opacity="0.2"
        />

        {/* Center verification mark */}
        <circle cx="400" cy="400" r="28" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.3" />
        <circle cx="400" cy="400" r="8" fill="currentColor" opacity="0.15" />
      </svg>
    </div>
  )
}
