# SupportOps AI specification

## Outcome

Build a portfolio application for a junior AI engineering role. A support operator reviews customer tickets, sees order facts and cited shop policies, approves permitted actions and receives a verifiable result. Agent execution is inspectable and recoverable.

## Agreed technology

- Python, FastAPI, Pydantic, SQLAlchemy and Alembic.
- LangChain for model/tool/retrieval integrations and LangGraph for agent workflow state.
- n8n for external intake and completion notifications through authenticated API/webhooks.
- LLM API via Microsoft Foundry. Select exact generation and embedding models after checking availability, quality and authorized budget. Environment variables identify deployments.
- PostgreSQL with pgvector for application data, persistent graph checkpoints and policy retrieval.
- React and TypeScript operator interface.
- LangSmith for agent traces and evaluations, with secrets and sensitive fields redacted.
- pytest, frontend checks, Docker Compose, Git and GitHub Actions.
- Azure Container Apps for API and worker, Azure Database for PostgreSQL, Service Bus, Blob Storage, Key Vault, Container Registry, Azure Monitor and a VM for n8n.
- Use Bicep for Azure infrastructure as code as the initial implementation choice. Record any necessary change.

## Data and provenance

Start with the retail domain in https://github.com/sierra-research/tau2-bench . Pin a revision and retain license and attribution. Import a bounded reproducible fixture from its database, policy and tasks. These are research simulation data.

Use selected inputs from https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset to expand language variation. They are hybrid synthetic data under the dataset's stated license. Explicitly record mappings to shop orders. Dataset answers are not authoritative shop policy.

Olist is a later extension using real historical Brazilian orders. Preserve original semantics, dates, currency and provenance. Adapted tickets and reconstructed time snapshots must be labeled. Do not join unrelated datasets as if their customers or orders matched.

Keep evaluation answers outside RAG. Distinguish upstream benchmark results from adapted project scenarios. Store source URL, revision/checksum, license and transformation notes.

## Product and workflow

1. A demo client creates an authenticated support ticket.
2. The API validates ownership and input, persists the ticket and schedules processing.
3. The order agent obtains structured facts through shop tools. The policy agent retrieves applicable policy fragments with source identifiers. Read-only work may run concurrently where dependency and policy rules permit.
4. The decision agent proposes an action and customer response grounded in both results.
5. Deterministic backend rules check eligibility, ownership and the proposed state transition.
6. Any mutation waits for explicit operator approval tied to the exact proposed action. Revalidate the order at execution time.
7. Execute an idempotent simulated shop action, save the result and publish a completion event.

Missing information triggers clarification. Unsupported requests are escalated. Tool failures have bounded retries and visible failure states. A worker does not remain occupied while awaiting human approval. Queue messages may be delivered more than once.

The UI contains ticket list, status filters, ticket details, order facts, policy citations, action proposal, approve/reject controls and execution history. Include a demo ticket form. Default interface language is English for the Singapore-facing portfolio.

## Required scenarios

- Order/delivery status enquiry grounded in shop data.
- Eligible cancellation, ineligible cancellation and already-cancelled order.
- Eligible return/refund request and an ineligible request, according to the selected policy.
- Missing order identifier, wrong customer ownership and unavailable tool.
- Approval followed by worker restart and successful recovery.
- Duplicate request or queue delivery with exactly one business mutation.
- Order state changed between proposal and approval, requiring revalidation.

## Acceptance

- A documented local Docker Compose startup and repeatable seed/import process work.
- A user can complete the three principal flows through the operator UI and real local API/database.
- A real LangGraph flow and RAG pipeline run. Offline fixtures are explicitly labeled. Live Foundry/embedding and LangSmith checks require available credentials and budget and must be reported separately.
- n8n workflows can be imported, have documented credentials, and pass a local demo integration test.
- Business rules, access checks, duplicate delivery and restart recovery have automated tests.
- At least 50 versioned evaluation scenarios include expected actions and citations. Report actual task success, policy violations, retrieval results and latency. Report cost only when measured from live runs.
- Azure configuration validates and deployment/runbook prerequisites are documented. Actual Azure deployment is a separate authorized milestone.
- Required build, lint, type and test checks pass. The README documents launch, architecture, test commands and known limitations.
- Reviewed local commits use the owner's Git identity, with no AI co-author trailers. Publishing is manual.

## Scope

First release supports one demo shop and the specified scenarios. Additional channels, localization, Olist and extra frameworks are follow-up milestones. Preserve a clear separation between working local functionality, validated cloud configuration and tested live cloud integration.
