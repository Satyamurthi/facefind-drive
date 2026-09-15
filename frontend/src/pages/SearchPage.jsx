import { useState, useEffect, useRef } from 'react'
import { toast } from 'react-hot-toast'
import { api } from '../api'
import UploadZone from '../components/UploadZone'
import ResultsGallery from '../components/ResultsGallery'
import ConsentBanner from '../components/ConsentBanner'

const STAGES = ['Detecting face…', 'Loading index…', 'Comparing embeddings…', 'Finalizing…']

export default function SearchPage() {
  const [file, setFile] = useState(null)
  const [searching, setSearching] = useState(false)
  const [status, setStatus] = useState('')
  const [progress, setProgress] = useState(0)
  const [results, setResults] = useState(null)
  const [indexedTotal, setIndexedTotal] = useState(0)
  const [threshold, setThreshold] = useState(0.68)
  const [purpose, setPurpose] = useState('')
  const abortRef = useRef(null)

  useEffect(() => {
    api.purpose().then(d => setPurpose(d.stated_purpose)).catch(() => {})
  }, [])

  const handleSearch = async () => {
    if (!file) { toast.error('Please upload a reference photo first'); return }
    setSearching(true)
    setResults(null)
    setStatus('Starting search…')
    setProgress(10)
    let stageIdx = 0

    try {
      const res = await api.searchStream(file)
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Search failed')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      const progressInterval = setInterval(() => {
        setProgress(p => Math.min(p + 8, 88))
        stageIdx = (stageIdx + 1) % STAGES.length
      }, 1200)

      abortRef.current = () => {
        reader.cancel()
        clearInterval(progressInterval)
      }

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop()
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = JSON.parse(line.slice(6))
          if (payload.type === 'progress') {
            setStatus(payload.message)
          } else if (payload.type === 'result') {
            setResults(payload.matches)
            setIndexedTotal(payload.indexed_total)
            setThreshold(payload.threshold)
            setProgress(100)
            setStatus(`Found ${payload.total} match${payload.total !== 1 ? 'es' : ''}`)
          } else if (payload.type === 'error') {
            throw new Error(payload.message)
          }
        }
      }
      clearInterval(progressInterval)
    } catch (err) {
      toast.error(err.message)
      setStatus('')
      setProgress(0)
    } finally {
      setSearching(false)
      abortRef.current = null
    }
  }

  const reset = () => {
    if (abortRef.current) abortRef.current()
    setFile(null)
    setResults(null)
    setStatus('')
    setProgress(0)
    setSearching(false)
  }

  return (
    <div className="container" style={{ paddingTop: 'var(--space-xl)', paddingBottom: 'var(--space-2xl)' }}>
      {/* Header */}
      <div style={{ marginBottom: 'var(--space-xl)', textAlign: 'center' }}>
        <h1 style={{ marginBottom: 12 }}>
          Find Your <span className="gradient-text">Photos</span>
        </h1>
        <p style={{ maxWidth: 520, margin: '0 auto', fontSize: '1rem' }}>
          Upload a reference photo and we'll search the Drive folder for all matching images.
        </p>
      </div>

      {/* Consent Banner */}
      {purpose && <ConsentBanner purpose={purpose} />}

      {/* Upload + Search */}
      <div className="card" style={{ padding: 'var(--space-xl)', marginBottom: 'var(--space-xl)' }}>
        <UploadZone onFile={setFile} disabled={searching} />

        {/* Progress */}
        {searching && (
          <div style={{ marginTop: 'var(--space-lg)' }} className="animate-fade-in">
            <div className="scan-status">
              <div className="spinner" />
              <span>{status}</span>
            </div>
            <div style={{ marginTop: 12 }}>
              <div className="progress-wrap">
                <div className="progress-bar" style={{ width: `${progress}%` }} />
              </div>
            </div>
          </div>
        )}

        {/* CTA */}
        <div style={{ display: 'flex', gap: 12, marginTop: 'var(--space-lg)', justifyContent: 'center', flexWrap: 'wrap' }}>
          <button
            className="btn btn-primary btn-lg"
            onClick={handleSearch}
            disabled={!file || searching}
            id="btn-search"
          >
            {searching
              ? <><span className="spinner" /> Searching…</>
              : '🔍 Search Drive'}
          </button>
          {(results !== null || searching) && (
            <button className="btn btn-ghost" onClick={reset} id="btn-reset">
              ✕ New Search
            </button>
          )}
        </div>
      </div>

      {/* Results */}
      {results !== null && !searching && (
        <div className="animate-fade-in">
          <ResultsGallery
            matches={results}
            indexedTotal={indexedTotal}
            threshold={threshold}
          />
        </div>
      )}
    </div>
  )
}
