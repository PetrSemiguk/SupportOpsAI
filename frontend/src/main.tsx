import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

function App() {
  const [status, setStatus] = useState('Checking connection…')

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/health/ready', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('Service unavailable')
        const result = await response.json()
        setStatus(result.status === 'ready' ? 'API and database connected' : 'Service unavailable')
      })
      .catch(() => {
        if (!controller.signal.aborted) setStatus('Service unavailable — check the API connection')
      })
    return () => controller.abort()
  }, [])

  return (
    <main>
      <p className="eyebrow">SUPPORT OPERATIONS · DEVELOPMENT</p>
      <h1>SupportOps AI</h1>
      <p>Evidence-backed decisions. Human-approved actions.</p>
      <section aria-labelledby="environment-title">
        <h2 id="environment-title">Local environment</h2>
        <p role="status">{status}</p>
        <p className="note">Foundation milestone. Ticket workflows are being developed.</p>
      </section>
    </main>
  )
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
