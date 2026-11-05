import { useEffect, useState } from 'react'

export const statuses = {
  queued: 'Queued',
  awaiting_approval: 'Awaiting approval',
  needs_clarification: 'Needs clarification',
  completed: 'Completed',
  rejected: 'Rejected',
  escalated: 'Escalated',
  failed: 'Failed',
} as const

export type Status = keyof typeof statuses
export type Intent = 'status' | 'cancel' | 'return' | 'other'

export const intents: Record<Intent, string> = {
  status: 'Order status', cancel: 'Cancellation', return: 'Return', other: 'Other request',
}

export interface Order {
  id: string
  status: string
  items: { id: string; name: string; price: string }[]
  tracking_ids: string[]
  version: number
}

export interface TicketInput {
  message: string
  intent: Intent
  order_id: string | null
  cancellation_reason: string | null
  item_ids: string[]
  customer_confirmed: boolean
}

export interface Ticket {
  id: string
  customer_id: string
  created_at: string
  status: Status
  input: TicketInput
  decision: { approved: boolean; proposal_id: string } | null
  outcome: {
    response: string
    order: Order | null
    evidence: { citation: string; title: string; content: string; revision: string }[]
    proposal_id: string | null
    proposal: {
      order_id: string
      order_version: number
      action: { kind: 'cancel'; reason: string } | {
        kind: 'return'; item_ids: string[]; refund_destination: string
      }
    } | null
    result: { action_id: string; order: Order } | null
  } | null
  history: { at: string; event: string }[]
}

export async function request<T>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Authorization', `Bearer ${token}`)
  if (options.body) headers.set('Content-Type', 'application/json')
  const response = await fetch(path, { ...options, headers, cache: 'no-store' })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    const detail = typeof payload?.detail === 'string' ? payload.detail : null
    const fallback = response.status === 422 ? 'Check the request fields and try again.' : 'Try again shortly.'
    throw new Error(detail ?? `Request failed (${response.status}). ${fallback}`)
  }
  return response.json() as Promise<T>
}

interface Resource<T> {
  path: string
  data?: T
  error?: string
}

export function useResource<T>(path: string | null, token: string, revision = 0, poll = false, active = true) {
  const [state, setState] = useState<Resource<T> | null>(null)
  useEffect(() => {
    if (!active || !path) return
    const controller = new AbortController()
    let timer: number | undefined
    const refresh = async () => {
      try {
        const data = await request<T>(path, token, { signal: controller.signal })
        if (!controller.signal.aborted) setState({ path, data })
      } catch (error) {
        if (!controller.signal.aborted) {
          const message = error instanceof Error ? error.message : 'Connection failed.'
          setState(previous => ({ path, error: message, data: previous?.path === path ? previous.data : undefined }))
        }
      } finally {
        if (poll && !controller.signal.aborted) timer = window.setTimeout(refresh, 2500)
      }
    }
    void refresh()
    return () => {
      controller.abort()
      window.clearTimeout(timer)
    }
  }, [path, token, revision, poll, active])
  return state?.path === path ? state : null
}
