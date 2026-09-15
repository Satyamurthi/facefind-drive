import { useState } from 'react'
import { toast } from 'react-hot-toast'
import MatchCard from './MatchCard'
import { api } from '../api'

export default function ResultsGallery({ matches, indexedTotal, threshold }) {
  const [selected, setSelected] = useState(new Set())
  const [downloading, setDownloading] = useState(false)

  const toggleSelect = (fileId) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(fileId) ? next.delete(fileId) : next.add(fileId)
      return next
    })
  }

  const toggleAll = () => {
    if (selected.size === matches.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(matches.map(m => m.file_id)))
    }
  }

  const downloadZip = async () => {
    const ids = selected.size > 0 ? [...selected] : matches.map(m => m.file_id)
    if (!ids.length) return
    setDownloading(true)
    try {
      const res = await api.downloadZip(ids)
      // res is a Response object (raw fetch result)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'facefind_matches.zip'
      a.click()
      URL.revokeObjectURL(url)
      toast.success(`Downloaded ${ids.length} file(s)`)
    } catch (err) {
      toast.error('ZIP download failed: ' + err.message)
    } finally {
      setDownloading(false)
    }
  }

  if (!matches || matches.length === 0) {
    return (
      <div className="empty-state animate-fade-in">
        <div className="empty-state-icon">🔍</div>
        <div className="empty-state-title">No matches found</div>
        <p style={{ maxWidth: 340, margin: '0 auto' }}>
          No photos of this person were found above the {Math.round(threshold * 100)}% confidence threshold
          in {indexedTotal} indexed images. Try a clearer photo or ask an admin to lower the threshold.
        </p>
      </div>
    )
  }

  const allSelected = selected.size === matches.length
  const someSelected = selected.size > 0

  return (
    <div className="animate-fade-in">
      <div className="results-header">
        <div>
          <div className="results-count">
            Found <strong>{matches.length}</strong> match{matches.length !== 1 ? 'es' : ''} in{' '}
            <strong>{indexedTotal}</strong> indexed photos
            {someSelected && <> &nbsp;·&nbsp; <strong>{selected.size}</strong> selected</>}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
          <button
            className="btn btn-ghost btn-sm"
            onClick={toggleAll}
            id="btn-select-all"
          >
            {allSelected ? '☐ Deselect All' : '☑ Select All'}
          </button>
          <button
            className="btn btn-accent"
            onClick={downloadZip}
            disabled={downloading}
            id="btn-download-zip"
          >
            {downloading ? <><span className="spinner" /> Preparing…</> : `⬇ Download ${someSelected ? selected.size : 'All'} as ZIP`}
          </button>
        </div>
      </div>

      <div className="gallery-grid">
        {matches.map((match, i) => (
          <div key={match.file_id} style={{ animationDelay: `${i * 40}ms` }}>
            <MatchCard
              match={match}
              selected={selected.has(match.file_id)}
              onSelect={toggleSelect}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
