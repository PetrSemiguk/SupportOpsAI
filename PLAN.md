# Implementation plan

Each milestone ends with relevant verification, diff review, a local commit when permitted and a PROGRESS.md update. Continue to the next unblocked milestone.

- [x] M0. Repository connected and instructions installed. Author and committer identities checked. Git index writes and Docker Engine access verified through automatic approval review. Activate the implementation Goal only after the user asks to start.
- [ ] M1. Select and pin project-compatible runtimes. Create the backend/frontend structure, dependency locks, local PostgreSQL/pgvector container, migrations and basic CI checks. Verify clean startup, health endpoint and database connectivity.
- [ ] M2. Import pinned retail fixtures and policy documents. Implement order/customer ownership, tool adapters, policy eligibility rules and idempotent simulated actions. Verify their focused tests.
- [ ] M3. Build policy chunking, embeddings, retrieval and source citations. Keep evaluation labels isolated. Verify retrieval and missing-evidence behavior.
- [ ] M4. Implement the three-agent LangGraph flow, persisted checkpoints, durable scheduling, bounded retries, approval and resume. Verify duplicate delivery, restart and stale-proposal scenarios.
- [ ] M5. Build the React operator panel and demo intake form. Exercise principal flows through the UI and API.
- [ ] M6. Provide importable n8n workflows for intake and completion. Verify authenticated webhooks, deduplication and credential placeholders.
- [ ] M7. Add Foundry and LangSmith integration configuration and a 50-scenario evaluation suite. Run local evaluations and, only with credentials and budget, live checks. Record actual results.
- [ ] M8. Prepare Bicep, container publishing/deployment workflow definitions with manual triggers, monitoring and operational instructions. Validate templates locally. Real resource creation remains a separately authorized milestone.
- [ ] M9. Run end-to-end acceptance, resolve defects, complete README/demo instructions and audit local commit metadata. Report the exact readiness level and remaining external prerequisites.

## Later scope

- [ ] Olist historical order adapter and time-consistent reconstructed scenarios.
- [ ] Azure deployment and live smoke tests after resource scope, credentials and budget are authorized.
