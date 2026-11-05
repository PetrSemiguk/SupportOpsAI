import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { intents, request, useResource } from './api'
import type { Intent, Order, Ticket, TicketInput } from './api'
import { StatusBadge } from './operator'

const emptyInput: TicketInput = {
  message: '', intent: 'status', order_id: null, cancellation_reason: null,
  item_ids: [], customer_confirmed: false,
}

function RequestForm({ orders, token, clarification, onSave }: {
  orders: Order[]
  token: string
  clarification?: Ticket
  onSave: (ticket: Ticket) => void
}) {
  const [input, setInput] = useState(clarification?.input ?? emptyInput)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const pending = useRef<{ payload: string; id: string } | null>(null)
  const order = orders.find(candidate => candidate.id === input.order_id)
  const items = [...new Map(order?.items.map(item => [item.id, item])).values()]
  const mutation = input.intent === 'cancel' || input.intent === 'return'

  const changeAction = (fields: Partial<TicketInput>) => {
    setInput(previous => ({ ...previous, ...fields, customer_confirmed: false }))
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (busy) return
    setError('')
    setBusy(true)
    const normalized = { ...input, message: input.message.trim() }
    const payload = JSON.stringify(normalized)
    try {
      let path = '/api/tickets'
      let body = payload
      if (clarification) {
        path = `/api/tickets/${clarification.id}/clarification`
      } else {
        if (pending.current?.payload !== payload) pending.current = { payload, id: crypto.randomUUID() }
        body = JSON.stringify({ ...normalized, request_id: pending.current.id })
      }
      const receipt = await request<Ticket>(path, token, { method: 'POST', body })
      pending.current = null
      onSave(receipt)
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Unable to submit the request.')
    } finally {
      setBusy(false)
    }
  }

  return <form className="request-form" onSubmit={event => void submit(event)}>
    <fieldset disabled={busy}>
      <legend>{clarification ? 'Clarify your request' : 'New support request'}</legend>
      <label>Request type<select value={input.intent} onChange={event => changeAction({
        intent: event.target.value as Intent, cancellation_reason: null, item_ids: [],
      })}>{Object.entries(intents).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
      <label>Your order<select value={input.order_id ?? ''} onChange={event => changeAction({ order_id: event.target.value || null, item_ids: [] })}>
        <option value="">No order supplied</option>
        {orders.map(entry => <option value={entry.id} key={entry.id}>{entry.id} · {entry.status}</option>)}
      </select></label>
      {input.intent === 'cancel' && <label>Cancellation reason<select value={input.cancellation_reason ?? ''}
        onChange={event => changeAction({ cancellation_reason: event.target.value || null })}>
        <option value="">Choose a reason</option><option>ordered by mistake</option><option>no longer needed</option>
      </select></label>}
      {input.intent === 'return' && <fieldset className="items-field">
        <legend>Items to return</legend>
        {items.length ? items.map(item => <label key={item.id} className="check-label">
          <input type="checkbox" checked={input.item_ids.includes(item.id)} onChange={event => changeAction({
            item_ids: event.target.checked ? [...input.item_ids, item.id] : input.item_ids.filter(id => id !== item.id),
          })} />{item.name} <small>{item.id}</small>
        </label>) : <p className="muted">Select an order to see its items.</p>}
      </fieldset>}
      <label>Message<textarea required maxLength={1500} rows={4} value={input.message}
        placeholder="Tell the support team how they can help."
        onChange={event => setInput({ ...input, message: event.target.value })} /></label>
      {mutation && <label className="check-label confirmation"><input type="checkbox" checked={input.customer_confirmed}
        onChange={event => setInput({ ...input, customer_confirmed: event.target.checked })} />
        I confirm this order and the action details above.
      </label>}
      <button disabled={busy || !input.message.trim()}>{busy ? 'Sending…' : clarification ? 'Send clarification' : 'Submit ticket'}</button>
      {error && <p className="error" role="alert">{error}</p>}
    </fieldset>
  </form>
}

export function CustomerDesk({ token, active }: { token: string; active: boolean }) {
  const [receipt, setReceipt] = useState<Ticket | null>(null)
  const [revision, setRevision] = useState(0)
  const ticketResult = useResource<Ticket>(receipt ? `/api/tickets/${receipt.id}` : null, token, revision, Boolean(receipt), active)
  const fetched = ticketResult?.data
  const ticket = fetched && fetched.history.length >= (receipt?.history.length ?? 0) ? fetched : receipt
  const orders = useResource<Order[]>('/api/orders', token, revision, false, active)
  const activeTicket = ticket?.status === 'needs_clarification' ? ticket : undefined

  const save = (result: Ticket) => {
    setReceipt(result)
    setRevision(previous => previous + 1)
  }

  return <div className="customer-layout">
    <section className="panel customer-panel" aria-labelledby="customer-title">
      <p className="eyebrow">DEMO CUSTOMER</p><h2 id="customer-title">Request support</h2>
      <p className="muted">Send an order question or request a simulated shop action.</p>
      {orders?.error && <div className="error" role="alert">{orders.error} <button className="secondary compact" onClick={() => setRevision(previous => previous + 1)}>Retry</button></div>}
      {!orders && <p role="status">Loading your orders…</p>}
      {orders?.data && (!ticket || activeTicket) && <RequestForm key={activeTicket?.id ?? 'new'}
        orders={orders.data} token={token} clarification={activeTicket} onSave={save} />}
      {ticket && !activeTicket && <button className="secondary" onClick={() => {
        setReceipt(null); setRevision(previous => previous + 1)
      }}>Start another request</button>}
    </section>
    <section className="panel customer-panel" aria-labelledby="receipt-title">
      <p className="eyebrow">REQUEST TRACKING</p><h2 id="receipt-title">Ticket status</h2>
      {ticket ? <div className="receipt">
        <StatusBadge status={ticket.status} />
        <p className="muted">Reference {ticket.id.slice(0, 8).toUpperCase()}</p>
        <p aria-live="polite">{ticket.outcome?.response ?? 'Your request is queued for processing.'}</p>
      </div> : <p className="muted">Your ticket and its latest response will appear here.</p>}
      {ticketResult?.error && <p className="error" role="alert">{ticketResult.error}</p>}
    </section>
  </div>
}
