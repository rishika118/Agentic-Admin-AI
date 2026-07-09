/**
 * pages/Dashboard.jsx — Interactive System Dashboard
 * ===================================================
 * Displays real-time statistics from the backend, live health status
 * of all services (PostgreSQL, Qdrant, Ollama), and quick actions.
 */

import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const [documents, setDocuments] = useState([])
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchDashboardData() {
      try {
        const [docsRes, healthRes] = await Promise.all([
          fetch('/api/documents/').then(r => r.ok ? r.json() : []),
          fetch('/health/full').then(r => r.ok ? r.json() : null)
        ])
        setDocuments(docsRes || [])
        setHealth(healthRes)
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchDashboardData()
  }, [])

  const totalChunks = documents.reduce((acc, doc) => acc + (doc.chunk_count || 0), 0)

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: '2.5rem' }}>
        <h1 style={{ fontSize: '2.2rem', marginBottom: '0.5rem' }}>
          Welcome to Agentic Admin AI
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.05rem' }}>
          Intelligent Retrieval-Augmented Generation & Agentic Orchestration for NIT Calicut Administrative Documents.
        </p>
      </div>

      {/* Stat Cards Row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        gap: '1.5rem',
        marginBottom: '2.5rem'
      }}>
        {/* Total Documents Card */}
        <div className="glass-card" style={{ padding: '1.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontWeight: 500 }}>INDEXED DOCUMENTS</span>
            <span className="badge">Knowledge Base</span>
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--accent-emerald-light)' }}>
            {loading ? '...' : documents.length}
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
            PDF orders, circulars & regulations
          </p>
        </div>

        {/* Total Chunks Card */}
        <div className="glass-card" style={{ padding: '1.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontWeight: 500 }}>EMBEDDED CHUNKS</span>
            <span className="badge badge-blue">Qdrant Vectors</span>
          </div>
          <div style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--accent-cyan-light)' }}>
            {loading ? '...' : totalChunks}
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>
            Semantic chunks (bge-small-en-v1.5)
          </p>
        </div>

        {/* System Health Card */}
        <div className="glass-card" style={{ padding: '1.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontWeight: 500 }}>SYSTEM HEALTH</span>
            <span className="badge" style={{
              background: health?.status === 'ok' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
              color: health?.status === 'ok' ? 'var(--accent-emerald-light)' : '#fcd34d'
            }}>
              {health?.status ? health.status.toUpperCase() : 'CHECKING'}
            </span>
          </div>
          <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>PostgreSQL:</span>
              <span style={{ color: health?.services?.postgresql === 'ok' ? 'var(--accent-emerald-light)' : 'var(--text-muted)' }}>
                {health?.services?.postgresql || '...'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Qdrant Vector DB:</span>
              <span style={{ color: health?.services?.qdrant?.startsWith('ok') ? 'var(--accent-emerald-light)' : 'var(--text-muted)' }}>
                {health?.services?.qdrant || '...'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Ollama LLM:</span>
              <span style={{ color: health?.services?.ollama?.startsWith('ok') ? 'var(--accent-emerald-light)' : 'var(--text-muted)' }}>
                {health?.services?.ollama || '...'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Action Banner */}
      <h2 style={{ fontSize: '1.3rem', marginBottom: '1rem' }}>Quick Actions</h2>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '1.25rem',
        marginBottom: '2.5rem'
      }}>
        <Link to="/assistant" className="glass-card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ fontSize: '1.5rem' }}>💬</div>
          <h3 style={{ fontSize: '1.15rem' }}>Ask AI Assistant</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Ask natural language questions about NIT Calicut rules, policies, and circulars with real-time RAG citations.
          </p>
          <span style={{ color: 'var(--accent-emerald-light)', fontSize: '0.9rem', fontWeight: 600, marginTop: 'auto' }}>
            Open Assistant →
          </span>
        </Link>

        <Link to="/upload" className="glass-card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ fontSize: '1.5rem' }}>📁</div>
          <h3 style={{ fontSize: '1.15rem' }}>Upload Administrative Documents</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Ingest new PDF orders and circulars. Extracts metadata, chunks text, and indexes semantic vectors.
          </p>
          <span style={{ color: 'var(--accent-cyan-light)', fontSize: '0.9rem', fontWeight: 600, marginTop: 'auto' }}>
            Manage Documents →
          </span>
        </Link>

        <Link to="/report" className="glass-card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ fontSize: '1.5rem' }}>📋</div>
          <h3 style={{ fontSize: '1.15rem' }}>Generate Briefing Summary</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
            Summarize key rules and policy requirements across specific administrative departments.
          </p>
          <span style={{ color: 'var(--accent-emerald-light)', fontSize: '0.9rem', fontWeight: 600, marginTop: 'auto' }}>
            Create Report →
          </span>
        </Link>
      </div>

      {/* Recent Documents Table */}
      <div className="glass-card" style={{ padding: '1.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: '1.3rem' }}>Recently Indexed Documents</h2>
          <Link to="/upload" style={{ fontSize: '0.9rem' }}>View All Documents →</Link>
        </div>

        {loading ? (
          <p style={{ color: 'var(--text-muted)' }}>Loading documents...</p>
        ) : documents.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2.5rem 0', color: 'var(--text-muted)' }}>
            <p style={{ marginBottom: '1rem' }}>No administrative documents indexed yet.</p>
            <Link to="/upload" className="btn btn-primary">Upload Your First PDF</Link>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  <th style={{ padding: '0.75rem 0' }}>TITLE</th>
                  <th style={{ padding: '0.75rem 1rem' }}>DEPARTMENT</th>
                  <th style={{ padding: '0.75rem 1rem' }}>CATEGORY</th>
                  <th style={{ padding: '0.75rem 1rem' }}>DATE</th>
                  <th style={{ padding: '0.75rem 0' }}>CHUNKS</th>
                </tr>
              </thead>
              <tbody>
                {documents.slice(0, 5).map((doc) => (
                  <tr key={doc.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '0.95rem' }}>
                    <td style={{ padding: '0.9rem 0', fontWeight: 500, color: 'var(--text-primary)' }}>{doc.title}</td>
                    <td style={{ padding: '0.9rem 1rem', color: 'var(--text-secondary)' }}>{doc.department || '—'}</td>
                    <td style={{ padding: '0.9rem 1rem' }}>
                      {doc.category ? <span className="badge badge-blue">{doc.category}</span> : '—'}
                    </td>
                    <td style={{ padding: '0.9rem 1rem', color: 'var(--text-secondary)' }}>{doc.date || '—'}</td>
                    <td style={{ padding: '0.9rem 0', color: 'var(--accent-emerald-light)', fontWeight: 600 }}>{doc.chunk_count}</td>
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
