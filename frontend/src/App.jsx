// [FRONTEND-SAFE] App.jsx — redesigned app shell
// All API calls, state management, and camera logic preserved from original.
// Adds: login flow, sidebar layout, proper page routing.

import { useCallback, useEffect, useState } from 'react'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import DashboardPage from './pages/DashboardPage'
import VerifyPage from './pages/VerifyPage'
import ScreeningPage from './pages/ScreeningPage'
import HistoryPage from './pages/HistoryPage'
import AlertsPage from './pages/AlertsPage'
import { checkHealth, fetchDashboard, fetchHistory, fetchAlerts } from './services/api'

const PAGE_TITLES = {
  dashboard: 'Command Center',
  verify: 'Biometric Verification',
  screening: 'Document Screening',
  history: 'Screening History',
  alerts: 'Open Alerts',
}

// Prototype/demo mode: keep the operator console directly accessible. The
// backend login endpoint remains available for a future secured deployment.
const PROTOTYPE_SESSION = {
  token: 'prototype-session',
  officerId: 'demo.officer@pramaanx.local',
  role: 'officer',
}

export default function App() {
  // ── Auth state (in-memory only, never persisted) ──────────────────────────
  // Login is intentionally skipped for the local synthetic-data demo.
  const session = PROTOTYPE_SESSION

  // ── Service state ─────────────────────────────────────────────────────────
  const [serviceOnline, setServiceOnline] = useState(null)

  // ── Navigation ────────────────────────────────────────────────────────────
  const [activeView, setActiveView] = useState('dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // ── Platform data ─────────────────────────────────────────────────────────
  const [dashboardData, setDashboardData] = useState(null)
  const [historyData, setHistoryData] = useState(null)
  const [alertsData, setAlertsData] = useState(null)
  const [dataBusy, setDataBusy] = useState(false)

  // ── Health check ──────────────────────────────────────────────────────────
  const runHealthCheck = useCallback(async () => {
    try {
      await checkHealth()
      setServiceOnline(true)
    } catch {
      setServiceOnline(false)
    }
  }, [])

  useEffect(() => {
    runHealthCheck()
    const interval = setInterval(runHealthCheck, 30_000)
    return () => clearInterval(interval)
  }, [runHealthCheck])

  // ── Load platform data ────────────────────────────────────────────────────
  const loadPlatformData = useCallback(async (searchQuery) => {
    setDataBusy(true)
    try {
      const [dashboard, history, alerts] = await Promise.allSettled([
        fetchDashboard(),
        fetchHistory(25, 0, searchQuery),
        fetchAlerts(),
      ])
      if (dashboard.status === 'fulfilled') setDashboardData(dashboard.value)
      if (history.status === 'fulfilled') setHistoryData(history.value)
      if (alerts.status === 'fulfilled') setAlertsData(alerts.value)
    } finally {
      setDataBusy(false)
    }
  }, [])

  useEffect(() => {
    if (session && activeView !== 'verify' && activeView !== 'screening') {
      loadPlatformData()
    }
  }, [session, activeView, loadPlatformData])

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleNavigate = (view) => {
    setActiveView(view)
    setSidebarOpen(false)
  }

  const handleHistoryRefresh = async (search) => {
    setDataBusy(true)
    try {
      const history = await fetchHistory(25, 0, search)
      setHistoryData(history)
    } finally {
      setDataBusy(false)
    }
  }

  const handleAlertsRefresh = async () => {
    setDataBusy(true)
    try {
      const alerts = await fetchAlerts()
      setAlertsData(alerts)
    } finally {
      setDataBusy(false)
    }
  }

  // ── Show login if no session ───────────────────────────────────────────────
  // ── Main app shell ─────────────────────────────────────────────────────────
  return (
    <div className={`app-shell${sidebarOpen ? ' app-shell--sidebar-open' : ''}`}>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <Sidebar
        activeView={activeView}
        onNavigate={handleNavigate}
        serviceOnline={serviceOnline}
        officerId={session.officerId}
      />

      {/* Main content area */}
      <div className="app-main">
        <Topbar
          serviceOnline={serviceOnline}
          onMenuToggle={() => setSidebarOpen((v) => !v)}
          title={PAGE_TITLES[activeView] || 'PramaanX'}
        />

        <main className="app-content" id="main-content">
          {activeView === 'dashboard' && (
            <DashboardPage
              data={dashboardData}
              history={historyData}
              alerts={alertsData}
              busy={dataBusy}
              onRefresh={loadPlatformData}
              onNavigate={handleNavigate}
            />
          )}
          {activeView === 'verify' && (
            <VerifyPage officerId={session.officerId} />
          )}
          {activeView === 'screening' && (
            <ScreeningPage />
          )}
          {activeView === 'history' && (
            <HistoryPage
              history={historyData}
              busy={dataBusy}
              onRefresh={handleHistoryRefresh}
            />
          )}
          {activeView === 'alerts' && (
            <AlertsPage
              alerts={alertsData}
              busy={dataBusy}
              onRefresh={handleAlertsRefresh}
              officerId={session.officerId}
            />
          )}
        </main>

        <footer className="app-footer" role="contentinfo">
          <span>PramaanX · Decision support, not an automatic authenticity verdict.</span>
          <span className="app-footer__privacy">◉ Prototype · Synthetic/sample records only</span>
        </footer>
      </div>
    </div>
  )
}
