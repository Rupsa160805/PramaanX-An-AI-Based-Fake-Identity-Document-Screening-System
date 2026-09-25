// P4 — Blockchain Integrity Panel
// Communicates ONLY with Flask backend — no Web3, no MetaMask, no wallets.
// Displays tamper-evident record verification, NOT AI correctness.

import { useCallback, useEffect, useState } from 'react'

const STATUS_DISPLAY = {
    MATCH: { icon: '✓', label: 'VERIFIED', cls: 'integrity-match' },
    VERIFIED: { icon: '✓', label: 'VERIFIED', cls: 'integrity-match' },
    MISMATCH: { icon: '⚠', label: 'MISMATCH', cls: 'integrity-mismatch' },
    NOT_FOUND: { icon: '—', label: 'NOT FOUND', cls: 'integrity-notfound' },
    UNAVAILABLE: { icon: '—', label: 'UNAVAILABLE', cls: 'integrity-unavailable' },
}

const CHAIN_DISPLAY = {
    INTACT: { label: 'INTACT', cls: 'chain-intact' },
    WARNING: { label: 'WARNING', cls: 'chain-warning' },
    INCOMPLETE: { label: 'INCOMPLETE', cls: 'chain-incomplete' },
    UNAVAILABLE: { label: 'UNAVAILABLE', cls: 'chain-unavailable' },
}

function StatusRow({ type, status }) {
    const display = STATUS_DISPLAY[status] || STATUS_DISPLAY.UNAVAILABLE
    return (
        <div className={`integrity-row ${display.cls}`} id={`integrity-row-${type.toLowerCase()}`}>
            <span className="integrity-row__type">{type}</span>
            <span className="integrity-row__status">
                <span className="integrity-row__icon" aria-hidden="true">{display.icon}</span>
                {display.label}
            </span>
        </div>
    )
}

function ChainBadge({ chainStatus }) {
    const display = CHAIN_DISPLAY[chainStatus] || CHAIN_DISPLAY.UNAVAILABLE
    return (
        <div className={`chain-badge ${display.cls}`} id="chain-status-badge">
            <span className="chain-badge__label">Chain Status:</span>
            <span className="chain-badge__value">{display.label}</span>
        </div>
    )
}

export default function IntegrityPanel({ verificationId, screeningResult, h2 }) {
    const [integrityData, setIntegrityData] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [demoResult, setDemoResult] = useState(null)

    const checkIntegrity = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
            const resp = await fetch(`${apiBase}/api/v1/integrity/verify-all`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    verification_id: verificationId || 'PX-DEMO-001',
                    result: screeningResult || null,
                    h2: h2 || '',
                }),
            })
            if (!resp.ok) throw new Error(`Integrity check failed (${resp.status})`)
            const data = await resp.json()
            setIntegrityData(data)
        } catch (err) {
            setError(err.message)
            setIntegrityData(null)
        } finally {
            setLoading(false)
        }
    }, [verificationId, screeningResult, h2])

    const anchorFinal = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
            const resp = await fetch(`${apiBase}/api/v1/integrity/final`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    verification_id: verificationId || 'PX-DEMO-001',
                    result: screeningResult || null,
                    h2: h2 || '',
                }),
            })
            if (!resp.ok) throw new Error(`Anchor failed (${resp.status})`)
            // After anchoring, re-check integrity
            await checkIntegrity()
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [verificationId, screeningResult, h2, checkIntegrity])

    const runDemoMismatch = useCallback(async () => {
        setLoading(true)
        setError(null)
        setDemoResult(null)
        try {
            const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
            const resp = await fetch(`${apiBase}/api/v1/integrity/demo-mismatch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
            })
            if (!resp.ok) throw new Error(`Demo failed (${resp.status})`)
            const data = await resp.json()
            setDemoResult(data)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }, [])

    // Auto-check on mount
    useEffect(() => {
        checkIntegrity()
    }, [checkIntegrity])

    const records = integrityData?.records || {}
    const chainStatus = integrityData?.chain_status || 'UNAVAILABLE'

    return (
        <section className="integrity-panel" id="integrity-panel" aria-label="Blockchain Integrity">
            <div className="integrity-panel__header">
                <div className="integrity-panel__title-group">
                    <h2 className="integrity-panel__title">
                        <span className="integrity-panel__shield" aria-hidden="true">⛓</span>
                        Blockchain Integrity
                    </h2>
                    <p className="integrity-panel__subtitle">Tamper-Evident Record Verification</p>
                </div>
                <div className="integrity-panel__actions">
                    <button
                        className="integrity-btn integrity-btn--anchor"
                        onClick={anchorFinal}
                        disabled={loading}
                        id="btn-anchor-final"
                        title="Compute H3 and anchor the FINAL record on-chain"
                    >
                        {loading ? '…' : '⚓'} Anchor FINAL
                    </button>
                    <button
                        className="integrity-btn integrity-btn--verify"
                        onClick={checkIntegrity}
                        disabled={loading}
                        id="btn-verify-integrity"
                        title="Verify all checkpoint hashes against blockchain"
                    >
                        {loading ? '…' : '⟳'} Verify
                    </button>
                </div>
            </div>

            {error && (
                <div className="integrity-error" role="alert" id="integrity-error">
                    {error}
                </div>
            )}

            <div className="integrity-panel__body">
                <div className="integrity-records" id="integrity-records">
                    <StatusRow type="INPUT" status={records.INPUT?.status || 'UNAVAILABLE'} />
                    <StatusRow type="ANALYSIS" status={records.ANALYSIS?.status || 'UNAVAILABLE'} />
                    <StatusRow type="FINAL" status={records.FINAL?.status || 'UNAVAILABLE'} />
                </div>
                <ChainBadge chainStatus={chainStatus} />
            </div>

            <p className="integrity-panel__disclaimer">
                Record integrity confirms that data has not changed since it was anchored on the blockchain.
                It does <strong>not</strong> confirm AI correctness or document authenticity.
            </p>

            {/* Controlled mismatch demo */}
            <details className="integrity-demo" id="integrity-demo">
                <summary className="integrity-demo__toggle">🔬 Controlled Mismatch Demo</summary>
                <div className="integrity-demo__body">
                    <p>
                        Anchors a synthetic FINAL record, then modifies <code>risk_level</code> to
                        demonstrate how a post-anchoring change is detected as a MISMATCH.
                        Uses synthetic data only — never real identity documents.
                    </p>
                    <button
                        className="integrity-btn integrity-btn--demo"
                        onClick={runDemoMismatch}
                        disabled={loading}
                        id="btn-demo-mismatch"
                    >
                        Run Demo
                    </button>
                    {demoResult && (
                        <div className="integrity-demo__result" id="demo-mismatch-result">
                            <div className="integrity-demo__step">
                                <strong>1. Anchored</strong> with risk_level = &quot;{demoResult.step_2_modification?.original}&quot;
                            </div>
                            <div className="integrity-demo__step">
                                <strong>2. Modified</strong> risk_level → &quot;{demoResult.step_2_modification?.modified}&quot;
                            </div>
                            <div className={`integrity-demo__step integrity-demo__step--${demoResult.step_3_verification?.status === 'MISMATCH' ? 'mismatch' : 'match'
                                }`}>
                                <strong>3. Result:</strong> {demoResult.step_3_verification?.status}
                            </div>
                            <p className="integrity-demo__explanation">{demoResult.explanation}</p>
                        </div>
                    )}
                </div>
            </details>
        </section>
    )
}
