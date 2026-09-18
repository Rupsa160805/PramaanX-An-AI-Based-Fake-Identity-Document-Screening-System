// [FRONTEND-SAFE] History page — GET /api/v1/history
// Premium table with search support. API contract preserved.

import { useState } from 'react'

function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  return isNaN(d.getTime()) ? String(value) : d.toLocaleString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  })
}

export default function HistoryPage({ history, busy, onRefresh }) {
  const [search, setSearch] = useState('')
  const [searching, setSearching] = useState(false)

  const handleSearch = async (e) => {
    e.preventDefault()
    setSearching(true)
    try {
      await onRefresh(search.trim() || undefined)
    } finally {
      setSearching(false)
    }
  }

  const items = history?.items || []
  const total = history?.total ?? 0

  return (
    <div className="page-content">
      {/* Header */}
      <section className="page-header">
        <div>
          <p className="eyebrow">RECORD MANAGEMENT</p>
          <h2 className="page-header__title">Screening History</h2>
          <p className="page-header__sub">
            Persisted verification results loaded from the configured repository.
          </p>
        </div>
        <button className="btn btn--secondary" onClick={() => onRefresh()} disabled={busy}>
          {busy ? 'Refreshing…' : '↻ Refresh Records'}
        </button>
      </section>

      {/* Summary + search */}
      <div className="history-toolbar">
        <div className="history-summary">
          <strong className="history-summary__count">{total}</strong>
          <span className="history-summary__label">stored verification results</span>
        </div>
        <form className="history-search" onSubmit={handleSearch} role="search">
          <input
            className="form-field__input history-search__input"
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by document number…"
            aria-label="Search verification history"
          />
          <button
            type="submit"
            className="btn btn--secondary btn--sm"
            disabled={searching || busy}
          >
            Search
          </button>
        </form>
      </div>

      {/* Table */}
      <section className="panel history-panel">
        {items.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table" aria-label="Verification history">
              <thead>
                <tr>
                  <th scope="col">Document</th>
                  <th scope="col">Submitted</th>
                  <th scope="col">Risk</th>
                  <th scope="col">Face</th>
                  <th scope="col">Review Status</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item._id || item.submission_id} className="data-table__row">
                    <td>
                      <span className="data-table__doc-num">
                        {item.document_number || '—'}
                      </span>
                    </td>
                    <td className="data-table__date">
                      {formatDate(item.submitted_at || item.created_at)}
                    </td>
                    <td>
                      <span className={`risk-badge risk-badge--${item.risk?.level || 'unknown'}`}>
                        {String(item.risk?.level || 'unknown').toUpperCase()}
                      </span>
                    </td>
                    <td className="data-table__face">
                      {item.face_verification?.is_match === true
                        ? <span className="data-table__match">✓ Match</span>
                        : item.face_verification?.error
                          ? <span className="data-table__error">{item.face_verification.error}</span>
                          : <span className="data-table__na">Not run</span>}
                    </td>
                    <td>
                      <span className={`review-badge review-badge--${item.manual_review?.status || 'pending'}`}>
                        {item.manual_review?.status || 'pending'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state__icon" aria-hidden="true">≡</div>
            <p className="empty-state__title">No verification results</p>
            <p className="empty-state__sub">
              {search ? 'No results match your search.' : 'Completed document screenings will appear here.'}
            </p>
          </div>
        )}
      </section>
    </div>
  )
}
