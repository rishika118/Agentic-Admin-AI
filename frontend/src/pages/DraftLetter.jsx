/**
 * pages/DraftLetter.jsx — Official Administrative Memo & Circular Draft Assistant
 * ==============================================================================
 * Helps NIT Calicut administrative staff draft formal memos, notices, or circulars
 * using proper institutional tone and referencing relevant administrative rules.
 */

import React, { useState } from 'react'

export default function DraftLetter() {
  const [subject, setSubject] = useState('')
  const [recipient, setRecipient] = useState('All Students & Faculty')
  const [details, setDetails] = useState('')
  const [draftText, setDraftText] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleDraft(e) {
    e.preventDefault()
    setLoading(true)
    setDraftText('')

    const prompt = `Draft a formal official administrative circular/memo for NIT Calicut.
Subject: ${subject}
Addressed to: ${recipient}
Key Points to include: ${details}

Please format as a clean, professional institutional notification referencing applicable general rules where relevant.`

    try {
      const res = await fetch('/api/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: prompt })
      })

      if (!res.ok) throw new Error('Failed to draft letter')
      const data = await res.json()
      setDraftText(data.answer)
    } catch (err) {
      setDraftText(`Error drafting document: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  function handleCopy() {
    navigator.clipboard.writeText(draftText)
    alert('Draft copied to clipboard!')
  }

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '0.4rem' }}>
          Administrative Circular & Letter Drafter
        </h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Draft official NIT Calicut circulars, notices, and memos formatted with institutional precision.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '2rem' }}>
        {/* Input Form Card */}
        <div className="glass-card" style={{ padding: '1.75rem' }}>
          <h2 style={{ fontSize: '1.25rem', marginBottom: '1.25rem' }}>Drafting Parameters</h2>
          <form onSubmit={handleDraft} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 500, marginBottom: '0.4rem', color: 'var(--text-secondary)' }}>
                Circular / Notice Subject *
              </label>
              <input
                type="text"
                className="input-field"
                placeholder="e.g. Revised Hostel Visitor Guidelines & Gate Timings"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                required
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 500, marginBottom: '0.4rem', color: 'var(--text-secondary)' }}>
                Addressed To
              </label>
              <input
                type="text"
                className="input-field"
                placeholder="e.g. All Hostel Residents / Heads of Departments"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 500, marginBottom: '0.4rem', color: 'var(--text-secondary)' }}>
                Key Instructions & Details *
              </label>
              <textarea
                className="input-field"
                rows={5}
                placeholder="Specify the rules, timings, deadlines, or compliance requirements to be announced..."
                value={details}
                onChange={(e) => setDetails(e.target.value)}
                required
              />
            </div>

            <button type="submit" disabled={loading} className="btn btn-primary">
              {loading ? '✍️ Drafting Official Circular...' : '⚡ Generate Formal Draft'}
            </button>
          </form>
        </div>

        {/* Output Preview Card */}
        <div className="glass-card" style={{ padding: '1.75rem', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <h2 style={{ fontSize: '1.25rem' }}>Official Draft Preview</h2>
            {draftText && (
              <button onClick={handleCopy} className="btn btn-secondary" style={{ padding: '0.35rem 0.8rem', fontSize: '0.85rem' }}>
                📋 Copy to Clipboard
              </button>
            )}
          </div>

          {loading ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
              Drafting institutional document...
            </div>
          ) : !draftText ? (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
              Fill in the parameters on the left and click Generate to draft an official NIT Calicut notice.
            </div>
          ) : (
            <div style={{
              background: 'rgba(15, 23, 42, 0.9)',
              border: '1px solid var(--border-color)',
              borderRadius: 'var(--radius-md)',
              padding: '1.5rem',
              whiteSpace: 'pre-wrap',
              lineHeight: 1.7,
              fontSize: '0.95rem',
              overflowY: 'auto',
              maxHeight: '520px'
            }}>
              {draftText}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
