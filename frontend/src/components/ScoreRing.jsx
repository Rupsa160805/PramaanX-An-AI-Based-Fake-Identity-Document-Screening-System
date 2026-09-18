// [FRONTEND-SAFE] Score ring — enhanced from original, shows biometric similarity
// ONLY displays similarity from actual backend response. null → shows '—'
import { useEffect, useRef, useState } from 'react'

export default function ScoreRing({ similarity, isMatch }) {
  const [displayed, setDisplayed] = useState(0)
  const rafRef = useRef(null)
  const startTimeRef = useRef(null)

  const score = typeof similarity === 'number' ? Math.round(similarity * 100) : null
  const angle = score === null ? 0 : Math.max(0, Math.min(360, score * 3.6))

  useEffect(() => {
    if (score === null) return
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    startTimeRef.current = null
    const animate = (ts) => {
      if (!startTimeRef.current) startTimeRef.current = ts
      const progress = Math.min((ts - startTimeRef.current) / 900, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplayed(Math.round(eased * score))
      if (progress < 1) rafRef.current = requestAnimationFrame(animate)
    }
    rafRef.current = requestAnimationFrame(animate)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [score])

  const matchColor = isMatch ? '#0E7C66' : '#C83B3B'
  const trackColor = isMatch ? '#E0F5F0' : '#FDEAEA'

  return (
    <div
      className={`score-ring score-ring--${isMatch ? 'match' : 'no-match'}`}
      style={{ '--score-angle': `${angle}deg`, '--match-color': matchColor, '--track-color': trackColor }}
      role="img"
      aria-label={`Similarity score ${score !== null ? score + '%' : 'unavailable'}`}
    >
      <div className="score-ring__inner">
        <strong className="score-ring__value">
          {score === null ? '—' : `${displayed}%`}
        </strong>
        <span className="score-ring__label">similarity</span>
      </div>
    </div>
  )
}
