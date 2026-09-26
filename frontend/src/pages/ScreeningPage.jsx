// [FRONTEND-SAFE] Document screening page — POST /api/v1/verify
// Redesigned from original DocumentScreeningPanel. API contract preserved.

import { useState } from 'react'
import UploadDropzone from '../components/UploadDropzone'
import RiskGauge from '../components/RiskGauge'
import StatusPill from '../components/StatusPill'
import VerificationPipeline from '../components/VerificationPipeline'
import IntegrityPanel from '../components/IntegrityPanel'
import { verifyDocument, ApiError } from '../services/api'

// Sequential pipeline animation states during processing
const PIPELINE_SEQUENCE = [
  'upload', 'ocr', 'mrz', 'database', 'tampering', 'biometric', 'risk'
]

export default function ScreeningPage() {
  const [file, setFile] = useState(null)
  const [documentNumber, setDocumentNumber] = useState('')
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [pipelineStates, setPipelineStates] = useState({})
  const [processingStep, setProcessingStep] = useState(-1)

  const runPipelineAnimation = async () => {
    const states = {}
    for (let i = 0; i < PIPELINE_SEQUENCE.length; i++) {
      const step = PIPELINE_SEQUENCE[i]
      // Mark current step as processing
      states[step] = 'processing'
      setPipelineStates({ ...states })
      await new Promise((r) => setTimeout(r, 380))
      // Mark complete (we'll override with real data after API returns)
      states[step] = 'complete'
      setPipelineStates({ ...states })
      setProcessingStep(i)
    }
  }

  const handleSubmit = async () => {
    if (!file) { setError('Choose a document image first.'); return }
    setBusy(true); setError(''); setResult(null); setPipelineStates({}); setProcessingStep(-1)

    // Start pipeline animation (visual loading sequence only)
    const animationPromise = runPipelineAnimation()

    try {
      const form = new FormData()
      form.append('document', file, file.name)
      if (documentNumber.trim()) form.append('document_number', documentNumber.trim())
      const data = await verifyDocument(form)
      await animationPromise
      setResult(data)
    } catch (e) {
      await animationPromise
      if (e instanceof ApiError && e.body) {
        setResult(e.body)
        setError(e.message)
      } else {
        setError(e.message || 'Screening failed. Please try again.')
        // Mark last pipeline step as failed
        setPipelineStates((prev) => {
          const last = PIPELINE_SEQUENCE[processingStep] || PIPELINE_SEQUENCE[0]
          return { ...prev, [last]: 'failed' }
        })
      }
    } finally {
      setBusy(false)
    }
  }

  const handleReset = () => {
    setFile(null); setDocumentNumber(''); setResult(null)
    setError(''); setPipelineStates({}); setProcessingStep(-1)
  }

  const riskLevel = result?.risk?.level
  const riskScore = result?.risk?.score

  return (
    <div className="page-content">
      {/* Page header */}
      <section className="page-header">
        <div>
          <p className="eyebrow">DOCUMENT INTELLIGENCE</p>
          <h2 className="page-header__title">New Verification</h2>
          <p className="page-header__sub">
            Submit an identity document for multi-layer verification: OCR, MRZ, database cross-check, tampering detection, and risk assessment.
          </p>
        </div>
        <StatusPill tone="neutral">◉ Synthetic/demo records only</StatusPill>
      </section>

      <div className="screening-grid">
        {/* Input panel */}
        <section className="panel screening-grid__input">
          <div className="panel__header">
            <div>
              <p className="eyebrow">DOCUMENT UPLOAD</p>
              <h3 className="panel__title">Document Details</h3>
            </div>
          </div>

          <div className="form-field">
            <label className="form-field__label" htmlFor="screening-doc-number">
              Document Number <span className="form-field__optional">(optional)</span>
            </label>
            <input
              id="screening-doc-number"
              className="form-field__input form-field__input--mono"
              type="text"
              value={documentNumber}
              onChange={(e) => setDocumentNumber(e.target.value)}
              placeholder="e.g. Q2714253"
              autoComplete="off"
              disabled={busy}
            />
            <p className="form-field__help">
              Use a number stored in the MongoDB Atlas reference store.
            </p>
          </div>

          <div className="form-field">
            <label className="form-field__label">Document Image</label>
            <UploadDropzone
              onFile={setFile}
              acceptedFile={file}
              label="Drop identity document here"
            />
          </div>

          {error && (
            <div className="inline-alert inline-alert--error" role="alert">
              <span aria-hidden="true">⚠</span>
              <div>
                <strong>Screening failed</strong>
                <span>{error}</span>
              </div>
            </div>
          )}

          <button
            className="btn btn--verify btn--full"
            onClick={handleSubmit}
            disabled={busy || !file}
          >
            {busy ? (
              <span className="btn__loading">
                <span className="btn__spinner" aria-hidden="true" />
                Screening…
              </span>
            ) : (
              'Run Document Screening →'
            )}
          </button>

          {(result || busy) && (
            <button className="btn--reset" onClick={handleReset}>Clear</button>
          )}
        </section>

        {/* Result panel */}
        <section className="panel screening-grid__result">
          {/* Processing pipeline */}
          {(busy || Object.keys(pipelineStates).length > 0) && (
            <div className="screening-pipeline">
              <div className="panel__header">
                <div>
                  <p className="eyebrow">ANALYSIS PIPELINE</p>
                  <h3 className="panel__title">
                    {busy ? 'Analyzing verification evidence…' : 'Screening complete'}
                  </h3>
                </div>
              </div>
              <VerificationPipeline stepStatuses={pipelineStates} compact />
            </div>
          )}

          {/* Empty state */}
          {!result && !busy && Object.keys(pipelineStates).length === 0 && (
            <div className="empty-result">
              <div className="empty-result__geo" aria-hidden="true">
                <svg viewBox="0 0 120 120" width="90" height="90" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="60" cy="60" r="55" stroke="currentColor" strokeWidth="0.8" opacity="0.2" />
                  <circle cx="60" cy="60" r="38" stroke="currentColor" strokeWidth="0.8" opacity="0.15" />
                  <circle cx="60" cy="60" r="20" stroke="currentColor" strokeWidth="0.8" opacity="0.12" />
                  <text x="60" y="65" textAnchor="middle" fontSize="22" fill="currentColor" opacity="0.3" fontFamily="system-ui">◫</text>
                </svg>
              </div>
              <h4 className="empty-result__title">Awaiting Document</h4>
              <p className="empty-result__sub">
                The screening report will include database state, OCR results, MRZ validation, tampering detection, risk reasons, and persistence status.
              </p>
            </div>
          )}

          {/* Result display */}
          {result && !busy && (
            <div className="result-content">
              {/* Decision banner */}
              <div className={`decision-banner decision-banner--${riskLevel === 'low' ? 'success' : riskLevel === 'high' ? 'danger' : 'warning'}`}>
                <div>
                  <span className="decision-banner__kicker">RISK ASSESSMENT</span>
                  <h4 className="decision-banner__verdict">
                    {riskLevel === 'low' ? 'Low Risk — Verified' :
                     riskLevel === 'medium' ? 'Medium Risk — Review Recommended' :
                     riskLevel === 'high' ? 'High Risk — Manual Review Required' :
                     'Risk Level Unknown'}
                  </h4>
                </div>
                <StatusPill tone={result.persistence?.stored ? 'success' : 'warning'}>
                  {result.persistence?.stored ? 'Saved' : 'Not Saved'}
                </StatusPill>
              </div>

              {/* Risk gauge + stats */}
              <div className="result-gauge-row">
                <RiskGauge score={riskScore} level={riskLevel} />
                <div className="result-stats">
                  <div className="result-stat">
                    <span className="result-stat__label">Reference Record</span>
                    <strong className={`result-stat__value ${result.database_checks?.found ? 'result-stat__value--success' : 'result-stat__value--danger'}`}>
                      {result.database_checks?.found ? 'FOUND' : 'NOT FOUND'}
                    </strong>
                  </div>
                  {result.persistence?.result_id && (
                    <div className="result-stat">
                      <span className="result-stat__label">Result ID</span>
                      <strong className="result-stat__value result-stat__value--mono">
                        {String(result.persistence.result_id).slice(0, 16)}…
                      </strong>
                    </div>
                  )}
                </div>
              </div>

              {/* Explainability */}
              <div className="explainability">
                <div className="explainability__header">
                  <span className="explainability__label">WHY THIS RESULT</span>
                </div>
                {result.risk?.reasons?.length ? (
                  <ul className="explainability__reasons">
                    {result.risk.reasons.map((r, i) => (
                      <li key={i} className="explainability__reason-item">
                        <span aria-hidden="true">·</span> {r}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="explainability__reason">
                    {result.warnings?.join(' ') || 'No additional explanation returned by the service.'}
                  </p>
                )}
                <p className="explainability__note">
                  Officer interpretation: Review all evidence before making a final determination.
                  This system provides decision support — not an automatic authenticity verdict.
                </p>
              </div>

              {/* Blockchain integrity — driven only by the server-owned verification_id */}
              {result.verification_id && (
                <IntegrityPanel verificationId={result.verification_id} />
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
