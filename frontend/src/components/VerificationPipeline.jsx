// [FRONTEND-SAFE] Verification pipeline — visual step progress
// Steps animate sequentially. State driven by actual frontend processing state.

const STEPS = [
  { id: 'upload', label: 'Document Received', icon: '◫' },
  { id: 'ocr', label: 'OCR Extraction', icon: '⊡' },
  { id: 'mrz', label: 'MRZ Validation', icon: '≣' },
  { id: 'database', label: 'Database Cross-check', icon: '◎' },
  { id: 'tampering', label: 'Tampering Detection', icon: '⊛' },
  { id: 'biometric', label: 'Biometric Verification', icon: '◉' },
  { id: 'risk', label: 'Risk Assessment', icon: '◬' },
]

// status: 'pending' | 'processing' | 'complete' | 'failed' | 'skipped'
export default function VerificationPipeline({ stepStatuses = {}, compact = false }) {
  return (
    <div className={`pipeline ${compact ? 'pipeline--compact' : ''}`} role="list" aria-label="Verification pipeline progress">
      {STEPS.map((step, idx) => {
        const status = stepStatuses[step.id] || 'pending'
        return (
          <div key={step.id} className="pipeline__item" role="listitem">
            <div className={`pipeline__node pipeline__node--${status}`}>
              <span className="pipeline__node-icon" aria-hidden="true">
                {status === 'complete' ? '✓' : status === 'failed' ? '✕' : status === 'processing' ? '◌' : step.icon}
              </span>
            </div>
            <div className="pipeline__label">
              <span className="pipeline__step-name">{step.label}</span>
              <span className={`pipeline__step-status pipeline__step-status--${status}`}>
                {STATUS_LABELS[status]}
              </span>
            </div>
            {idx < STEPS.length - 1 && (
              <div className={`pipeline__connector pipeline__connector--${status === 'complete' ? 'active' : 'idle'}`} aria-hidden="true" />
            )}
          </div>
        )
      })}
    </div>
  )
}

const STATUS_LABELS = {
  pending: 'Pending',
  processing: 'Processing…',
  complete: 'Complete',
  failed: 'Failed',
  skipped: 'Skipped',
}
