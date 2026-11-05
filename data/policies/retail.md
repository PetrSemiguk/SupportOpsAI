# SupportOps demo shop policies

## Order access [order-access]

Authenticate the customer before looking up orders. Only disclose orders attached to the authenticated customer. Provide the stored status, items and any tracking references when available. Ask for clarification if an order cannot be identified. Escalate requests outside the demo shop's supported actions.

## Cancellation [cancellation]

Only a pending order qualifies for cancellation. Confirm the order and whether the customer ordered by mistake or no longer needs the items. Submit the proposed action for operator approval. After approval, verify the order version and current status again. A successful simulated cancellation updates the status to cancelled. Any associated repayment is simulated and uses the original payment source.

## Return [return]

Only a delivered order qualifies for a return request. Confirm the order and the specific items to return. The demo supports refunds to the original payment source when it can be verified. Submit the proposed action for operator approval and recheck eligibility at execution. The resulting order status is return requested. A return request records intent and does not indicate that a refund has settled.

## Approval [approval]

Customer confirmation is required for the order and action details. An operator must then approve the exact proposal before any change to an order. An earlier approval does not apply if the order changes. The same approval identifier cannot execute a different action. Replaying a previously completed action returns its recorded result.

Adapted from the τ-bench retail policy. See the data provenance notes for revision, attribution, license and adaptations.
