import { StrictMode, useState } from 'react'
import type { FormEvent } from 'react'
import { createRoot } from 'react-dom/client'
import { CustomerDesk } from './customer'
import { OperatorDesk } from './operator'
import './style.css'

type Role = 'operator' | 'customer'

function Connect({ role, onConnect }: { role: Role; onConnect: (token: string) => void }) {
  const [token, setToken] = useState('')
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (token.trim()) onConnect(token.trim())
  }
  return <section className="panel connect" aria-labelledby="connect-title">
    <p className="eyebrow">LOCAL DEMO ACCESS</p>
    <h2 id="connect-title">Connect as {role === 'operator' ? 'operator' : 'customer'}</h2>
    <p className="muted">Enter the {role} token configured for this demo in the local <code>.env</code> file.</p>
    <form onSubmit={submit}>
      <label>{role === 'operator' ? 'Operator token' : 'Customer token'}
        <input type="password" required autoComplete="off" spellCheck={false} value={token}
          onChange={event => setToken(event.target.value)} />
      </label>
      <button disabled={!token.trim()}>Connect</button>
    </form>
  </section>
}

function App() {
  const [role, setRole] = useState<Role>('operator')
  const [tokens, setTokens] = useState<Record<Role, string>>({ operator: '', customer: '' })
  const token = tokens[role]
  const disconnect = () => setTokens(previous => ({ ...previous, [role]: '' }))

  return <>
    <header className="topbar"><div className="header-content">
      <div className="brand"><div className="brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none">
        <path d="M7 10h18M7 16h18M7 22h18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <circle cx="12" cy="10" r="2" fill="currentColor" /><circle cx="20" cy="16" r="2" fill="currentColor" /><circle cx="14" cy="22" r="2" fill="currentColor" />
      </svg></div><div><strong>SupportOps AI</strong><small>Retail support workspace</small></div></div>
      <div className="header-actions"><span className="environment"><i aria-hidden="true" />Local demo</span>
        {token && <button className="secondary compact" onClick={disconnect}>Disconnect</button>}
      </div>
    </div></header>
    <main className="shell">
      <div className="intro"><p className="eyebrow">SUPPORT OPERATIONS</p><h1>{role === 'operator' ? 'Operator workspace' : 'Customer demo'}</h1>
        <p className="muted">{role === 'operator' ? 'Review requests, policy evidence and proposed actions.' : 'Open a ticket and follow its progress through the support workflow.'}</p>
      </div>
      <nav className="mode-switch" aria-label="Workspace mode">
        <button aria-pressed={role === 'operator'} onClick={() => setRole('operator')}>Operator</button>
        <button aria-pressed={role === 'customer'} onClick={() => setRole('customer')}>Demo customer</button>
      </nav>
      {tokens.operator && <div hidden={role !== 'operator'}><OperatorDesk token={tokens.operator} active={role === 'operator'} /></div>}
      {tokens.customer && <div hidden={role !== 'customer'}><CustomerDesk token={tokens.customer} active={role === 'customer'} /></div>}
      {!token && <Connect key={role} role={role} onConnect={value => setTokens(previous => ({ ...previous, [role]: value }))} />}
    </main>
  </>
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
