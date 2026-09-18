// [FRONTEND-SAFE] Evidence card — displays individual verification module results
// Only shows values from actual API response

export default function EvidenceCard({ icon, title, status, metric, detail, tone = 'neutral', expandable }) {
  const TONES = {
    success: { cls: 'evidence-card--success', indicator: '✓' },
    warning: { cls: 'evidence-card--warning', indicator: '⚠' },
    danger: { cls: 'evidence-card--danger', indicator: '✕' },
    neutral: { cls: 'evidence-card--neutral', indicator: '○' },
    skipped: { cls: 'evidence-card--skipped', indicator: '–' },
  }
  const t = TONES[tone] || TONES.neutral

  return (
    <div className={`evidence-card ${t.cls}`} role="article">
      <div className="evidence-card__header">
        <span className="evidence-card__icon" aria-hidden="true">{icon}</span>
        <div className="evidence-card__meta">
          <span className="evidence-card__title">{title}</span>
          {metric && (
            <span className="evidence-card__metric">{metric}</span>
          )}
        </div>
        <div className="evidence-card__status">
          <span className="evidence-card__indicator" aria-hidden="true">{t.indicator}</span>
          <span className={`evidence-card__status-text evidence-card__status--${tone}`}>
            {status}
          </span>
        </div>
      </div>
      {detail && (
        <p className="evidence-card__detail">{detail}</p>
      )}
    </div>
  )
}
