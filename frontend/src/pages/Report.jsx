/**
 * pages/Report.jsx — Administrative Briefing Summary Generator
 * =============================================================
 * Synthesizes key regulations and circular policies into formatted reports
 * using the Agentic AI RAG backend.
 */

import React, { useState } from 'react'

const REPORT_TEMPLATES = [
  {
    label: "Hostel Rules & Visitor Policies Briefing",
    prompt: "Summarize all key regulations regarding hostel visitor timings, cleanliness guidelines, and disciplinary actions from the administrative circulars."
  },
  {
    label: "Leave & Attendance Guidelines Summary",
    prompt: "Provide a structured summary of rules and procedures regarding staff and student attendance and leave policies."
  },
  {
    label: "General Office Orders Overview",
    prompt: "Summarize the major administrative orders and compliance guidelines issued by NIT Calicut."
  }
]

export default function Report() {
  const [selectedPrompt, setSelectedPrompt] = useState(REPORT_TEMPLATES[0].prompt)
  const [reportText, setReportText] = useState('')
  const [citations, setCitations] = useState([])
  const [loading, setLoading] = useState(false)

  async function generateReport() {
    setLoading(true)
    setReportText('')
    setCitations([])

    try {
      const res = await fetch('/api/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: selectedPrompt })
      })

      if (!res.ok) throw new Error('Failed to generate report from backend')
      const data = await res.json()

      setReportText(data.answer)
      setCitations(data.citations || [])
    } catch (err) {
      setReportText(`Error generating briefing report: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '0.4rem' }}>
          Executive Briefing Report Generator
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Generate structured policy summaries grounded strictly in indexed NIT Calicut circulars and regulations.
        </p>
      </div>

      <div className="glass-card" style={{ padding: '1.75rem', marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Select Policy Focus Area</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem', marginBottom: '1.5rem' }}>
          {REPORT_TEMPLATES.map((tpl, i) => (
            <label
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.9rem 1.1rem',
                borderRadius: 'var(--radius-md)',
                background: selectedPrompt === tpl.prompt ? 'rgba(16, 185, 129, 0.12)' : 'var(--bg-surface)',
                border: `1px solid ${selectedPrompt === tpl.prompt ? 'var(--accent-emerald)' : 'var(--border-color)'}`,
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              <input
                type="radio"
                name="report_topic"
                checked={selectedPrompt === tpl.prompt}
                onChange={() => setSelectedPrompt(tpl.prompt)}
              />
              <div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{tpl.label}</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>"{tpl.prompt}"</div>
              </div>
            </label>
          ))}
        </div>

        <button onClick={generateReport} disabled={loading} className="btn btn-primary">
          {loading ? '⚙️ Synthesizing Briefing Report via RAG...' : '⚡ Generate Policy Briefing Report'}
        </button>
      </div>

      {/* Generated Report Display */}
      {(reportText || loading) && (
        <div className="glass-card" style={{ padding: '2rem' }}>
          <h2 style={{ fontSize: '1.4rem', marginBottom: '1rem', color: 'var(--accent-emerald-light)' }}>
            📋 Administrative Synthesis Report
          </h2>

          {loading ? (
            <p style={{ color: 'var(--text-muted)' }}>Analyzing vector database and drafting executive summary...</p>
          ) : (
            <div>
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, fontSize: '1.02rem', marginBottom: '1.5rem' }}>
                {reportText}
              </div>

              {citations.length > 0 && (
                <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
                  <h3 style={{ fontSize: '0.95rem', color: 'var(--accent-cyan-light)', marginBottom: '0.75rem' }}>
                    📚 Source References & Compliance Grounding
                  </h3>
                  <div style={{ display: 'grid', gap: '0.75rem' }}>
                    {citations.map((c, i) => (
                      <div key={i} style={{ background: 'var(--bg-surface)', padding: '0.8rem 1rem', borderRadius: 'var(--radius-sm)' }}>
                        <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                          [{i + 1}] {c.document_title} — Page {c.page_no} ({Math.round(c.score * 100)}% match)
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
