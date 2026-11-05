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

Proceed with M4. Build the ticket lifecycle, three-node agent workflow and durable worker using LangGraph checkpoints and PostgreSQL. Bind operator approval to the exact proposal and reuse the order version and action ledger to revalidate and deduplicate writes. Test restart, duplicate delivery and stale approval. Live Foundry calls remain subject to credentials and budget.

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
