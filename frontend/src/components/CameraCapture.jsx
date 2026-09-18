// [FRONTEND-SAFE] Premium camera capture UI — uses forwardRef to expose snapshot/stopCamera
// Uses the SAME camera/snapshot logic as original. No functional changes to API integration.

import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react'

const CameraCapture = forwardRef(function CameraCapture(
  {
    onPhotoReady,       // (blob) => void
    onUploadFile,       // (file) => void
    onServiceCapture,   // () => void
    livePreview,
    livePhotoPath,
    livenessResult,
    busy,
    onRunLiveness,
  },
  ref
) {
  const [cameraOpen, setCameraOpen] = useState(false)
  const [cameraStatus, setCameraStatus] = useState('idle') // idle | detecting | ready | capturing
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop())
    }
  }, [])

  useEffect(() => {
    if (videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current
    }
  }, [cameraOpen])

  const getCamera = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error('Camera access is not available in this browser.')
    }
    if (streamRef.current) return streamRef.current
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
    })
    streamRef.current = stream
    setCameraOpen(true)
    return stream
  }, [])

  const prepareVideo = useCallback(async (stream) => {
    for (let i = 0; i < 30; i++) {
      const v = videoRef.current
      if (v) {
        v.srcObject = stream
        try { await v.play() } catch { /* deferred */ }
        if (v.videoWidth) return
      }
      await new Promise((r) => setTimeout(r, 50))
    }
    throw new Error('Camera preview is not ready. Please try again.')
  }, [])

  const snapshot = useCallback(async () => {
    const v = videoRef.current, c = canvasRef.current
    if (!v || !c || !v.videoWidth) throw new Error('Camera preview not ready.')
    c.width = v.videoWidth; c.height = v.videoHeight
    c.getContext('2d').drawImage(v, 0, 0, c.width, c.height)
    return new Promise((res, rej) =>
      c.toBlob((b) => b ? res(b) : rej(new Error('Frame capture failed.')), 'image/jpeg', 0.92)
    )
  }, [])

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    setCameraOpen(false)
    setCameraStatus('idle')
  }, [])

  // Expose snapshot and stopCamera to parent via ref
  useImperativeHandle(ref, () => ({ snapshot, stopCamera }), [snapshot, stopCamera])

  const handleStartCamera = async () => {
    try {
      setCameraStatus('detecting')
      const stream = await getCamera()
      await prepareVideo(stream)
      setCameraStatus('ready')
    } catch (e) {
      setCameraStatus('idle')
      alert(e.message)
    }
  }

  const handleCapture = async () => {
    if (!cameraOpen) {
      // Start camera then capture
      setCameraStatus('detecting')
      try {
        const stream = await getCamera()
        await prepareVideo(stream)
        setCameraStatus('capturing')
        const blob = await snapshot()
        onPhotoReady(blob)
        setCameraStatus('ready')
      } catch (e) {
        setCameraStatus('idle')
        alert(e.message)
      }
      return
    }
    setCameraStatus('capturing')
    try {
      const blob = await snapshot()
      onPhotoReady(blob)
      setCameraStatus('ready')
    } catch (e) {
      setCameraStatus('ready')
      alert(e.message)
    }
  }

  const handleFile = (e) => {
    const file = e.target.files?.[0]
    if (file) onUploadFile(file)
  }

  const livenessColor = livenessResult
    ? livenessResult.is_live ? 'success' : 'danger'
    : 'neutral'

  return (
    <div className="camera-capture">
      {/* Camera viewport */}
      <div className="camera-capture__viewport">
        {/* Corner brackets */}
        <span className="camera-capture__corner camera-capture__corner--tl" aria-hidden="true" />
        <span className="camera-capture__corner camera-capture__corner--tr" aria-hidden="true" />
        <span className="camera-capture__corner camera-capture__corner--bl" aria-hidden="true" />
        <span className="camera-capture__corner camera-capture__corner--br" aria-hidden="true" />

        {cameraOpen ? (
          <>
            <video ref={videoRef} className="camera-capture__video" muted playsInline aria-label="Camera preview" />
            <div className="camera-capture__scanline" aria-hidden="true" />
            <div className="camera-capture__live-badge" aria-live="polite">
              <span className="camera-capture__live-dot" aria-hidden="true" />
              LIVE
            </div>
          </>
        ) : livePreview ? (
          <img className="camera-capture__preview" src={livePreview} alt="Captured live face" />
        ) : (
          <div className="camera-capture__empty">
            <div className="camera-capture__face-guide" aria-hidden="true">
              <span className="camera-capture__face-icon">◉</span>
            </div>
            <p className="camera-capture__empty-text">
              {cameraStatus === 'detecting' ? 'Initializing camera…' : 'Position face within the frame'}
            </p>
          </div>
        )}

        {livePhotoPath && !cameraOpen && (
          <div className="camera-capture__ready-badge" aria-live="polite">
            <span aria-hidden="true">✓</span> Photo Ready
          </div>
        )}
      </div>

      <canvas ref={canvasRef} className="camera-capture__canvas" aria-hidden="true" />

      {/* Controls */}
      <div className="camera-capture__controls">
        <div className="camera-capture__control-row">
          {!cameraOpen ? (
            <button className="btn btn--secondary" onClick={handleStartCamera} disabled={busy !== ''}>
              <span aria-hidden="true">◉</span> Open Camera
            </button>
          ) : (
            <button className="btn btn--secondary" onClick={stopCamera}>
              <span aria-hidden="true">✕</span> Close Camera
            </button>
          )}
          <button
            className="btn btn--primary"
            onClick={handleCapture}
            disabled={busy !== ''}
          >
            {busy === 'photo' ? 'Saving…' : 'Capture Photo'}
          </button>
        </div>

        <div className="camera-capture__control-row">
          <label className="btn btn--ghost camera-capture__file-btn">
            <span aria-hidden="true">⬆</span> Upload Photo
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleFile}
              className="camera-capture__file-input"
              aria-label="Upload a photo file"
            />
          </label>
          <button
            className="btn btn--ghost"
            onClick={onServiceCapture}
            disabled={busy !== ''}
            title="Capture using the server-side webcam"
          >
            Service Camera
          </button>
        </div>
      </div>

      {/* Liveness section */}
      <div className="camera-capture__liveness">
        <div className="camera-capture__liveness-header">
          <span className="camera-capture__liveness-label">Liveness Check</span>
          <span className={`liveness-badge liveness-badge--${livenessColor}`}>
            {livenessResult
              ? livenessResult.is_live ? '✓ Passed' : '✕ Failed'
              : '○ Not Run'}
          </span>
        </div>
        <p className="camera-capture__liveness-help">
          Captures 3 frames to detect motion. MVP heuristic — not production anti-spoofing.
        </p>
        <button
          className="btn btn--outline btn--full"
          onClick={onRunLiveness}
          disabled={busy !== ''}
        >
          {busy === 'liveness' ? 'Capturing frames…' : 'Run Liveness Check'}
        </button>
        {livenessResult && (
          <p className="camera-capture__liveness-reason">
            {livenessResult.reason}
            {typeof livenessResult.motion_score === 'number' &&
              ` · Motion score: ${livenessResult.motion_score.toFixed(3)}`}
          </p>
        )}
      </div>
    </div>
  )
})

export default CameraCapture
