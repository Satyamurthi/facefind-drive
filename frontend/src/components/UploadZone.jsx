import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'

const ACCEPTED = { 'image/*': ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'] }

export default function UploadZone({ onFile, disabled }) {
  const [preview, setPreview] = useState(null)
  const [filename, setFilename] = useState(null)

  const onDrop = useCallback((accepted) => {
    const file = accepted[0]
    if (!file) return
    setFilename(file.name)
    const url = URL.createObjectURL(file)
    setPreview(url)
    onFile(file)
  }, [onFile])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    multiple: false,
    disabled,
  })

  const clear = (e) => {
    e.stopPropagation()
    setPreview(null)
    setFilename(null)
    onFile(null)
  }

  if (preview) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-md)' }}>
        <div className="upload-preview animate-fade-in">
          <img src={preview} alt="Reference photo preview" />
          <button className="upload-preview-clear" onClick={clear} title="Clear" aria-label="Clear reference image">✕</button>
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
          📁 {filename}
        </div>
      </div>
    )
  }

  return (
    <div
      {...getRootProps()}
      className={`upload-zone ${isDragActive ? 'drag-over' : ''}`}
      id="upload-zone"
      role="button"
      aria-label="Upload reference photo"
    >
      <input {...getInputProps()} id="file-input" />
      <div className="upload-zone-content">
        <span className="upload-icon">🤳</span>
        <div className="upload-zone-title">
          {isDragActive ? 'Drop your photo here…' : 'Upload a reference photo'}
        </div>
        <div className="upload-zone-sub" style={{ marginTop: 8 }}>
          Drag & drop or <span style={{ color: 'var(--color-primary-light)', fontWeight: 600 }}>click to browse</span>
          <br />JPG, PNG, WEBP up to 10 MB
        </div>
      </div>
    </div>
  )
}
