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

## Evaluation inputs

`evaluation/cases_v1.jsonl` contains 50 project-authored workflow cases.
`evaluation/adapted_cases_v1.jsonl` contains six additional cases based on the
source requests below. Each row is a new paraphrase and a single structured turn.
Expected actions and citations are authored from the SupportOps policy. The
runner creates its own order and customer for each case. No source customer,
order or payment identifier is carried into the evaluation or matched across
datasets. Source responses and evaluation fixtures stay outside the RAG corpus.
The results measure SupportOps workflow behavior on these cases.

The τ-bench mappings refer to task IDs in the pinned retail `tasks.json`
(SHA-256 `8e03ebce7901bd6218e7a7dc3105faa9324091a68058f7fe61c65262868812e8`).
The Bitext mappings refer to one-based CSV data rows, excluding the header.
Bitext is hybrid synthetic support data under CDLA-Sharing-1.0. The
[pinned Bitext dataset](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset/tree/430d1a89bd93bd1fa23c16f29dd53e73f0087443)
contains `Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv`
(SHA-256 `6f81102b0100b97b8468eb04368033a23206bf1fde9d53500d5806ec1001a434`).
The CSV and its responses are excluded from the repository and runtime.

| Evaluation case | Source and adaptation | Demo order |
| --- | --- | --- |
| `tau-retail-16-cancel` | τ-bench task 16, isolate the cancellation request | One pending order, confirmed reason and operator approval |
| `tau-retail-5-return` | τ-bench task 5, use the final request to return one item | Delivered order, the bottle mapped to `item-1`, confirmed and approved |
| `bitext-1-cancel` | Bitext row 1, cancellation enquiry | Pending order, reason and confirmation still needed |
| `bitext-24883-status` | Bitext row 24883, order status enquiry | Processed order with tracking |
| `bitext-15899-refund` | Bitext row 15899, standalone refund enquiry | Delivered order, escalation for operator review |
| `bitext-1996-address` | Bitext row 1996, address change enquiry | Processed order, escalation for operator review |
