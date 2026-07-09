/**
 * pages/Upload.jsx — Document Upload & Management Interface
 * ==========================================================
 * Upload PDF documents to POST /api/documents/upload.
 * Lists all ingested documents via GET /api/documents/.
 * Allows complete deletion (PostgreSQL + Qdrant) via DELETE /api/documents/{id}.
 */

import React, { useState, useEffect } from 'react'

export default function Upload() {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)
  const [file, setFile] = useState(null)
  const [sourceUrl, setSourceUrl] = useState('')
  const [uploading, setUploading] = useState(false)
  const [statusMsg, setStatusMsg] = useState(null)

  async function fetchDocuments() {
    try {
      const res = await fetch('/api/documents/')
      if (res.ok) {
        const data = await res.json()
        setDocuments(data)
      }
    } catch (err) {
      console.error('Error fetching documents:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDocuments()
  }, [])

  async function handleUpload(e) {
    e.preventDefault()
    if (!file) return

    setUploading(true)
    setStatusMsg({ type: 'info', text: 'Ingesting PDF: extracting metadata, chunking text, and generating embeddings...' })

    const formData = new FormData()
    formData.append('file', file)
    formData.append('source_url', sourceUrl)

    try {
      const res = await fetch('/api/documents/upload', {
        method: 'POST',
        body: formData
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Upload failed.')
      }

      setStatusMsg({
        type: 'success',
        text: `Success! Ingested '${data.title}' (${data.chunks} semantic chunks stored in Qdrant & PostgreSQL).`
      })
      setFile(null)
      setSourceUrl('')
      fetchDocuments()
    } catch (err) {
      setStatusMsg({
        type: 'error',
        text: err.message
      })
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(id, title) {
    if (!window.confirm(`Are you sure you want to delete '${title}'? This will remove its chunks from PostgreSQL and vector embeddings from Qdrant.`)) {
      return
    }

    try {
      const res = await fetch(`/api/documents/${id}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        setStatusMsg({ type: 'success', text: `Deleted '${title}' completely.` })
        fetchDocuments()
      } else {
        const data = await res.json()
        alert(data.detail || 'Delete failed')
      }
    } catch (err) {
      alert('Error deleting document: ' + err.message)
    }
  }

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '0.4rem' }}>
          Document Repository & Ingestion Engine
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Upload administrative PDFs (orders, circulars, notifications) to populate the Agentic AI Knowledge Base.
        </p>
      </div>

      {/* Upload Form Card */}
      <div className="glass-card" style={{ padding: '1.75rem', marginBottom: '2.5rem' }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '1.25rem' }}>Ingest New Administrative PDF</h2>

        <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
            {/* File Input */}
            <div>
              <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 500, marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                PDF Document File *
              </label>
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                disabled={uploading}
                className="input-field"
                style={{ padding: '0.65rem' }}
                required
              />
            </div>

            {/* Source URL Input */}
            <div>
              <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 500, marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                Source Website URL (Optional)
              </label>
              <input
                type="url"
                placeholder="https://nitc.ac.in/..."
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                disabled={uploading}
                className="input-field"
              />
            </div>
          </div>

          {/* Status Message Alert */}
          {statusMsg && (
            <div style={{
              padding: '0.9rem 1.2rem',
              borderRadius: 'var(--radius-md)',
              background: statusMsg.type === 'success'
                ? 'rgba(16, 185, 129, 0.15)'
                : statusMsg.type === 'error'
                ? 'rgba(248, 113, 113, 0.15)'
                : 'rgba(6, 182, 212, 0.15)',
              border: `1px solid ${statusMsg.type === 'success' ? 'var(--accent-emerald)' : statusMsg.type === 'error' ? '#f87171' : 'var(--accent-cyan)'}`,
              color: statusMsg.type === 'success' ? 'var(--accent-emerald-light)' : statusMsg.type === 'error' ? '#fca5a5' : 'var(--accent-cyan-light)',
              fontSize: '0.95rem'
            }}>
              {statusMsg.text}
            </div>
          )}

          <div>
            <button type="submit" className="btn btn-primary" disabled={uploading || !file}>
              {uploading ? '⚙️ Ingesting & Embedding PDF...' : '⚡ Upload & Ingest Document'}
            </button>
          </div>
        </form>
      </div>

      {/* Indexed Documents Table Card */}
      <div className="glass-card" style={{ padding: '1.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: '1.3rem' }}>Indexed Knowledge Base ({documents.length})</h2>
          <button onClick={fetchDocuments} className="btn btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}>
            🔄 Refresh List
          </button>
        </div>

        {loading ? (
          <p style={{ color: 'var(--text-muted)' }}>Loading indexed documents...</p>
        ) : documents.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', padding: '1.5rem 0' }}>No administrative documents found. Upload a PDF above.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  <th style={{ padding: '0.8rem 0' }}>TITLE</th>
                  <th style={{ padding: '0.8rem 1rem' }}>DEPARTMENT</th>
                  <th style={{ padding: '0.8rem 1rem' }}>CATEGORY</th>
                  <th style={{ padding: '0.8rem 1rem' }}>DOC NUMBER</th>
                  <th style={{ padding: '0.8rem 1rem' }}>CHUNKS</th>
                  <th style={{ padding: '0.8rem 0', textAlign: 'right' }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.92rem' }}>
                    <td style={{ padding: '0.9rem 0', fontWeight: 500 }}>{doc.title}</td>
                    <td style={{ padding: '0.9rem 1rem', color: 'var(--text-secondary)' }}>{doc.department || '—'}</td>
                    <td style={{ padding: '0.9rem 1rem' }}>
                      {doc.category ? <span className="badge badge-blue">{doc.category}</span> : '—'}
                    </td>
                    <td style={{ padding: '0.9rem 1rem', color: 'var(--text-muted)' }}>{doc.document_number || '—'}</td>
                    <td style={{ padding: '0.9rem 1rem', color: 'var(--accent-emerald-light)', fontWeight: 600 }}>
                      {doc.chunk_count}
                    </td>
                    <td style={{ padding: '0.9rem 0', textAlign: 'right' }}>
                      <button
                        onClick={() => handleDelete(doc.id, doc.title)}
                        className="btn"
                        style={{
                          background: 'rgba(248, 113, 113, 0.15)',
                          color: '#f87171',
                          padding: '0.35rem 0.75rem',
                          fontSize: '0.8rem'
                        }}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
