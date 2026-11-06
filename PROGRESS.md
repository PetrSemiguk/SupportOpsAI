# Progress

## Setup snapshot — 2026-11-05 Asia/Singapore

- User cloned https://github.com/PetrSemiguk/SupportOpsAI into C:/Users/semig/SupportOpsAI.
- This existing chat is now attached to C:/Users/semig/SupportOpsAI. AGENTS.md, SPEC.md, PLAN.md, PROGRESS.md and START.md are installed in the repository root. Added .gitignore and .gitattributes for credentials/generated files and cross-platform line endings.
- The user enabled automatic approval review. Project files are writable and reviewed elevated commands now permit Git index writes. Staging all seven setup files succeeded. Git writes still use the supported approval path because .git is protected inside the default execution environment.
- Git inspection verified origin is https://github.com/PetrSemiguk/SupportOpsAI. The initial setup checkpoint is being committed on main. Consult git log for the resulting commit identifier.
- Git identity observed from existing configuration is Petr Semiguk <semiguksg@gmail.com>.
- Git ownership differs because Codex commands run as CodexSandboxOnline. Read-only inspection uses a per-command safe.directory value for this exact verified repository. No global trust changes are made.
- Environment verification found Codex CLI 0.166.0, Python 3.14.4, Node.js 26.13.0, npm 11.20.0, uv and the Python launcher. During implementation select project-compatible runtimes and pin them, rather than assuming these latest installed versions are compatible.
- After the permission change, an approved docker version command successfully returned Docker Engine 29.9.2. Container startup and image pulls will be verified during M1. Azure CLI was not found on PATH.
- Both git var GIT_AUTHOR_IDENT and GIT_COMMITTER_IDENT resolve to Petr Semiguk <semiguksg@gmail.com>. The repository contains only sample hooks, and no core.hooksPath override was returned. Inspect the actual first commit for any injected trailers after creation.
- The user activated autonomous implementation and later paused the persistent Goal. The user's follow-up asked to continue work in this chat. Follow the economical single-agent workflow with focused checks. Publishing remains manual.

## Next step

Proceed with M7. Add configurable Foundry generation and embedding adapters, redacted LangSmith tracing and at least 50 versioned evaluation cases. Keep the local deterministic path usable and distinguish its metrics from credential-dependent live results.

## Verification log

- 2026-11-05, setup verification: approved docker version returned 29.9.2; explicit git add succeeded; git diff --cached --check passed. Staged files are .gitattributes, .gitignore, AGENTS.md, PLAN.md, PROGRESS.md, SPEC.md and START.md.
- Future milestones must record changes, commands, outcomes, commit identifiers and remaining limitations. Do not mark unrun live integrations as passing.

## M1 verification — 2026-11-05

- Initial setup commit 45af498 was verified with owner author/committer identity and no co-author trailers.
- Installed project-local Python 3.12.14 via uv. Dependencies locked in uv.lock and frontend/package-lock.json. Local frontend checks use installed Node 26.13.0; Docker and CI select Node 24.
- Added FastAPI app factory, sanitized liveness/readiness, SQLAlchemy engine lifecycle, Alembic vector migration and a small React connection page.
- `ruff check .`, `ruff format --check backend`, `mypy`, frontend lint and production build passed.
- `pytest -q` with TEST_DATABASE_URL pointed to the running migrated PostgreSQL passed 3 tests, including real schema/pgvector readiness. A dependency warning notes Starlette's future transition from httpx to httpx2; no test was suppressed.
- `docker compose up --build -d` completed. Database and API are healthy. HTTP checks to the API and frontend-proxied readiness both returned ready, and the frontend root returned 200. Browser rendering has not yet been visually checked.
- `npm audit` initially found a moderate minimatch issue in development dependencies. A documented 11.0.1 override removed the findings; lint/build and a new audit passed with zero findings.
- The frontend lockfile changed after its initial image build. Rebuild web before claiming the running image includes the updated lint dependency. The generated UI bundle is unchanged.
- Local services listen only on 127.0.0.1 ports 8080, 8000 and 54329. No paid model calls, cloud resources, live LangSmith checks or dataset imports have been performed.

## M2 verification — 2026-11-05

- M1 checkpoint `b5248af` was committed locally with owner metadata. Rebuilt the frontend image during the M2 Compose check using the revised lockfile.
- Imported the pinned τ-bench retail projection. The first seed inserted 24 orders for 24 customer aliases, and the second inserted zero. Raw source files are ignored, checksums and license are recorded, and policy text documents the supported demo subset.
- `alembic upgrade head`, `alembic check`, Ruff and mypy passed. Nine pytest tests passed against the running PostgreSQL instance, including concurrent replay, rollback and scoped API access.
- Rebuilt Compose and verified order access through the running frontend proxy. Owner returned HTTP 200, another authenticated customer returned 404 and an anonymous caller returned 401. Temporary test credentials were scoped to the local demo container.
- Order writes are internal transaction functions. The later workflow must verify the operator's exact approval before calling them. Live external integrations were not exercised.

## M3 verification — 2026-11-05

- M2 checkpoint `7273af1` was committed locally with owner metadata and no co-author trailer.
- Added a dedicated policy table, four stable citation IDs with content revisions, LangChain-compatible deterministic token embeddings and cosine search via pgvector. Only the application policy file is indexed. Source tasks remain outside the index.
- Migration and `alembic check` passed. Ruff, mypy and 16 pytest tests passed against PostgreSQL. Tests verify three ranked policy matches, three missing-evidence queries and repeat indexing.
- `docker compose up --build -d --wait` succeeded. Through the running frontend proxy, the cancellation query returned `data/policies/retail.md#cancellation` and an unrelated query returned zero excerpts.
- The adapter tests lexical retrieval and makes no external calls. Its results do not measure hosted semantic embeddings. LangGraph orchestration, approvals and generation are the next milestone.

## M4 verification — 2026-11-05

- M3 checkpoint `03382a3` was committed locally with owner metadata. The live indexed revision matched the committed policy file.
- Added authenticated customer intake, clarification and operator review endpoints. Intake retries are scoped to a customer and request UUID. Decisions are scoped to the exact proposal UUID and can be replayed safely.
- LangGraph runs parallel order and policy nodes, then a decision node. Mutations interrupt before execution. `PostgresSaver` keeps checkpoints in `supportops_graph`. The local worker claims tickets using row locks, retries transient failures up to three attempts and projects outcomes and completion events together.
- The offline decision adapter uses structured intent and customer confirmation. It makes no hosted generation calls. Mutation replay uses the M2 action ledger and stale versions are rejected. If checkpoint acknowledgement is lost after a committed action, final projection can recover from that ledger.
- `alembic upgrade head`, `alembic check`, checkpoint setup, Ruff, mypy and 24 pytest tests passed against PostgreSQL. The eight workflow tests include concurrent recovery, duplicate approval, authorization, clarification, bounded failure, successful return and stale approval.
- A live HTTP smoke test through the Compose web proxy stopped the worker at the approval boundary, submitted the same approval twice while the worker was stopped, then restarted it. The order was cancelled at version 1 with exactly one action ledger entry and one completion event. Temporary records and credentials were cleaned up. API readiness passed after the test.
- Completion events are persisted locally. n8n delivery, the operator UI and live Foundry generation remain later milestones.

## M5 verification — 2026-11-05

- M4 checkpoint `4e2fb8c` was verified locally and present on the tracking branch when M5 started.
- Added separate React operator and customer views. Operators can filter the queue, review order facts and versioned policy excerpts, approve or reject proposals and see activity. Customers can submit requests, provide clarifications and see the outcome. Credentials remain in memory. Polling stops when a view is hidden.
- Frontend lint, TypeScript and Vite production build passed. No new runtime dependencies were required.
- Built and ran Compose. A fresh headless Chrome session submitted order status, cancellation and return via the customer form, inspected policy citations and used the operator filter and approval controls. PostgreSQL confirmed three completed tickets and exactly two simulated order changes. Temporary records and browser test credentials were removed.
- Inspected operator and customer layouts at desktop and 390px mobile widths. No horizontal overflow or uncaught browser errors occurred in the tested flows. Playwright and screenshots are in ignored `.local` and were used for milestone verification.
- Created ignored `.env` with random local demo credentials for `demo-007` (status), `demo-008` (pending cancellation) and `demo-021` (delivered return), plus a distinct operator token. These are local demo accounts. Model decisions still use the offline adapter.

## M6 verification — 2026-11-05

- M5 checkpoint `8561ae1` was verified locally and present on the tracking branch when M6 started.
- Added a separate completion token, a pending feed without customer details and transactional idempotent acknowledgements. Existing events remain pending after migration until consumed.
- Ruff, mypy, migrations and 25 pytest tests passed against PostgreSQL. The new integration test checks role isolation, concurrent acknowledgements and a stable first timestamp.
- Pinned n8n 2.46.6 in the optional Compose profile. Imported both JSON workflows into the local instance with separate encrypted credentials. Activated the workflows via the n8n CLI. Credential values are stored only in the ignored local environment and n8n credential store.
- A live n8n test rejected missing webhook/customer credentials, created two status tickets, returned the same ticket for a replay and passed through HTTP 409 for a conflicting body. The scheduled workflow acknowledged both completion events. Repeated acknowledgements preserved the original timestamps. Test tickets were cleaned up.
- The completion workflow records delivery to a local notification sink in PostgreSQL. External messaging and live model calls were outside this milestone.

## M7 verification — 2026-11-06

- Starting checkpoint `c1030f3` matched the tracking branch. Added opt-in Microsoft Foundry chat and embeddings adapters. The chat model receives allowlisted order facts and policy excerpts and can only add a cited draft for operator review. Approval and mutation rules stay deterministic. Hosted vectors have a separate index and require an explicit indexing command.
- Added opt-in LangSmith tracing for workflow and step names, timing and statuses. Raw graph state and SDK runtime metadata are excluded. Foundry, embeddings and LangSmith were verified with test doubles. Actual hosted calls, hosted quality, service latency and cost are unmeasured pending credentials and budget.
- Versioned 50 project-authored retail scenarios in `data/evaluation/cases_v1.jsonl`. These use explicit intent and synthetic order data, independent of the upstream benchmark. The RAG corpus remains the versioned retail policy.
- Ran `python -m supportops.evaluate --output .local/m7-evaluation.json` against a dedicated local PostgreSQL/pgvector database with real LangGraph checkpoints. 50/50 scenarios passed, with 0 policy violations and 40/40 expected citations retrieved. Workflow latency was 29.02 ms p50 and 61.54 ms p95, including checkpoint access and resumed approval runs where applicable.
- `alembic upgrade head`, `alembic check`, checkpoint setup, Ruff, mypy, frontend lint/build and all 33 pytest tests passed. API tests verified customer isolation and removal of an approval draft after rejection. The hosted-index test used provider doubles and real pgvector.
- Compose built and started the services with hosted integrations disabled. The web, API and n8n readiness routes returned HTTP 200. A live local n8n smoke test verified intake authorization, replay, conflict handling and scheduled completion acknowledgement.
- Next executable step is M8. Prepare and locally validate Azure Bicep and manual deployment workflows without provisioning Azure resources.

## M8 verification — 2026-11-06

- Starting checkpoint `0c6c559` matched the tracking branch. Added a resource-group foundation with Azure Container Apps, private PostgreSQL 17 with pgvector, ACR, Key Vault and Log Analytics. Service Bus and Blob Storage are opt-in resources reserved for later integrations. The queue stays in PostgreSQL.
- Added a public web/API app with same-origin loopback proxying, a worker without ingress, a manual migration job, restart alerts and an optional n8n VM with an operator-only SSH tunnel. The Azure demo shares a dedicated database owner credential for migrations and runtime.
- Added manually dispatched publishing and deployment workflows with separate OIDC identities. Deployment resolves images by digest, waits for the specific migration execution and checks the latest app revisions and HTTPS readiness. The Azure runbook documents prerequisites, optional demo seeding, n8n setup, monitoring and rollback.
- Bicep CLI 0.48.1 compiled all five templates. actionlint 1.7.12 and Bash syntax checks passed. A local script with Azure CLI and HTTP doubles verified the success path, deployment prevention after a failed migration, and tag validation before any Azure operation.
- Executed the compiled migration commands in the local backend container against a dedicated PostgreSQL database. Migrations and checkpoint setup succeeded, four policy sections were indexed and 24 pinned synthetic orders were seeded. Local Compose readiness and the loopback proxy topology returned HTTP 200. The optional n8n Compose configuration parsed successfully.
- Ruff, mypy, frontend lint/build and all 33 pytest tests passed. The local n8n smoke test verified intake authorization and replay, conflicting requests and scheduled acknowledgements.
- Azure-side ARM validation, image publishing, RBAC/DNS and cloud runtime checks require a configured subscription, credentials and approved budget. The GitHub release workflows were validated locally and have not been dispatched.
- Next executable step is M9. Run final local end-to-end acceptance and audit the documented readiness and Git commit metadata.

## M9 verification — 2026-11-06

- Started from `1b99afb`. Rebuilt and started the local Compose stack. On a clean isolated PostgreSQL database, the documented migration and seed commands indexed four policy sections and inserted 24 pinned orders. A second seed inserted zero orders. Verified the README demo aliases and their initial statuses.
- Repeated the three principal flows in headless Chrome through the actual React UI, Compose API, LangGraph worker and PostgreSQL. Checked tracking, policy citations, queue filtering, operator approval and the 390 px layout. The database contained exactly three completed test tickets and two simulated order changes. Temporary browser test records were cleaned up.
- Re-ran the local n8n webhook and scheduled workflow smoke test. Verified auth rejection, stable intake replay, HTTP 409 for conflicting input and idempotent scheduled acknowledgement of both test tickets.
- Added six new single-turn cases mapped to two pinned τ-bench tasks and four pinned Bitext inputs. Documented revision, checksums, licensing and synthetic order mappings. Kept upstream downloads and responses out of Git and RAG. The GitHub checks workflow now runs the offline evaluation.
- `python -m supportops.evaluate --output .local/m9-evaluation.json` passed 56/56 cases, retrieved 44/44 expected citations and recorded zero policy violations on PostgreSQL. Graph latency including checkpoint access was 38.59 ms p50 and 93.31 ms p95. Intent was explicit. The scores describe offline workflow and retrieval behavior.
- `alembic check`, 33 pytest tests, Ruff, mypy, frontend lint and build, Bicep compilation for five templates and actionlint passed. Audited every preceding commit for the owner's author and committer identity and an empty co-author trailer list. Checked tracked paths for raw data, local test state and `.env`.
- Local release acceptance is complete. The next external step is Azure subscription validation and deployment after credentials and budget are authorized. Live Foundry generation, hosted retrieval quality and LangSmith delivery remain unverified. Service Bus and Blob Storage are reserved infrastructure. Olist remains later scope.
