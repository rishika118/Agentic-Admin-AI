/**
 * pages/Assistant.jsx — Agentic AI Chat Interface
 * ==================================================
 * Interactive Q&A interface connecting to POST /api/chat.
 * Displays user prompts, agentic intent classification badges,
 * rich response text, and detailed RAG source citations.
 */

import React, { useState } from 'react'

const SUGGESTED_QUESTIONS = [
  "What are the rules for hostel visitors?",
  "What are the guidelines for hostel cleanliness?",
  "What disciplinary actions apply for hostel rule violations?"
]

export default function Assistant() {
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: "Hello! I'm your NIT Calicut Agentic Administrative Assistant. Ask me any question about office orders, circulars, rules, or policies.",
      intent: null,
      citations: []
    }
  ])
  const [loading, setLoading] = useState(false)

  async function handleSend(customQuery = null) {
    const promptText = customQuery || query
    if (!promptText.trim() || loading) return

    const newMessages = [
      ...messages,
      { role: 'user', text: promptText }
    ]
    setMessages(newMessages)
    setQuery('')
    setLoading(true)

    try {
      const res = await fetch('/api/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: promptText })
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `Server error: ${res.status}`)
      }

      const data = await res.json()

      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          text: data.answer,
          intent: data.intent,
          citations: data.citations || []
        }
      ])
    } catch (err) {
      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          text: `Error: Could not retrieve answer (${err.message}). Please ensure the FastAPI backend is running.`,
          intent: 'error',
          citations: []
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)' }}>
      {/* Header */}
      <div style={{ marginBottom: '1.25rem' }}>
        <h1 style={{ fontSize: '1.8rem', marginBottom: '0.25rem' }}>AI Administrative Assistant</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
          Powered by LangGraph Agent Orchestration & Qdrant Retrieval-Augmented Generation
        </p>
      </div>

      {/* Suggestion Chips */}
      <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
        {SUGGESTED_QUESTIONS.map((q, i) => (
          <button
            key={i}
            onClick={() => handleSend(q)}
            disabled={loading}
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-color)',
              borderRadius: '9999px',
              padding: '0.4rem 0.9rem',
              color: 'var(--text-secondary)',
              fontSize: '0.85rem',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            💡 {q}
          </button>
        ))}
      </div>

      {/* Chat Messages Area */}
      <div className="glass-card" style={{
        flex: 1,
        overflowY: 'auto',
        padding: '1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.5rem',
        marginBottom: '1rem'
      }}>
        {messages.map((msg, index) => (
          <div
            key={index}
            style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: msg.role === 'user' ? '70%' : '88%',
              width: msg.role === 'user' ? 'auto' : '100%',
            }}
          >
            {/* Sender Label & Intent Badge */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              marginBottom: '0.4rem',
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
            }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                {msg.role === 'user' ? 'YOU' : 'AGENTIC ASSISTANT'}
              </span>
              {msg.intent && (
                <span className="badge" style={{
                  fontSize: '0.68rem',
                  background: msg.intent === 'answer'
                    ? 'rgba(16, 185, 129, 0.18)'
                    : msg.intent === 'clarify'
                    ? 'rgba(245, 158, 11, 0.18)'
                    : 'rgba(148, 163, 184, 0.18)',
                  color: msg.intent === 'answer'
                    ? 'var(--accent-emerald-light)'
                    : msg.intent === 'clarify'
                    ? '#fcd34d'
                    : '#e2e8f0'
                }}>
                  Intent: {msg.intent.toUpperCase()}
                </span>
              )}
            </div>

            {/* Bubble */}
            <div style={{
              background: msg.role === 'user'
                ? 'linear-gradient(135deg, var(--accent-emerald), var(--accent-cyan))'
                : 'var(--bg-surface)',
              color: msg.role === 'user' ? '#042f2e' : 'var(--text-primary)',
              padding: '1rem 1.25rem',
              borderRadius: msg.role === 'user'
                ? '16px 16px 4px 16px'
                : '16px 16px 16px 4px',
              border: msg.role === 'user' ? 'none' : '1px solid var(--border-color)',
              fontWeight: msg.role === 'user' ? 500 : 400,
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap'
            }}>
              {msg.text}

              {/* Citations block */}
              {msg.citations && msg.citations.length > 0 && (
                <div style={{
                  marginTop: '1.25rem',
                  paddingTop: '1rem',
                  borderTop: '1px solid rgba(255, 255, 255, 0.12)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.65rem'
                }}>
                  <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--accent-emerald-light)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    📚 RETRIEVED GROUNDING SOURCES ({msg.citations.length})
                  </div>
                  {msg.citations.map((cite, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: 'rgba(15, 23, 42, 0.65)',
                        border: '1px solid var(--border-color)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '0.75rem',
                        fontSize: '0.85rem'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                          [{idx + 1}] {cite.document_title} — Page {cite.page_no}
                        </span>
                        <span className="badge badge-blue" style={{ fontSize: '0.7rem' }}>
                          Match: {Math.round(cite.score * 100)}%
                        </span>
                      </div>
                      <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', fontStyle: 'italic', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        "{cite.chunk_text}"
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--accent-emerald-light)' }}>
            <span style={{ animation: 'pulse 1.5s infinite' }}>🤖 Thinking & querying RAG engine...</span>
          </div>
        )}
      </div>

      {/* Input Form Area */}
      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <input
          type="text"
          className="input-field"
          placeholder="Ask a question about administrative rules, leave, circulars..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          style={{ flex: 1 }}
        />
        <button
          className="btn btn-primary"
          onClick={() => handleSend()}
          disabled={loading || !query.trim()}
          style={{ minWidth: '130px' }}
        >
          {loading ? 'Sending...' : 'Send →'}
        </button>
      </div>
    </div>
  )
}
