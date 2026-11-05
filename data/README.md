# Retail demo data provenance

- Source: https://github.com/sierra-research/tau2-bench/tree/033bf082f48e4a3c6a1256208e93cf2ce9c3bb6f/data/tau2/domains/retail
- Revision: `033bf082f48e4a3c6a1256208e93cf2ce9c3bb6f`
- Attribution: Copyright (c) 2025 Sierra Research. See `licenses/tau-bench-MIT.txt`.
- Data type: simulated retail research data. Amounts and shipment references are demo values.

`supportops.seed_retail` verifies SHA-256 checksums for the source database, policy,
tasks and license. These downloads stay under ignored `data/raw/tau-retail`.
The importer sorts orders by source ID and selects up to six for each status.
The pinned snapshot has 24 selected orders. Import replaces customer names with
stable `demo-NNN` aliases and omits addresses, email and payment identifiers.
Existing records are preserved, including mutations from earlier demos.

`policies/retail.md` is an application-specific policy adapted from the upstream
retail policy. SupportOps adds operator approval after confirmation of the customer
request. It supports status enquiries, cancellation and return to the original
payment source. Other τ-bench actions and payment routing are outside the current
demo. The action ledger stores simulated changes and no payment transactions.

The upstream tasks remain separate from policies and order fixtures. They may be
adapted into test cases during evaluation. This application is not an official
τ-bench benchmark run.
