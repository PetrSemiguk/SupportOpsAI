import { useState } from 'react'
import { intents, request, statuses, useResource } from './api'
import type { Status, Ticket } from './api'

const timestamp = new Intl.DateTimeFormat('en-SG', { dateStyle: 'medium', timeStyle: 'short' })

export function StatusBadge({ status }: { status: Status }) {
  return <span className={`badge badge-${status}`}><i aria-hidden="true" />{statuses[status]}</span>
}

function TicketDetail({ ticket, decide, busy, error, offline }: {
  ticket: Ticket
  decide: (approved: boolean) => void
  busy: boolean
  error: string
  offline: boolean
}) {
  const outcome = ticket.outcome
  const order = outcome?.order
  const proposal = outcome?.proposal
  const canDecide = ticket.status === 'awaiting_approval' && Boolean(outcome?.proposal_id && proposal)
  return <article className="panel case" aria-labelledby="case-title">
    <div className="case-heading">
      <div><p className="eyebrow">TICKET {ticket.id.slice(0, 8).toUpperCase()}</p>
        <h2 id="case-title">{intents[ticket.input.intent]}</h2>
        <p className="muted">{ticket.customer_id} · {timestamp.format(new Date(ticket.created_at))}</p>
      </div>
      <StatusBadge status={ticket.status} />
    </div>
    <section className="case-section" aria-labelledby="message-title">
      <h3 id="message-title">Customer message</h3>
      <p className="message">{ticket.input.message}</p>
    </section>
    {outcome && <section className="case-section" aria-labelledby="response-title">
      <h3 id="response-title">Workflow response</h3>
      <p className="response" aria-live="polite">{outcome.response}</p>
      {outcome.draft && <div className="proposal model-draft">
        <strong>Model draft · Review before use</strong>
        <p>{outcome.draft.text}</p><code>{outcome.draft.citation}</code>
      </div>}
      {outcome.result && <p className="muted result-id">Action recorded · <code>{outcome.result.action_id}</code></p>}
    </section>}
    {order && <section className="case-section" aria-labelledby="order-title">
      <h3 id="order-title">Order facts</h3>
      <dl className="facts"><div><dt>Order</dt><dd>{order.id}</dd></div>
        <div><dt>Status</dt><dd>{order.status}</dd></div>
        <div><dt>Version</dt><dd>{order.version}</dd></div></dl>
      <ul className="order-items">{order.items.map((item, index) => <li key={`${item.id}-${index}`}>
        <span>{item.name} <small>{item.id}</small></span><span>{item.price}</span>
      </li>)}</ul>
      {order.tracking_ids.length > 0 && <p className="muted">Tracking · {order.tracking_ids.join(', ')}</p>}
    </section>}
    {proposal && <section className="case-section" aria-labelledby="proposal-title">
      <h3 id="proposal-title">Action proposal</h3>
      <div className="proposal">
        <strong>{proposal.action.kind === 'cancel' ? 'Cancel' : 'Request return for'} {proposal.order_id}</strong>
        <p>{proposal.action.kind === 'cancel'
          ? `Reason · ${proposal.action.reason}`
          : `Items · ${proposal.action.item_ids.join(', ')} · Refund to ${proposal.action.refund_destination}`}</p>
        <p className="muted">Order version {proposal.order_version}</p>
        {canDecide && <div className="actions">
          <button disabled={busy || offline} onClick={() => decide(true)}>Approve action</button>
          <button className="secondary" disabled={busy || offline} onClick={() => decide(false)}>Reject</button>
        </div>}
        {ticket.decision && <p className="muted">Decision recorded · {ticket.decision.approved ? 'Approved' : 'Rejected'}</p>}
        {error && <p className="error" role="alert">{error}</p>}
      </div>
    </section>}
    <section className="case-section" aria-labelledby="evidence-title">
      <h3 id="evidence-title">Policy evidence</h3>
      {outcome?.evidence.length ? outcome.evidence.map(evidence => <details className="evidence" key={evidence.citation}>
        <summary>{evidence.title}</summary><p>{evidence.content}</p>
        <code>{evidence.citation}</code><small>Revision {evidence.revision.slice(0, 12)}</small>
      </details>) : <p className="muted">No excerpts attached.</p>}
    </section>
    <section className="case-section" aria-labelledby="history-title">
      <h3 id="history-title">Activity</h3>
      <ol className="timeline">{ticket.history.map((entry, index) => <li key={`${entry.at}-${index}`}>
        <span>{entry.event.replaceAll('_', ' ')}</span>
        <time dateTime={entry.at}>{timestamp.format(new Date(entry.at))}</time>
      </li>)}</ol>
    </section>
  </article>
}

export function OperatorDesk({ token, active }: { token: string; active: boolean }) {
  const [filter, setFilter] = useState<Status | ''>('')
  const [selection, setSelection] = useState<string | null>(null)
  const [revision, setRevision] = useState(0)
  const [busy, setBusy] = useState(false)
  const [decisionError, setDecisionError] = useState('')
  const [receipt, setReceipt] = useState<Ticket | null>(null)
  const path = `/api/tickets?limit=100${filter ? `&status=${filter}` : ''}`
  const list = useResource<Ticket[]>(path, token, revision, true, active)
  const tickets = list?.data ?? []
  const selected = selection ?? tickets[0]?.id
  const detail = useResource<Ticket>(selected ? `/api/tickets/${selected}/operator` : null, token, revision, true, active)
  const fetched = detail?.data
  const ticket = receipt?.id === selected && receipt && receipt.history.length > (fetched?.history.length ?? 0)
    ? receipt : fetched

  const decide = async (approved: boolean) => {
    if (busy || ticket?.status !== 'awaiting_approval' || !ticket.outcome?.proposal_id) return
    setBusy(true)
    setDecisionError('')
    try {
      const result = await request<Ticket>(`/api/tickets/${ticket.id}/decision`, token, {
        method: 'POST', body: JSON.stringify({ proposal_id: ticket.outcome.proposal_id, approved }),
      })
      setReceipt(result)
    } catch (error) {
      setDecisionError(error instanceof Error ? error.message : 'Could not save the decision.')
    } finally {
      setBusy(false)
      setRevision(previous => previous + 1)
    }
  }

  return <div className="workspace">
    <aside className="panel queue" aria-labelledby="queue-title">
      <div className="queue-heading"><div><p className="eyebrow">WORK QUEUE</p><h2 id="queue-title">Tickets</h2></div>
        <button className="secondary compact" onClick={() => setRevision(previous => previous + 1)}>Refresh</button>
      </div>
      <div className="filter"><label htmlFor="ticket-status">Status</label><select id="ticket-status" disabled={busy} value={filter} onChange={event => {
        setFilter(event.target.value as Status | ''); setSelection(null); setDecisionError('')
      }}><option value="">All statuses</option>{Object.entries(statuses).map(([key, label]) => (
        <option key={key} value={key}>{label}</option>
      ))}</select></div>
      {list?.error && <p className="error" role="alert">{list.error}</p>}
      {!list && <p className="muted" role="status">Loading tickets…</p>}
      {list?.data && !tickets.length && <p className="muted">No tickets in this view.</p>}
      <ul className="ticket-list">{tickets.map(entry => <li key={entry.id}>
        <button className="ticket-link" disabled={busy} aria-pressed={selected === entry.id} onClick={() => {
          setSelection(entry.id); setDecisionError('')
        }}>
          <span className="ticket-title">{intents[entry.input.intent]} <small>{entry.input.order_id ?? 'No order'}</small></span>
          <span className="ticket-message">{entry.input.message}</span>
          <StatusBadge status={entry.status} />
        </button>
      </li>)}</ul>
    </aside>
    <div className="case-column">
      {detail?.error && <p className="error" role="alert">{detail.error}</p>}
      {ticket ? <TicketDetail ticket={ticket} decide={decide} busy={busy} error={decisionError} offline={Boolean(detail?.error)} />
        : <div className="panel empty" role="status">{selected ? 'Loading ticket details…' : 'Select a ticket to review its evidence and proposed action.'}</div>}
    </div>
  </div>
}
