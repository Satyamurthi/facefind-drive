export default function ConsentBanner({ purpose }) {
  return (
    <div className="consent-banner" role="note" aria-label="Purpose notice">
      <div className="consent-icon">⚖️</div>
      <div className="consent-text">
        <div className="consent-title">Stated Purpose</div>
        <strong style={{ color: 'var(--color-text-primary)' }}>{purpose}</strong>
        <br />
        This tool uses facial recognition to locate photos. Access is restricted to authorized users.
        All searches are logged for auditability. Do not use this for any purpose beyond the stated one.
      </div>
    </div>
  )
}
