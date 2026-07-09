/**
 * main.jsx — React Application Bootstrap
 * ========================================
 * This is the first JavaScript file that runs in the browser.
 * It:
 *  1. Imports React and ReactDOM.
 *  2. Wraps the <App> component in React.StrictMode (helps catch bugs during development).
 *  3. Mounts the React app into the <div id="root"> in index.html.
 *
 * You will rarely need to change this file.
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {/* BrowserRouter enables page-level routing with react-router-dom */}
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
