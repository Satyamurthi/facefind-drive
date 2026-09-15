import { api } from '../api'

function ConfidenceBar({ score }) {
  const pct = Math.round(score * 100)
  const cls = score >= 0.85 ? 'confidence-high' : score >= 0.72 ? 'confidence-med' : 'confidence-low'
  const color = score >= 0.85 ? 'var(--color-success)' : score >= 0.72 ? 'var(--color-warning)' : 'var(--color-error)'
  return (
    <div className="match-card-footer">
      <div className="confidence-bar">
        <div className={`confidence-fill ${cls}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="confidence-label" style={{ color }}>{pct}%</span>
    </div>
  )
}

export default function MatchCard({ match, selected, onSelect }) {
  const { file_id, filename, confidence } = match
  const thumbUrl = api.thumbnailUrl(file_id)
  const downloadUrl = api.downloadFile(file_id)

  return (
    <div
      className={`match-card animate-fade-in-up ${selected ? 'selected' : ''}`}
      onClick={() => onSelect(file_id)}
      role="checkbox"
      aria-checked={selected}
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && onSelect(file_id)}
    >
      {/* Selection checkbox */}
      <div className="match-card-checkbox">
        {selected && <span style={{ color: 'white', fontSize: 13 }}>✓</span>}
      </div>

      {/* Thumbnail */}
      <img
        src={thumbUrl}
        alt={filename}
        className="match-card-img"
        onError={e => {
          e.currentTarget.style.display = 'none'
          e.currentTarget.nextSibling.style.display = 'flex'
        }}
      />
      <div className="match-card-img-placeholder" style={{ display: 'none' }}>🖼️</div>

      <div className="match-card-body">
        <div className="match-card-name" title={filename}>{filename}</div>
        <ConfidenceBar score={confidence} />

        {/* Download button */}
        <a
          href={downloadUrl}
          download={filename}
          className="btn btn-ghost btn-sm"
          style={{ width: '100%', marginTop: 10, justifyContent: 'center' }}
          onClick={e => e.stopPropagation()}
          id={`btn-download-${file_id}`}
        >
          ⬇ Download
        </a>
      </div>
    </div>
  )
}
