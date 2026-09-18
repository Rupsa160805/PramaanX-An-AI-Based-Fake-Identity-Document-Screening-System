// [FRONTEND-SAFE] Login page — uses POST /api/v1/login
// Demo mode warning displayed if backend returns warning field.
// Token stored in memory only (not localStorage) per privacy requirement.

import { useState } from 'react'
import GeometricBackground from '../components/GeometricBackground'
import { login, ApiError } from '../services/api'

export default function LoginPage({ onLogin }) {
  const [officerId, setOfficerId] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [demoWarning, setDemoWarning] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!officerId.trim() || !password) {
      setError('Please enter your officer ID and password.')
      return
    }
    setBusy(true)
    setError('')
    setDemoWarning('')
    try {
      const data = await login(officerId.trim(), password)
      if (data.warning) setDemoWarning(data.warning)
      // Pass token and officer_id up to App
      onLogin({ token: data.token, officerId: data.officer_id, role: data.role })
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || 'Authentication failed. Please check your credentials.')
      } else {
        setError('Unable to reach the verification service. Check if the backend is running.')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-page">
      {/* Left panel — brand & visual */}
      <div className="login-page__left">
        <GeometricBackground variant="login" />
        <div className="login-page__left-content">
          <div className="login-page__mark">
            <PramaanXFullMark />
          </div>
          <div className="login-page__headline">
            <p className="login-page__eyebrow">PRAMAANX · VERIFICATION PLATFORM</p>
            <h1 className="login-page__hero-text">Trust,<br />verified.</h1>
            <p className="login-page__tagline">
              Intelligent identity and document verification<br />
              for a safer digital India.
            </p>
          </div>
          <div className="login-page__features">
            {['Multi-layer document screening', 'Biometric face verification', 'Explainable risk assessment'].map((f) => (
              <div key={f} className="login-page__feature">
                <span className="login-page__feature-dot" aria-hidden="true" />
                {f}
              </div>
            ))}
          </div>
          <p className="login-page__privacy-note">
            ◉ Prototype · Synthetic/sample records · Decision support only
          </p>
        </div>
      </div>

      {/* Right panel — login form */}
      <div className="login-page__right">
        <div className="login-page__form-wrap">
          <div className="login-page__form-header">
            <div className="login-page__form-mark" aria-hidden="true">
              <MiniPramaanXMark />
            </div>
            <h2 className="login-page__form-title">Officer Sign In</h2>
            <p className="login-page__form-sub">Access the verification command center</p>
          </div>

          {error && (
            <div className="login-page__alert login-page__alert--error" role="alert">
              <span aria-hidden="true">⚠</span>
              <span>{error}</span>
            </div>
          )}

          {demoWarning && (
            <div className="login-page__alert login-page__alert--warning" role="status">
              <span aria-hidden="true">◉</span>
              <span>Development mode active</span>
            </div>
          )}

          <form className="login-page__form" onSubmit={handleSubmit} noValidate>
            <div className="form-field">
              <label className="form-field__label" htmlFor="officer-id">
                Officer ID
              </label>
              <input
                id="officer-id"
                className="form-field__input"
                type="text"
                value={officerId}
                onChange={(e) => setOfficerId(e.target.value)}
                placeholder="Enter your officer ID"
                autoComplete="username"
                autoFocus
                disabled={busy}
                aria-required="true"
              />
            </div>

            <div className="form-field">
              <label className="form-field__label" htmlFor="password">
                Password
              </label>
              <div className="form-field__input-wrap">
                <input
                  id="password"
                  className="form-field__input"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  disabled={busy}
                  aria-required="true"
                />
                <button
                  type="button"
                  className="form-field__toggle"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? '◌' : '●'}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn--verify btn--full"
              disabled={busy}
            >
              {busy ? (
                <span className="btn__loading">
                  <span className="btn__spinner" aria-hidden="true" />
                  Authenticating…
                </span>
              ) : (
                'Sign In →'
              )}
            </button>
          </form>

          <div className="login-page__security">
            <span className="login-page__security-icon" aria-hidden="true">⊛</span>
            <span>Secure verification console · Session not persisted</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function PramaanXFullMark() {
  return (
    <svg viewBox="0 0 120 120" width="120" height="120" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="PramaanX logo">
      <circle cx="60" cy="60" r="55" stroke="#E87522" strokeWidth="1.5" opacity="0.5" />
      <circle cx="60" cy="60" r="40" stroke="#E87522" strokeWidth="1" opacity="0.4" />
      <circle cx="60" cy="60" r="25" stroke="#E87522" strokeWidth="1" opacity="0.3" />
      {Array.from({ length: 24 }, (_, i) => {
        const a = (i * 15 * Math.PI) / 180
        const x1 = 60 + 27 * Math.cos(a), y1 = 60 + 27 * Math.sin(a)
        const x2 = 60 + 53 * Math.cos(a), y2 = 60 + 53 * Math.sin(a)
        return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#E87522" strokeWidth={i % 3 === 0 ? '1' : '0.4'} opacity={i % 3 === 0 ? '0.6' : '0.25'} />
      })}
      <circle cx="60" cy="60" r="10" fill="#E87522" opacity="0.8" />
      <circle cx="60" cy="60" r="5" fill="#07111F" />
    </svg>
  )
}

function MiniPramaanXMark() {
  return (
    <svg viewBox="0 0 40 40" width="32" height="32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="20" cy="20" r="18" stroke="#E87522" strokeWidth="1.5" opacity="0.6" />
      <circle cx="20" cy="20" r="10" stroke="#E87522" strokeWidth="1" opacity="0.4" />
      {Array.from({ length: 8 }, (_, i) => {
        const a = (i * 45 * Math.PI) / 180
        return <line key={i} x1={20 + 11 * Math.cos(a)} y1={20 + 11 * Math.sin(a)} x2={20 + 17 * Math.cos(a)} y2={20 + 17 * Math.sin(a)} stroke="#E87522" strokeWidth="1.2" opacity="0.7" />
      })}
      <circle cx="20" cy="20" r="5" fill="#E87522" opacity="0.9" />
      <circle cx="20" cy="20" r="2.5" fill="#0B1F33" />
    </svg>
  )
}
