import json
from typing import NotRequired, TypedDict
from uuid import uuid5

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from supportops.policies import POLICY_FILE, PolicySearchResult, search_policies
from supportops.retail import (
    ActionConflict,
    Cancellation,
    OrderDetails,
    OrderNotFound,
    ProposedAction,
    ReturnRequest,
    customer_order,
    execute_approved_action,
    validate_action,
)
from supportops.tickets import OperatorDecision, Ticket, TicketInput, TicketOutcome

POLICY_QUERIES = {
    "status": ("order-access", "Track shipment references and status for my order"),
    "cancel": ("cancellation", "Can I cancel a pending order?"),
    "return": ("return", "Return delivered items to the original payment source"),
}


class WorkflowState(TypedDict):
    ticket_id: str
    customer_id: str
    input: dict[str, object]
    order: NotRequired[dict[str, object] | None]
    evidence: NotRequired[dict[str, object]]
    outcome: NotRequired[dict[str, object]]
    decision: NotRequired[dict[str, object]]


def evaluate_ticket(state: WorkflowState, ticket: Ticket) -> TicketOutcome:
    """Deterministic decision adapter for the local demo. It makes no LLM calls."""
    payload = TicketInput.model_validate(state["input"])
    if payload.intent == "other":
        return TicketOutcome(status="escalated", response="An operator should review this request.")
    if state.get("order") is None:
        return TicketOutcome(status="needs_clarification", response="Provide an order you own.")
    order = OrderDetails.model_validate(state["order"])
    evidence = PolicySearchResult.model_validate(state["evidence"]).excerpts
    outcome = TicketOutcome(status="completed", response="", order=order, evidence=evidence)
    section_id, _ = POLICY_QUERIES[payload.intent]
    citation = f"{POLICY_FILE.as_posix()}#{section_id}"
    if not any(excerpt.citation == citation for excerpt in evidence):
        outcome.status = "escalated"
        outcome.response = "I could not find the policy needed to support this decision."
        return outcome

    if payload.intent == "status":
        tracking = (
            f" Tracking references: {', '.join(order.tracking_ids)}." if order.tracking_ids else ""
        )
        outcome.response = f"Order {order.id} is {order.status}.{tracking}"
        return outcome

    action: Cancellation | ReturnRequest
    if payload.intent == "cancel" and payload.cancellation_reason:
        action = Cancellation(reason=payload.cancellation_reason)
    elif payload.intent == "return" and payload.item_ids:
        action = ReturnRequest(item_ids=tuple(payload.item_ids))
    else:
        outcome.status = "needs_clarification"
        outcome.response = "Provide a cancellation reason or select the items to return."
        return outcome

    proposal = ProposedAction(
        order_id=order.id,
        customer_id=state["customer_id"],
        order_version=order.version,
        action=action,
    )
    try:
        validate_action(order, proposal)
    except ActionConflict as error:
        outcome.response = str(error) + "."
        return outcome

    if not payload.customer_confirmed:
        outcome.status = "needs_clarification"
        outcome.response = "Confirm the order and the exact requested action."
        return outcome

    canonical = json.dumps(proposal.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    outcome.status = "awaiting_approval"
    outcome.proposal = proposal
    outcome.proposal_id = uuid5(ticket.run_id, canonical)
    outcome.response = f"Proposed {payload.intent} for {order.id}. Awaiting operator approval."
    return outcome


def run_ticket(engine: Engine, checkpointer: PostgresSaver, ticket: Ticket) -> TicketOutcome:
    def order_agent(state: WorkflowState) -> dict[str, object]:
        payload = TicketInput.model_validate(state["input"])
        if payload.order_id is None or payload.intent == "other":
            return {"order": None}
        with Session(engine) as session:
            try:
                order = customer_order(session, state["customer_id"], payload.order_id)
            except OrderNotFound:
                return {"order": None}
        return {"order": order.model_dump(mode="json")}

    def policy_agent(state: WorkflowState) -> dict[str, object]:
        payload = TicketInput.model_validate(state["input"])
        query = POLICY_QUERIES.get(payload.intent)
        if query is None:
            return {}
        with Session(engine) as session:
            evidence = search_policies(session, query[1])
        return {"evidence": evidence.model_dump(mode="json")}

    def decision_agent(state: WorkflowState) -> dict[str, object]:
        return {"outcome": evaluate_ticket(state, ticket).model_dump(mode="json")}

    def operator_approval(state: WorkflowState) -> dict[str, object]:
        outcome = TicketOutcome.model_validate(state["outcome"])
        decision = interrupt(outcome.model_dump(mode="json"), response_schema=OperatorDecision)
        if decision.proposal_id != outcome.proposal_id:
            raise ValueError("Approval does not match the checkpointed proposal")
        return {"decision": decision.model_dump(mode="json")}

    def apply_decision(state: WorkflowState) -> dict[str, object]:
        outcome = TicketOutcome.model_validate(state["outcome"])
        decision = OperatorDecision.model_validate(state["decision"])
        if outcome.proposal is None or decision.proposal_id != outcome.proposal_id:
            raise ValueError("Approval is missing or no longer matches the proposal")
        if not decision.approved:
            outcome.status = "rejected"
            outcome.response = "The operator rejected the proposed action."
        else:
            try:
                with Session(engine) as session, session.begin():
                    result = execute_approved_action(
                        session, decision.proposal_id, outcome.proposal
                    )
            except (ActionConflict, OrderNotFound):
                outcome.status = "escalated"
                outcome.response = (
                    "The approved action is no longer eligible. Please review the order."
                )
            else:
                outcome.status = "completed"
                outcome.result = result
                outcome.order = result.order
                outcome.response = f"Order {result.order.id} is now {result.order.status}."
        return {"outcome": outcome.model_dump(mode="json")}

    def route_decision(state: WorkflowState) -> str:
        outcome = TicketOutcome.model_validate(state["outcome"])
        return "operator_approval" if outcome.status == "awaiting_approval" else END

    builder = StateGraph(WorkflowState)
    builder.add_node("order_agent", order_agent)
    builder.add_node("policy_agent", policy_agent)
    builder.add_node("decision_agent", decision_agent)
    builder.add_node("operator_approval", operator_approval)
    builder.add_node("apply_decision", apply_decision)
    builder.add_edge(START, "order_agent")
    builder.add_edge(START, "policy_agent")
    builder.add_edge(["order_agent", "policy_agent"], "decision_agent")
    builder.add_conditional_edges("decision_agent", route_decision, ["operator_approval", END])
    builder.add_edge("operator_approval", "apply_decision")
    builder.add_edge("apply_decision", END)
    graph = builder.compile(checkpointer=checkpointer)
    config: RunnableConfig = {"configurable": {"thread_id": str(ticket.run_id)}}
    checkpoint = graph.get_state(config)
    if not checkpoint.values:
        state = graph.invoke(
            {
                "ticket_id": str(ticket.id),
                "customer_id": ticket.customer_id,
                "input": ticket.input,
            },
            config,
            durability="sync",
        )
    elif checkpoint.interrupts and ticket.decision is not None:
        state = graph.invoke(Command(resume=ticket.decision), config, durability="sync")
    elif checkpoint.next and not checkpoint.interrupts:
        state = graph.invoke(None, config, durability="sync")
    else:
        # Projection may have failed after a checkpoint was already saved.
        state = checkpoint.values
    return TicketOutcome.model_validate(state["outcome"])
