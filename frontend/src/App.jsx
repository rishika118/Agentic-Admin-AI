/**
 * App.jsx — Root Application Component & Router
 * ================================================
 */

import React from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'

import Dashboard   from './pages/Dashboard'
import Upload      from './pages/Upload'
import Assistant   from './pages/Assistant'
import Report      from './pages/Report'
import DraftLetter from './pages/DraftLetter'

function Navbar() {
  const linkStyle = ({ isActive }) => ({
    color: isActive ? 'var(--accent-emerald-light)' : 'var(--text-secondary)',
    textDecoration: 'none',
    fontWeight: isActive ? '600' : '400',
    padding: '0.45rem 0.9rem',
    borderRadius: 'var(--radius-sm)',
    background: isActive ? 'rgba(110,231,183,0.12)' : 'transparent',
    transition: 'all 0.2s ease',
    fontSize: '0.92rem'
  })

  return (
    <nav style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      padding: '0.9rem 2.5rem',
      background: 'rgba(15, 23, 42, 0.85)',
      backdropFilter: 'blur(16px)',
      WebkitBackdropFilter: 'blur(16px)',
      borderBottom: '1px solid var(--border-color)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      {/* Brand */}
      <span style={{
        fontWeight: '700',
        fontSize: '1.25rem',
        background: 'linear-gradient(135deg, var(--accent-emerald-light), var(--accent-cyan-light))',
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        marginRight: 'auto',
        letterSpacing: '-0.5px',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem'
      }}>
        ⚡ Agentic Admin AI
      </span>

      {/* Nav Links */}
      <NavLink to="/"          style={linkStyle}>Dashboard</NavLink>
      <NavLink to="/assistant" style={linkStyle}>AI Assistant</NavLink>
      <NavLink to="/upload"    style={linkStyle}>Documents & Upload</NavLink>
      <NavLink to="/report"    style={linkStyle}>Reports</NavLink>
      <NavLink to="/draft"     style={linkStyle}>Draft Letter</NavLink>
    </nav>
  )
}

export default function App() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />

      <main style={{ flex: 1, padding: '2.5rem', maxWidth: '1400px', width: '100%', margin: '0 auto' }}>
        <Routes>
          <Route path="/"          element={<Dashboard />} />
          <Route path="/assistant" element={<Assistant />} />
          <Route path="/upload"    element={<Upload />} />
          <Route path="/report"    element={<Report />} />
          <Route path="/draft"     element={<DraftLetter />} />
        </Routes>
      </main>
    </div>
  )
}
