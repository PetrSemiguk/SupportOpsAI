# Local n8n workflows

The optional Compose `automation` profile runs n8n 2.46.6 at
http://localhost:5678 with a persistent volume. The workflows address the API
by its Compose service name, `http://api:8000`.

## Install

1. Configure the customer tokens as described in the project README. Generate
   distinct random values for `N8N_INTAKE_KEY` and `N8N_COMPLETION_TOKEN` in `.env`.
   The API receives the completion token. The intake key is used in n8n and by
   webhook callers.
2. Run `docker compose --profile automation up --build -d`. Open n8n and finish
   local owner setup if prompted.
3. Import both JSON files from `workflows/` using the editor's file import.
   On an instance where they already exist, open the imported workflows.
4. Create two **Header Auth** credentials and select them on the corresponding
   nodes. IDs in the workflow files are placeholders for credential references.

| Credential | Header name | Value | Nodes |
| --- | --- | --- | --- |
| SupportOps intake key | `X-SupportOps-Intake-Key` | The local `N8N_INTAKE_KEY` | Receive support request |
| SupportOps completion token | `Authorization` | `Bearer ` followed by `N8N_COMPLETION_TOKEN` | Read pending completions, Record demo notification |

5. Publish both workflows in the local editor. Use the production webhook URL
   after publishing. The scheduled completion workflow runs every 15 seconds.

Saved execution data and telemetry are disabled in the local Compose profile.
Credential values belong in the n8n credential store and the ignored `.env` file.
The editor and webhook listen on loopback for the HTTP demo. A separately hosted
instance needs its API URL, HTTPS and credential configuration set for that host.

## Intake

Send `POST http://localhost:5678/webhook/supportops/intake` with both the intake
key header and `Authorization: Bearer <customer token>`. The body is the existing
ticket API payload. An example shape follows.

```json
{
  "request_id": "9cb1ac18-f84a-4ddd-944a-f61d43f61934",
  "message": "Where is my order?",
  "intent": "status",
  "order_id": "#W1770559"
}
```

Use a fresh UUID for a new request, and an order belonging to the authenticated
customer. The workflow forwards the request to `/api/tickets` and returns the
API's status and receipt. A retry with the same customer, UUID and body returns
the same ticket. A conflicting retry returns HTTP 409.

## Completion notifications

The scheduled workflow reads up to 25 unacknowledged events using the dedicated
completion token. It records each notification through
`POST /api/integrations/completions/{ticket_id}/ack`. This local demo sink saves
the first `delivered_at` timestamp in PostgreSQL. Concurrent or repeated calls
return the same receipt. Unacknowledged events remain available for the next poll.
The feed contains ticket identifiers, statuses and timestamps. The workflow's
notification destination is the local database.
