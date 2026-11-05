# SupportOps AI

An operator workspace for grounded, auditable retail support decisions.

Development is in progress. The current foundation provides a FastAPI service,
PostgreSQL with pgvector, migrations, a React connection-status page and demo order lookup.

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
generation and n8n event delivery are later milestones. Confirmed mutations only
change the simulated shop database.

Compose initializes the checkpoint tables after migrations and policy indexing.
When running the API on the host, run `uv run python -m supportops.worker --setup`
once after migrations and start `uv run python -m supportops.worker` separately.

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
