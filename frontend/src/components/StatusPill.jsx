// [FRONTEND-SAFE] Status pill indicator — refined version of original component

export default function StatusPill({ tone = 'neutral', children, size = 'md' }) {
  return (
    <span className={`status-pill status-pill--${tone} status-pill--${size}`} role="status">
      <span className="status-pill__dot" aria-hidden="true" />
      <span className="status-pill__text">{children}</span>
    </span>
  )
}
