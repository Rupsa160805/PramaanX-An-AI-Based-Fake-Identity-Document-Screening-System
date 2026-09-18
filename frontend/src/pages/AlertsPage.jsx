// [FRONTEND-SAFE] Alerts page — GET /api/v1/alerts + POST /api/v1/alerts/:id/resolve
// Displays real alert items. Resolve button calls real endpoint.

import { useState } from 'react'
import { resolveAlert } from '../services/api'

function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  return isNaN(d.getTime()) ? String(value) : d.toLocaleString('en-IN', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
  })
}

export default function AlertsPage({ alerts, busy, onRefresh, officerId }) {
  const [resolvingId, setResolvingId] = useState(null)
  const [resolveError, setResolveError] = useState('')

  const handleResolve = async (alertId) => {
    setResolvingId(alertId)
    setResolveError('')
    try {
      await resolveAlert(alertId, officerId)
      await onRefresh()
    } catch (e) {
      setResolveError(e.message || 'Could not resolve alert.')
    } finally {
      setResolvingId(null)
    }
  }

  const items = alerts?.items || []

  return (
    <div className="page-content">
      {/* Header */}
      <section className="page-header page-header--danger-accent">
        <div>
          <p className="eyebrow">OFFICER QUEUE</p>
          <h2 className="page-header__title">Open Alerts</h2>
          <p className="page-header__sub">
            High-risk cases flagged for manual officer review.
          </p>
        </div>
        <button className="btn btn--secondary" onClick={onRefresh} disabled={busy}>
          {busy ? 'Refreshing…' : '↻ Refresh'}
        </button>
      </section>

      {resolveError && (
        <div className="inline-alert inline-alert--error" role="alert">
          <span aria-hidden="true">⚠</span>
          <div><strong>Error</strong><span>{resolveError}</span></div>
        </div>
      )}

      {/* Alert timeline */}
      <section className="panel alerts-panel">
        {items.length > 0 ? (
          <div className="alerts-list">
            {items.map((alert) => {
              const level = (alert.risk_level || 'high').toLowerCase()
              return (
                <div key={alert._id} className={`alert-item alert-item--${level}`}>
                  <div className="alert-item__stripe" aria-hidden="true" />
                  <div className="alert-item__body">
                    <div className="alert-item__header">
                      <div>
                        <span className={`risk-badge risk-badge--${level}`}>
                          {String(alert.risk_level || 'HIGH').toUpperCase()}
                        </span>
                        <strong className="alert-item__doc">
                          {alert.document_number || 'Unknown Document'}
                        </strong>
                      </div>
                      <time className="alert-item__time" dateTime={alert.created_at}>
                        {formatDate(alert.created_at)}
                      </time>
                    </div>
                    <p className="alert-item__reason">
                      {alert.reason_summary || 'Manual review required.'}
                    </p>
                    <div className="alert-item__footer">
                      <span className={`review-badge review-badge--${alert.status || 'open'}`}>
                        {alert.status || 'open'}
                      </span>
                      {alert.status !== 'resolved' && (
                        <button
                          className="btn btn--ghost btn--sm"
                          onClick={() => handleResolve(alert._id)}
                          disabled={resolvingId === alert._id || busy}
                        >
                          {resolvingId === alert._id ? 'Resolving…' : 'Mark Resolved'}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state__icon empty-state__icon--success" aria-hidden="true">✓</div>
            <p className="empty-state__title">No open alerts</p>
            <p className="empty-state__sub">All cases are resolved or below the alert threshold.</p>
          </div>
        )}
      </section>
    </div>
  )
}
