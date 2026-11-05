# Implementation plan

Each milestone ends with relevant verification, diff review, a local commit when permitted and a PROGRESS.md update. Continue to the next unblocked milestone.

- [x] M0. Repository connected and instructions installed. Author and committer identities checked. Git index writes and Docker Engine access verified through automatic approval review. Activate the implementation Goal only after the user asks to start.
- [x] M1. Python 3.12.14 and Node 24 container runtime selected. Backend/frontend, lockfiles, PostgreSQL/pgvector, migration, health endpoints and CI checks implemented. Real Compose startup and database/API/web proxy checks passed.
- [x] M2. Imported 24 orders from a pinned retail snapshot and added policy documents. Verified authenticated order access, cancellation/return rules and transactional replay protection against PostgreSQL.
- [x] M3. Indexed four versioned policy sections in pgvector using an offline LangChain embeddings adapter. Verified ranked citations, repeat indexing and missing-evidence behavior through tests and live HTTP.
- [x] M4. Implemented the order, policy and decision nodes in LangGraph, persisted checkpoints, PostgreSQL queue, exact operator approval and completion events. Verified retry, replay, restart and stale proposals.
- [ ] M5. Build the React operator panel and demo intake form. Exercise principal flows through the UI and API.
- [ ] M6. Provide importable n8n workflows for intake and completion. Verify authenticated webhooks, deduplication and credential placeholders.
- [ ] M7. Add Foundry and LangSmith integration configuration and a 50-scenario evaluation suite. Run local evaluations and, only with credentials and budget, live checks. Record actual results.
- [ ] M8. Prepare Bicep, container publishing/deployment workflow definitions with manual triggers, monitoring and operational instructions. Validate templates locally. Real resource creation remains a separately authorized milestone.
- [ ] M9. Run end-to-end acceptance, resolve defects, complete README/demo instructions and audit local commit metadata. Report the exact readiness level and remaining external prerequisites.

## Later scope

- [ ] Olist historical order adapter and time-consistent reconstructed scenarios.
- [ ] Azure deployment and live smoke tests after resource scope, credentials and budget are authorized.
