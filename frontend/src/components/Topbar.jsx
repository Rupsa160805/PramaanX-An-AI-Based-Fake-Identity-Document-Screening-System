// [FRONTEND-SAFE] Top bar — date/time, service health, mobile sidebar toggle
import { useEffect, useState } from 'react'
import StatusPill from './StatusPill'

export default function Topbar({ serviceOnline, onMenuToggle, title }) {
  const [time, setTime] = useState(() => new Date())

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const timeStr = time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })
  const dateStr = time.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })

  return (
    <header className="topbar" role="banner">
      <div className="topbar__left">
        <button
          className="topbar__menu-btn"
          onClick={onMenuToggle}
          aria-label="Toggle navigation menu"
        >
          <span className="topbar__menu-icon" aria-hidden="true">☰</span>
        </button>
        {title && <h1 className="topbar__title">{title}</h1>}
      </div>
      <div className="topbar__right">
        <time className="topbar__datetime" dateTime={time.toISOString()}>
          <span className="topbar__time">{timeStr}</span>
          <span className="topbar__date">{dateStr}</span>
        </time>
        {serviceOnline === true && (
          <StatusPill tone="success" size="sm">Service Online</StatusPill>
        )}
        {serviceOnline === false && (
          <StatusPill tone="danger" size="sm">Service Offline</StatusPill>
        )}
        {serviceOnline === null && (
          <StatusPill tone="neutral" size="sm">Checking…</StatusPill>
        )}
      </div>
    </header>
  )
}
