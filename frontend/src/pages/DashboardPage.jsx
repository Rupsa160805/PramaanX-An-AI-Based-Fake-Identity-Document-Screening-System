// [FRONTEND-SAFE] Dashboard page — uses /api/v1/dashboard, /api/v1/history, /api/v1/alerts
// Only displays actual API data. No fabricated metrics.

import StatCard from '../components/StatCard'
import StatusPill from '../components/StatusPill'
import GeometricBackground from '../components/GeometricBackground'

function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  return isNaN(d.getTime()) ? String(value) : d.toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export default function DashboardPage({ data, history, alerts, busy, onRefresh, onNavigate }) {
  const metrics = data || {}

  return (
    <div className="page-content">
      {/* Hero section */}
      <section className="dashboard-hero">
        <GeometricBackground variant="dashboard" />
        <div className="dashboard-hero__content">
          <p className="eyebrow">VERIFICATION COMMAND CENTER</p>
          <h2 className="dashboard-hero__title">
            Identity Verification<br />Intelligence
          </h2>
          <p className="dashboard-hero__sub">
            Monitor verification activity and review high-risk cases in real time.
          </p>
          <div className="dashboard-hero__actions">
            <button className="btn btn--saffron" onClick={() => onNavigate('screening')}>
              New Document Screening →
            </button>
            <button className="btn btn--ghost-light" onClick={() => onNavigate('verify')}>
              Biometric Check
            </button>
          </div>
        </div>
        {/* AI Engine visualization */}
        <div className="dashboard-hero__engine" aria-hidden="true">
          <div className="engine-ring engine-ring--outer">
            {['OCR', 'MRZ', 'DATABASE', 'TAMPERING', 'FACE', 'RISK'].map((label, i) => {
              const angle = i * 60
              const rad = (angle * Math.PI) / 180
              const x = 50 + 44 * Math.cos(rad - Math.PI / 2)
              const y = 50 + 44 * Math.sin(rad - Math.PI / 2)
              return (
                <div
                  key={label}
                  className="engine-node"
                  style={{ left: `${x}%`, top: `${y}%` }}
                >
                  {label}
                </div>
              )
            })}
          </div>
          <div className="engine-ring engine-ring--center">
            <span className="engine-brand">PRAMAANX</span>
            <span className="engine-sub">AI ENGINE</span>
          </div>
        </div>
      </section>

      {/* Stat cards */}
      <section className="dashboard-stats" aria-label="Key metrics">
        <StatCard
          label="Documents Screened"
          value={metrics.total_screenings}
          sub="Total persisted verifications"
          icon="◫"
          tone="default"
        />
        <StatCard
          label="Today's Checks"
          value={metrics.today_checks}
          sub="UTC calendar day"
          icon="◉"
          tone="default"
        />
        <StatCard
          label="Flagged Cases"
          value={metrics.flagged}
          sub="Medium or high risk"
          icon="◬"
          tone="warning"
        />
        <StatCard
          label="High Risk"
          value={metrics.high_risk}
          sub={`${metrics.open_alerts ?? 0} open alerts`}
          icon="⊛"
          tone="danger"
        />
      </section>

      {/* Data panels */}
      <div className="dashboard-panels">
        {/* Recent screenings */}
        <section className="panel">
          <div className="panel__header">
            <div>
              <p className="eyebrow">RECENT ACTIVITY</p>
              <h3 className="panel__title">Latest Screenings</h3>
            </div>
            <button className="btn btn--ghost btn--sm" onClick={onRefresh} disabled={busy}>
              {busy ? 'Refreshing…' : '↻ Refresh'}
            </button>
          </div>
          {history?.items?.length ? (
            <div className="data-list">
              {history.items.slice(0, 6).map((item) => (
                <div className="data-row" key={item._id || item.submission_id}>
                  <div className="data-row__main">
                    <strong className="data-row__doc">
                      {item.document_number || 'Document unavailable'}
                    </strong>
                    <span className="data-row__date">{formatDate(item.submitted_at || item.created_at)}</span>
                  </div>
                  <div className="data-row__meta">
                    <span className={`risk-badge risk-badge--${item.risk?.level || 'unknown'}`}>
                      {String(item.risk?.level || 'unknown').toUpperCase()}
                    </span>
                    <span className="data-row__review">
                      {item.manual_review?.status || 'pending'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state__icon" aria-hidden="true">◫</div>
              <p className="empty-state__title">No screenings yet</p>
              <p className="empty-state__sub">Completed document checks will appear here.</p>
            </div>
          )}
          <div className="panel__footer">
            <button className="btn btn--ghost btn--sm" onClick={() => onNavigate('history')}>
              View all history →
            </button>
          </div>
        </section>

        {/* Open alerts */}
        <section className="panel">
          <div className="panel__header">
            <div>
              <p className="eyebrow">OFFICER QUEUE</p>
              <h3 className="panel__title">Open Alerts</h3>
            </div>
            <button className="btn btn--ghost btn--sm" onClick={() => onNavigate('alerts')}>
              View all →
            </button>
          </div>
          {alerts?.items?.length ? (
            <div className="data-list">
              {alerts.items.slice(0, 5).map((alert) => (
                <div className="data-row data-row--alert" key={alert._id}>
                  <div className="data-row__alert-indicator" aria-hidden="true" />
                  <div className="data-row__main">
                    <strong className="data-row__doc">
                      {alert.document_number || 'Unknown document'}
                    </strong>
                    <span className="data-row__date">{alert.reason_summary || 'Review required'}</span>
                  </div>
                  <span className={`risk-badge risk-badge--${alert.risk_level?.toLowerCase() || 'high'}`}>
                    {alert.risk_level || 'HIGH'}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state__icon empty-state__icon--success" aria-hidden="true">✓</div>
              <p className="empty-state__title">No open alerts</p>
              <p className="empty-state__sub">All cases are resolved or clear.</p>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
