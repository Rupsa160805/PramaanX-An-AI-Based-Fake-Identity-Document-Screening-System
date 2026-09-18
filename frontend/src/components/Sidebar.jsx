// [FRONTEND-SAFE] Premium sidebar navigation
// Maps to existing views only — no invented features

import StatusPill from './StatusPill'

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: '⊞' },
  { id: 'screening', label: 'Verify Document', icon: '◫' },
  { id: 'verify', label: 'Biometric Check', icon: '◉' },
  { id: 'history', label: 'History', icon: '≡' },
  { id: 'alerts', label: 'Alerts', icon: '◬' },
]

export default function Sidebar({ activeView, onNavigate, serviceOnline, officerId, onLogout }) {
  return (
    <aside className="sidebar" role="navigation" aria-label="Primary navigation">
      {/* Brand */}
      <div className="sidebar__brand">
        <div className="sidebar__logo" aria-label="PramaanX logo">
          <PramaanXMark />
        </div>
        <div className="sidebar__brand-text">
          <span className="sidebar__brand-name">Praamaan<span className="sidebar__brand-x">X</span></span>
          <span className="sidebar__brand-tagline">Trust, Verified.</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar__nav">
        <p className="sidebar__nav-label">OPERATOR CONSOLE</p>
        <ul className="sidebar__nav-list" role="list">
          {NAV_ITEMS.map((item) => (
            <li key={item.id}>
              <button
                className={`sidebar__nav-item${activeView === item.id ? ' sidebar__nav-item--active' : ''}`}
                onClick={() => onNavigate(item.id)}
                aria-current={activeView === item.id ? 'page' : undefined}
              >
                <span className="sidebar__nav-icon" aria-hidden="true">{item.icon}</span>
                <span className="sidebar__nav-text">{item.label}</span>
                {item.id === 'alerts' && activeView !== 'alerts' && (
                  <span className="sidebar__nav-badge" aria-label="has alerts" />
                )}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {/* System Status */}
      <div className="sidebar__status">
        <p className="sidebar__nav-label">SYSTEM STATUS</p>
        <div className="sidebar__status-row">
          <span>AI Services</span>
          <StatusPill tone={serviceOnline ? 'success' : 'danger'} size="sm">
            {serviceOnline ? 'Online' : 'Offline'}
          </StatusPill>
        </div>
        <div className="sidebar__status-row">
          <span>Biometric</span>
          <StatusPill tone={serviceOnline ? 'success' : 'neutral'} size="sm">
            {serviceOnline ? 'Ready' : 'Checking'}
          </StatusPill>
        </div>
      </div>

      {/* Officer profile */}
      <div className="sidebar__profile">
        <div className="sidebar__profile-avatar" aria-hidden="true">
          {officerId ? officerId.slice(0, 2).toUpperCase() : 'OF'}
        </div>
        <div className="sidebar__profile-info">
          <strong className="sidebar__profile-name">{officerId || 'Officer'}</strong>
          <span className="sidebar__profile-role">Authorized Officer</span>
        </div>
        {onLogout && (
          <button
            className="sidebar__logout"
            onClick={onLogout}
            aria-label="Sign out"
            title="Sign out"
          >
            ↩
          </button>
        )}
      </div>

      {/* Privacy notice */}
      <p className="sidebar__privacy">
        ◉ Prototype · Synthetic records only
      </p>
    </aside>
  )
}

function PramaanXMark() {
  return (
    <svg viewBox="0 0 40 40" width="40" height="40" aria-hidden="true" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Outer ring */}
      <circle cx="20" cy="20" r="18" stroke="#E87522" strokeWidth="1.5" opacity="0.6" />
      {/* Inner ring */}
      <circle cx="20" cy="20" r="12" stroke="#E87522" strokeWidth="1" opacity="0.4" />
      {/* 8 spokes */}
      {Array.from({ length: 8 }, (_, i) => {
        const angle = (i * 45 * Math.PI) / 180
        const x1 = 20 + 13 * Math.cos(angle)
        const y1 = 20 + 13 * Math.sin(angle)
        const x2 = 20 + 17 * Math.cos(angle)
        const y2 = 20 + 17 * Math.sin(angle)
        return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#E87522" strokeWidth="1.2" opacity="0.7" />
      })}
      {/* Center checkmark abstraction */}
      <circle cx="20" cy="20" r="5" fill="#E87522" opacity="0.9" />
      <circle cx="20" cy="20" r="2.5" fill="#07111F" />
    </svg>
  )
}
