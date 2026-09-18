// [FRONTEND-SAFE] Biometric verification page — complete redesign of the existing verify flow
// ALL API calls preserved exactly: /api/upload-photo, /api/upload-frames,
// /api/liveness-check, /api/verify-face, /api/capture
// No fake scores. Null similarity → '—'. All values from backend.

import { useRef, useState } from 'react'
import CameraCapture from '../components/CameraCapture'
import ScoreRing from '../components/ScoreRing'
import EvidenceCard from '../components/EvidenceCard'
import StatusPill from '../components/StatusPill'
import { uploadPhoto, uploadFrames, captureServicePhoto, runLivenessCheck, verifyFace, ApiError } from '../services/api'

function Step({ number, label, active, complete }) {
  return (
    <div className={`step-indicator ${active ? 'step-indicator--active' : ''} ${complete ? 'step-indicator--complete' : ''}`}>
      <span className="step-indicator__num" aria-hidden="true">
        {complete ? '✓' : number}
      </span>
      <span className="step-indicator__label">{label}</span>
    </div>
  )
}

export default function VerifyPage() {
  const [documentNumber, setDocumentNumber] = useState('')
  const [livePhotoPath, setLivePhotoPath] = useState('')
  const [livePreview, setLivePreview] = useState('')
  const [livenessFramePaths, setLivenessFramePaths] = useState([])
  const [livenessResult, setLivenessResult] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  // CameraCapture exposes a ref to its snapshot function for liveness
  const cameraRef = useRef(null)

  const showError = (val) => {
    setError(val instanceof Error ? val.message : String(val))
    setNotice('')
  }

  // ── Handlers ─────────────────────────────────────────────────────────────────
  const handlePhotoReady = async (blob) => {
    setBusy('photo'); setError('')
    setLivePreview(URL.createObjectURL(blob))
    try {
      const path = await uploadPhoto(blob)
      setLivePhotoPath(path)
      setNotice('Live photo captured and uploaded.')
    } catch (e) { showError(e) } finally { setBusy('') }
  }

  const handleUploadFile = async (file) => {
    setBusy('photo'); setError('')
    setLivePreview(URL.createObjectURL(file))
    try {
      const path = await uploadPhoto(file, file.name)
      setLivePhotoPath(path)
      setNotice('Photo uploaded and ready for verification.')
    } catch (e) { showError(e) } finally { setBusy('') }
  }

  const handleServiceCapture = async () => {
    setBusy('photo'); setError('')
    try {
      const path = await captureServicePhoto()
      setLivePhotoPath(path)
      setLivePreview('')
      setNotice('Photo captured by service webcam.')
    } catch (e) { showError(e) } finally { setBusy('') }
  }

  const handleRunLiveness = async () => {
    if (!cameraRef.current?.snapshot) {
      setError('Open the camera first to run a liveness check.')
      return
    }
    setBusy('liveness'); setError('')
    try {
      const blobs = []
      for (let i = 0; i < 3; i++) {
        blobs.push(await cameraRef.current.snapshot())
        if (i < 2) await new Promise((r) => setTimeout(r, 320))
      }
      const paths = await uploadFrames(blobs)
      setLivenessFramePaths(paths)
      const body = await runLivenessCheck(paths)
      setLivenessResult(body)
      setNotice(body.is_live ? 'Liveness passed.' : 'Liveness check did not pass.')
    } catch (e) { showError(e) } finally { setBusy('') }
  }

  const handleVerify = async () => {
    if (!documentNumber.trim()) { setError('Enter the document number before verifying.'); return }
    if (!livePhotoPath) { setError('Capture or upload a live photo first.'); return }
    setBusy('verify'); setError(''); setResult(null)
    try {
      const payload = { live_photo_path: livePhotoPath, document_number: documentNumber.trim() }
      if (livenessFramePaths.length) payload.frame_paths = livenessFramePaths
      const data = await verifyFace(payload)
      setResult(data)
      setNotice('Verification completed. Review the evidence below.')
    } catch (e) {
      if (e instanceof ApiError && e.body) setResult(e.body)
      showError(e)
    } finally { setBusy('') }
  }

  const handleReset = () => {
    setDocumentNumber(''); setLivePhotoPath(''); setLivePreview('')
    setLivenessFramePaths([]); setLivenessResult(null)
    setResult(null); setError(''); setNotice('')
    cameraRef.current?.stopCamera?.()
  }

  // Step tracking
  const activeStep = result ? 3 : livePhotoPath ? 2 : 1
  const match = result?.is_match === true

  // Result tone
  const resultTone = match ? 'success' : result ? 'danger' : 'neutral'

  return (
    <div className="page-content">
      {/* Page header */}
      <section className="page-header">
        <div>
          <p className="eyebrow">BIOMETRIC VERIFICATION</p>
          <h2 className="page-header__title">Verify the person behind the document.</h2>
          <p className="page-header__sub">
            Capture a live face, compare against the authorized reference record.
          </p>
        </div>
        <StatusPill tone="neutral" size="md">◉ Synthetic/demo records only</StatusPill>
      </section>

      {/* Progress steps */}
      <div className="step-bar" role="list" aria-label="Verification progress">
        <Step number="01" label="Identify Document" active={activeStep === 1} complete={activeStep > 1} />
        <span className="step-bar__connector" aria-hidden="true" />
        <Step number="02" label="Capture Evidence" active={activeStep === 2} complete={activeStep > 2} />
        <span className="step-bar__connector" aria-hidden="true" />
        <Step number="03" label="Review Result" active={activeStep === 3} complete={false} />
      </div>

      {/* Workspace */}
      <div className="verify-grid">
        {/* Input panel */}
        <section className="panel verify-grid__input">
          <div className="panel__header">
            <div>
              <p className="eyebrow">CASE INPUT</p>
              <h3 className="panel__title">Start a Verification</h3>
            </div>
            <span className="panel__number" aria-hidden="true">01</span>
          </div>

          <div className="form-field">
            <label className="form-field__label" htmlFor="doc-number">Document Number</label>
            <input
              id="doc-number"
              className="form-field__input form-field__input--mono"
              type="text"
              value={documentNumber}
              onChange={(e) => setDocumentNumber(e.target.value)}
              placeholder="e.g. Q2714253"
              autoComplete="off"
              disabled={busy !== ''}
            />
            <p className="form-field__help">Matched against the reference database record.</p>
          </div>

          <div className="verify-divider">
            <span>Live Evidence</span>
          </div>

          <CameraCapture
            ref={cameraRef}
            onPhotoReady={handlePhotoReady}
            onUploadFile={handleUploadFile}
            onServiceCapture={handleServiceCapture}
            livePreview={livePreview}
            livePhotoPath={livePhotoPath}
            livenessResult={livenessResult}
            busy={busy}
            onRunLiveness={handleRunLiveness}
          />

          <button
            className="btn btn--verify btn--full"
            onClick={handleVerify}
            disabled={busy !== '' || !documentNumber.trim() || !livePhotoPath}
          >
            {busy === 'verify' ? (
              <span className="btn__loading"><span className="btn__spinner" aria-hidden="true" /> Verifying…</span>
            ) : (
              'Verify Face →'
            )}
          </button>
          <button className="btn--reset" onClick={handleReset}>Clear case</button>
        </section>

        {/* Result panel */}
        <section className="panel verify-grid__result">
          <div className="panel__header">
            <div>
              <p className="eyebrow">EVIDENCE REVIEW</p>
              <h3 className="panel__title">Biometric Result</h3>
            </div>
            <span className="panel__number" aria-hidden="true">02</span>
          </div>

          {/* Alerts */}
          {error && (
            <div className="inline-alert inline-alert--error" role="alert">
              <span aria-hidden="true">⚠</span>
              <div>
                <strong>Action needed</strong>
                <span>{error}</span>
              </div>
            </div>
          )}
          {notice && !error && (
            <div className="inline-alert inline-alert--info" role="status">
              <span aria-hidden="true">◉</span>
              <div>
                <strong>Update</strong>
                <span>{notice}</span>
              </div>
            </div>
          )}

          {/* Empty state */}
          {!result && !error && (
            <div className="empty-result">
              <div className="empty-result__geo" aria-hidden="true">
                <svg viewBox="0 0 120 120" width="90" height="90" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="60" cy="60" r="55" stroke="currentColor" strokeWidth="0.8" opacity="0.2" />
                  <circle cx="60" cy="60" r="38" stroke="currentColor" strokeWidth="0.8" opacity="0.15" />
                  <circle cx="60" cy="60" r="20" stroke="currentColor" strokeWidth="0.8" opacity="0.12" />
                  <text x="60" y="65" textAnchor="middle" fontSize="22" fill="currentColor" opacity="0.3" fontFamily="system-ui">✦</text>
                </svg>
              </div>
              <h4 className="empty-result__title">Awaiting Verification</h4>
              <p className="empty-result__sub">
                Complete the case input. The system will show similarity score, threshold decision, liveness state, and an explanation here.
              </p>
            </div>
          )}

          {/* Result */}
          {result && (
            <div className="result-content">
              {/* Decision banner */}
              <div className={`decision-banner decision-banner--${resultTone}`}>
                <div>
                  <span className="decision-banner__kicker">BIOMETRIC DECISION</span>
                  <h4 className="decision-banner__verdict">
                    {match ? 'Face Match Confirmed' : 'No Face Match'}
                  </h4>
                </div>
                <StatusPill tone={resultTone}>
                  {result.confidence_label || 'REVIEW'}
                </StatusPill>
              </div>

              {/* Score + similarity */}
              <div className="result-score-row">
                <ScoreRing similarity={result.similarity} isMatch={match} />
                <div className="result-score-detail">
                  <span className="result-score-detail__label">Similarity Score</span>
                  <strong className="result-score-detail__value">
                    {typeof result.similarity === 'number' ? result.similarity.toFixed(4) : 'Unavailable'}
                  </strong>
                  <span className="result-score-detail__threshold">
                    Threshold: <b>{typeof result.threshold_used === 'number' ? result.threshold_used.toFixed(3) : '—'}</b>
                  </span>
                </div>
              </div>

              {/* Evidence cards */}
              <div className="evidence-grid">
                <EvidenceCard
                  icon="◎"
                  title="Reference Record"
                  status={result.found_in_database ? 'Found' : 'Not Found'}
                  metric={result.found_in_database ? 'MATCHED' : 'MISSING'}
                  detail={result.found_in_database
                    ? 'Document found in the reference database.'
                    : 'This document number is not in the reference database.'}
                  tone={result.found_in_database ? 'success' : 'danger'}
                />
                <EvidenceCard
                  icon="◌"
                  title="Liveness Check"
                  status={!result.liveness_performed ? 'Skipped' : result.liveness_passed ? 'Passed' : 'Failed'}
                  metric={result.liveness_performed
                    ? (result.liveness_passed ? 'LIVE' : 'FAIL')
                    : 'N/A'}
                  detail={result.liveness_performed
                    ? (result.liveness_passed ? 'Motion detected across frames.' : 'Motion check did not pass.')
                    : 'No liveness frames were provided for this request.'}
                  tone={!result.liveness_performed ? 'skipped' : result.liveness_passed ? 'success' : 'danger'}
                />
              </div>

              {/* Explainability */}
              <div className="explainability">
                <div className="explainability__header">
                  <span className="explainability__label">WHY THIS RESULT</span>
                </div>
                <p className="explainability__reason">
                  {result.reason || result.error || 'No additional explanation returned by the service.'}
                </p>
                <p className="explainability__note">
                  Officer interpretation: Review the evidence above before making a final determination.
                  This system provides decision support — not an automatic authenticity verdict.
                </p>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
