// [FRONTEND-SAFE] Premium stat card for dashboard metrics
// Only displays values actually returned by the API — no fabrication

export default function StatCard({ label, value, sub, tone = 'default', icon }) {
  return (
    <div className={`stat-card stat-card--${tone}`}>
      <div className="stat-card__header">
        {icon && <span className="stat-card__icon" aria-hidden="true">{icon}</span>}
        <span className="stat-card__label">{label}</span>
      </div>
      <strong className="stat-card__value">
        {value ?? <span className="stat-card__dash">—</span>}
      </strong>
      {sub && <small className="stat-card__sub">{sub}</small>}
    </div>
  )
}
