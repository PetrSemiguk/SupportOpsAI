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

Cancellation and return operations are internal service functions. The operator
approval workflow will expose them through the ticket lifecycle in a later milestone.

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

Set `TEST_DATABASE_URL` to a migrated PostgreSQL database to include the integration
check. Without it, pytest reports that check as skipped. Frontend verification uses
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
