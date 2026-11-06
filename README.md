# SupportOps AI

An operator workspace for grounded, auditable retail support decisions.

The React workspace connects to FastAPI, PostgreSQL and a LangGraph worker. It
supports order status enquiries and operator approval of simulated cancellations
and returns. The current workflow uses a deterministic decision adapter.

## Run locally

Install Docker Desktop and start its Linux container engine. From the repository root run

```sh
docker compose up --build -d
```

Open http://localhost:8080 for the frontend and http://localhost:8000/docs for the API.
The database is exposed on localhost:54329. Compose uses documented local-only
credentials from `.env.example` as defaults. Use separate credentials for deployment.
Migrations run before the API becomes available. Data persists in the named volume.

```sh
docker compose ps
docker compose logs api migrate
docker compose down
```

Stopping the services preserves the database volume.

## Demo orders

With Compose running and `.env` set up from the example, run `uv run python -m
supportops.seed_retail --download` from the project root. This verifies the pinned
downloads and imports 24 simulated orders. Subsequent runs preserve existing
orders and action history. See `data/README.md` for provenance and adaptations.

Set `DEMO_CUSTOMER_TOKENS` in `.env` to a JSON object mapping a seeded customer
such as `demo-001` to a distinct random bearer token. Restart the API with
`docker compose up -d api` so it reads the updated environment. Authorize with
that token in the API docs and call `GET /api/orders`. Use the listed order ID
in `GET /api/orders/{order_id}`. Percent-encode the `#` in order IDs when building
a URL yourself. The API uses local demo credentials and scopes results to their owner.

## Ticket workflow

Set a separate random `DEMO_OPERATOR_TOKEN` in `.env` before starting Compose.
The customer and operator each use their own bearer token. Open the interactive
API docs at http://localhost:8000/docs to exercise the workflow.

### Browser demo

1. Seed the demo orders and configure `DEMO_CUSTOMER_TOKENS` and `DEMO_OPERATOR_TOKEN`
   in `.env`. Recreate the API with `docker compose up -d api` after credential edits.
2. Open http://localhost:8080 and select **Demo customer**. Connect using the
   token for an order owner. The order picker shows that customer's orders and statuses.
3. Ask for order status, choose a pending order to cancel, or choose a delivered
   order and select items to return. Supply the message and confirm mutation details.
4. Switch to **Operator** and connect with the separate operator token. Filter the
   queue by **Awaiting approval**, select the ticket and inspect the cited policy.
   Approve or reject the specific proposal. The ticket shows the outcome and activity.
5. Switch back to **Demo customer** to see the updated ticket status and response.

Tokens are held in browser memory until disconnect or page reload. Use locally
generated demo credentials. This browser workspace is intended for the local shop.

### API demo

1. As the customer, use `POST /api/tickets` with a fresh UUID in `request_id`, a
   message, an intent (`status`, `cancel`, `return`, or `other`) and, if known,
   an order ID. For mutations, supply `cancellation_reason` or `item_ids` and set
   `customer_confirmed` only after confirming the action details.
2. Poll `GET /api/tickets/{ticket_id}`. An incomplete request enters
   `needs_clarification`. The customer can submit revised details at
   `POST /api/tickets/{ticket_id}/clarification`.
3. As the operator, use `GET /api/tickets` or `GET /api/tickets/{ticket_id}/operator`
   to review the outcome, order facts and policy excerpts. At `awaiting_approval`,
   post the displayed `proposal_id` and an `approved` boolean to
   `POST /api/tickets/{ticket_id}/decision`.
4. The worker resumes from a PostgreSQL checkpoint and revalidates the action.
   It records at most one order change for a proposal and writes a completion event.

The worker polls the local PostgreSQL queue and locks each claimed ticket. The
order and policy nodes read in parallel. The current decision node uses the
submitted structured fields and a deterministic response adapter. Hosted
generation is a later milestone. Confirmed mutations change the simulated shop database.

Compose initializes the checkpoint tables after migrations and policy indexing.
When running the API on the host, run `uv run python -m supportops.worker --setup`
once after migrations and start `uv run python -m supportops.worker` separately.

## n8n automation

Start the optional integration with `docker compose --profile automation up --build -d`.
The `n8n/` folder contains importable workflows for authenticated ticket intake
and scheduled delivery to a local notification log. See `n8n/README.md` for
credential setup and a webhook example.

## Policy search

Compose indexes the sections in `data/policies/retail.md` after migrations.
For host-based development or a policy edit, run `uv run python -m
supportops.index_policies` to refresh the index. Query `/api/policies/search`
with a `q` parameter. Results include ranked excerpts, stable section identifiers
and a content revision. A query without enough matching evidence returns no excerpts.

The default `offline-token-hash-v1` uses deterministic token vectors via the
LangChain embeddings interface and cosine distance in PostgreSQL. It supports
repeatable tests and local demos. It measures lexical similarity and does not
measure the quality of a hosted semantic embedding model.

## Optional hosted integrations

The worker can call Microsoft Foundry to generate a cited draft for operator
review. Enable `FOUNDRY_ENABLED` in the private `.env` after configuring a budget,
an Azure OpenAI v1 endpoint, a key and a chat deployment that supports structured
outputs. The draft uses verified facts and policy excerpts. Customer messages,
order identifiers and credentials are excluded from the model prompt. The
deterministic response and operator approval rules still apply.

To use hosted vectors in the workflow, configure a separate embedding deployment
that supports 256 dimensions and explicitly build its index. Rebuild after a policy
or embedding deployment change. The public policy search endpoint uses the
offline index. The worker falls back to offline search when the hosted index
returns no excerpts or a provider error occurs.

```sh
docker compose run --rm worker .venv/bin/python -m supportops.index_policies --foundry
docker compose up -d worker
```

LangSmith is separately opt-in. Set `SUPPORTOPS_LANGSMITH_ENABLED`,
`SUPPORTOPS_LANGSMITH_API_KEY` and optionally `SUPPORTOPS_LANGSMITH_PROJECT`, then
recreate the worker. Published traces contain fixed workflow and step names,
timestamps and statuses. Raw graph inputs and outputs stay local.

## Azure demo configuration

The [Azure runbook](infra/README.md) covers Bicep validation, manually publishing
images to Azure Container Registry, deploying to Container Apps and configuring
the optional n8n VM. Live deployment requires an authorized Azure subscription,
credentials and budget.

## Backend development

Use Python 3.12 and uv. Copy `.env.example` to `.env` for host-based development,
then start the database and install the locked dependencies.

```sh
docker compose up -d db
uv sync --locked
uv run alembic upgrade head
uv run uvicorn supportops.main:create_app --factory --reload
```

## Frontend development

Use Node.js 24 and run these commands in `frontend`. The dev server proxies `/api`
to the host API on port 8000.

```sh
npm ci
npm run dev
```

## Verification

```sh
uv run ruff check .
uv run ruff format --check backend
uv run mypy
uv run pytest
```

Set `TEST_DATABASE_URL` to a migrated PostgreSQL test database with checkpoint
tables initialized. Use a separate database from any running demo worker.
Without it, pytest reports integration checks as skipped. Frontend verification uses
`npm run lint` and `npm run build` in `frontend`.

### Offline evaluation

The 50 synthetic cases in `data/evaluation/cases_v1.jsonl` cover structured retail
requests, missing details, policy denials, approvals, rejections and stale
approvals. The runner measures outcome and action correctness, citation hits,
policy violations and local graph latency including checkpoint reads and writes.
The inputs supply the intent explicitly. These scores measure workflow behavior
and policy retrieval in the demo, independent of hosted model quality.

Create a dedicated local PostgreSQL database, then run from the repository root.
The example uses PowerShell and the local demo database credentials.

```powershell
docker compose exec -T db createdb -U supportops supportops_eval
$env:EVAL_DATABASE_URL = "postgresql+psycopg://supportops:supportops-local-only@localhost:54329/supportops_eval"
$env:DATABASE_URL = $env:EVAL_DATABASE_URL
uv run alembic upgrade head
uv run python -m supportops.worker --setup
New-Item -ItemType Directory -Force .local | Out-Null
uv run python -m supportops.evaluate --output .local/offline-evaluation.json
Remove-Item Env:DATABASE_URL, Env:EVAL_DATABASE_URL
```

The frontend pins a `minimatch` override to 11.0.1 to address advisory
GHSA-g3hv-75wg-m249 in the development lint toolchain. Lint and production builds
are verified with this override. Revisit it when upstream dependencies adopt a fix.

The health endpoints distinguish process liveness from readiness. Readiness requires
database connectivity, an applied migration and the vector extension.

## Project contract

SPEC.md defines scope and acceptance, PLAN.md tracks milestones, and PROGRESS.md
records actual verification. Local commits are reviewed checkpoints. The owner
publishes changes manually. Azure resources and paid model calls require an
authorized budget and credentials.
