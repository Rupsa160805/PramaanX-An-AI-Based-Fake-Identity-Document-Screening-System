// [FRONTEND-SAFE] API Service Layer
// All endpoints preserved exactly from the existing App.jsx integration.
// DO NOT rename, modify payloads, or alter response field access.

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, body = {}) {
    super(message)
    this.name = 'ApiError'
    this.body = body
  }
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {})
  const init = { ...options, headers }
  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
    init.body = JSON.stringify(options.body)
  }
  const response = await fetch(`${API_BASE}${path}`, init)
  const contentType = response.headers.get('content-type') || ''
  const body = contentType.includes('application/json')
    ? await response.json()
    : await response.text()
  if (!response.ok) {
    const message = typeof body === 'object' ? body.error || body.reason : body
    throw new ApiError(message || `Request failed (${response.status})`, body)
  }
  return body
}

// GET /api/v1/health — includes the real Atlas repository status
export async function checkHealth() {
  const body = await request('/api/v1/health')
  if (body.status !== 'ok' || body.database?.connected !== true) {
    throw new ApiError('database unavailable', body)
  }
  return body
}

// POST /api/upload-photo  →  { uploaded, photo_path, error }
export async function uploadPhoto(blob, filename = 'live-photo.jpg') {
  const form = new FormData()
  form.append('photo', blob, filename)
  const body = await request('/api/upload-photo', { method: 'POST', body: form })
  return body.photo_path
}

// POST /api/upload-frames  →  { uploaded, frame_paths, error }
export async function uploadFrames(blobs) {
  const form = new FormData()
  blobs.forEach((blob, index) => form.append('frames', blob, `liveness-${index + 1}.jpg`))
  const body = await request('/api/upload-frames', { method: 'POST', body: form })
  return body.frame_paths
}

// POST /api/capture  →  { photo_path }
export async function captureServicePhoto() {
  const body = await request('/api/capture', { method: 'POST', body: {} })
  return body.photo_path
}

// POST /api/liveness-check  →  { is_live, reason, frames_used, motion_score }
export async function runLivenessCheck(framePaths) {
  return request('/api/liveness-check', {
    method: 'POST',
    body: { frame_paths: framePaths },
  })
}

// POST /api/verify-face  →  { found_in_database, similarity, is_match, threshold_used,
//                             liveness_passed, liveness_performed, confidence_label, reason, error }
export async function verifyFace(payload) {
  return request('/api/verify-face', { method: 'POST', body: payload })
}

// POST /api/v1/verify (multipart)  →  { risk, database_checks, persistence, verification_id, integrity, ... }
export async function verifyDocument(formData) {
  return request('/api/v1/verify', { method: 'POST', body: formData })
}

// POST /api/v1/integrity/verify-all  →  { verification_id, records, chain_status }
// Server-driven: only the verification_id is sent; the backend recomputes
// H1/H2/H3 from the persisted result. React never supplies a hash.
export async function verifyAll(verificationId) {
  return request('/api/v1/integrity/verify-all', {
    method: 'POST',
    body: { verification_id: verificationId },
  })
}

// GET /api/v1/dashboard  →  { total_screenings, today_checks, flagged, high_risk, open_alerts }
export async function fetchDashboard() {
  return request('/api/v1/dashboard')
}

// GET /api/v1/history  →  { items, total }
export async function fetchHistory(limit = 25, skip = 0, search = undefined) {
  const params = new URLSearchParams({ limit, skip })
  if (search) params.set('search', search)
  return request(`/api/v1/history?${params}`)
}

// GET /api/v1/alerts  →  { items }
export async function fetchAlerts(status = 'open') {
  return request(`/api/v1/alerts?status=${encodeURIComponent(status)}`)
}

// POST /api/v1/alerts/:id/resolve  →  { resolved, alert_id }
export async function resolveAlert(alertId, officerId) {
  return request(`/api/v1/alerts/${encodeURIComponent(alertId)}/resolve`, {
    method: 'POST',
    headers: officerId ? { 'X-Officer-ID': officerId } : {},
    body: {},
  })
}

// POST /api/v1/login  →  { token, officer_id, role, warning? }
export async function login(officerId, password) {
  return request('/api/v1/login', {
    method: 'POST',
    body: { officer_id: officerId, password },
  })
}
