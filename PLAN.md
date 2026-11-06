# Implementation plan

Each milestone ends with relevant verification, diff review, a local commit when permitted and a PROGRESS.md update. Continue to the next unblocked milestone.

- [x] M0. Repository connected and instructions installed. Author and committer identities checked. Git index writes and Docker Engine access verified through automatic approval review. Activate the implementation Goal only after the user asks to start.
- [x] M1. Python 3.12.14 and Node 24 container runtime selected. Backend/frontend, lockfiles, PostgreSQL/pgvector, migration, health endpoints and CI checks implemented. Real Compose startup and database/API/web proxy checks passed.
- [x] M2. Imported 24 orders from a pinned retail snapshot and added policy documents. Verified authenticated order access, cancellation/return rules and transactional replay protection against PostgreSQL.
- [x] M3. Indexed four versioned policy sections in pgvector using an offline LangChain embeddings adapter. Verified ranked citations, repeat indexing and missing-evidence behavior through tests and live HTTP.
- [x] M4. Implemented the order, policy and decision nodes in LangGraph, persisted checkpoints, PostgreSQL queue, exact operator approval and completion events. Verified retry, replay, restart and stale proposals.
- [x] M5. Added the React operator queue, ticket review, decisions and demo customer intake. Verified order status, cancellation and return in Chrome against the real Compose API, worker and PostgreSQL.
- [x] M6. Imported and ran two authenticated n8n workflows in Compose. Verified intake replay, conflict responses, scheduled notification acknowledgements and separate credential references.
- [x] M7. Added opt-in Foundry and LangSmith integrations and ran 50 versioned scenarios against local PostgreSQL. Provider contracts were tested with doubles. Live checks require separate credentials and budget.
- [x] M8. Prepared and compiled Azure Bicep, manual image publishing and deployment workflows, monitoring and an operational runbook. Tested release sequencing with doubles and verified local container compatibility. Live provisioning remains separate.
- [ ] M9. Run end-to-end acceptance, resolve defects, complete README/demo instructions and audit local commit metadata. Report the exact readiness level and remaining external prerequisites.

## Later scope

- [ ] Olist historical order adapter and time-consistent reconstructed scenarios.
- [ ] Azure deployment and live smoke tests after resource scope, credentials and budget are authorized.
