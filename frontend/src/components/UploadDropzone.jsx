// [FRONTEND-SAFE] Premium upload dropzone with Indian geometric empty state
import { useRef, useState } from 'react'

export default function UploadDropzone({ onFile, acceptedFile, label = 'Drop identity document here' }) {
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef(null)

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) onFile(file)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleChange = (e) => {
    const file = e.target.files?.[0]
    if (file) onFile(file)
  }

  return (
    <div
      className={`dropzone ${dragOver ? 'dropzone--over' : ''} ${acceptedFile ? 'dropzone--accepted' : ''}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={() => setDragOver(false)}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      aria-label={acceptedFile ? `Selected: ${acceptedFile.name}` : label}
      onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={handleChange}
        className="dropzone__input"
        aria-hidden="true"
        tabIndex={-1}
      />

      {acceptedFile ? (
        <div className="dropzone__accepted">
          <span className="dropzone__accepted-icon" aria-hidden="true">✓</span>
          <div className="dropzone__accepted-info">
            <strong className="dropzone__accepted-name">{acceptedFile.name}</strong>
            <span className="dropzone__accepted-size">
              {(acceptedFile.size / 1024 / 1024).toFixed(2)} MB · Click to change
            </span>
          </div>
        </div>
      ) : (
        <div className="dropzone__empty">
          {/* Geometric decoration */}
          <div className="dropzone__geo" aria-hidden="true">
            <svg viewBox="0 0 80 80" width="80" height="80" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="40" cy="40" r="36" stroke="currentColor" strokeWidth="0.8" opacity="0.3" />
              <circle cx="40" cy="40" r="24" stroke="currentColor" strokeWidth="0.8" opacity="0.25" />
              <circle cx="40" cy="40" r="12" stroke="currentColor" strokeWidth="0.8" opacity="0.2" />
              {Array.from({ length: 8 }, (_, i) => {
                const a = (i * 45 * Math.PI) / 180
                return (
                  <line
                    key={i}
                    x1={40 + 14 * Math.cos(a)} y1={40 + 14 * Math.sin(a)}
                    x2={40 + 35 * Math.cos(a)} y2={40 + 35 * Math.sin(a)}
                    stroke="currentColor" strokeWidth="0.6" opacity="0.2"
                  />
                )
              })}
              <text x="40" y="44" textAnchor="middle" fontSize="14" fill="currentColor" opacity="0.6" fontFamily="system-ui">◫</text>
            </svg>
          </div>
          <strong className="dropzone__title">{label}</strong>
          <span className="dropzone__formats">JPG · PNG · WEBP</span>
          <span className="dropzone__cta">Click or drag to upload</span>
        </div>
      )}
    </div>
  )
}
