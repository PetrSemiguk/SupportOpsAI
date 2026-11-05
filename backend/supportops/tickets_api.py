from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from supportops.auth import require_operator
from supportops.orders_api import CustomerIdentity, DatabaseSession
from supportops.retail import Customer, Order
from supportops.tickets import (
    HistoryEntry,
    OperatorDecision,
    Ticket,
    TicketCreate,
    TicketInput,
    TicketStatus,
    TicketView,
)

router = APIRouter(prefix="/api/tickets", tags=["Tickets"])
operator = [Depends(require_operator)]


def check_owned_order(session: DatabaseSession, customer_id: str, order_id: str | None) -> None:
    if (
        order_id
        and session.scalar(
            select(Order.id).where(Order.id == order_id, Order.customer_id == customer_id)
        )
        is None
    ):
        raise HTTPException(404, "Order not found")


@router.post("", status_code=202)
def submit_ticket(
    payload: TicketCreate, customer_id: CustomerIdentity, session: DatabaseSession
) -> TicketView:
    with session.begin():
        if session.get(Customer, customer_id) is None:
            raise HTTPException(404, "Demo customer not found")
        check_owned_order(session, customer_id, payload.order_id)
        request = payload.model_dump(mode="json", exclude={"request_id"})
        history = HistoryEntry(at=datetime.now(UTC), event="submitted").model_dump(mode="json")
        ticket = session.scalar(
            insert(Ticket)
            .values(
                customer_id=customer_id,
                request_id=payload.request_id,
                initial_input=request,
                input=request,
                history=[history],
            )
            .on_conflict_do_nothing(constraint="uq_ticket_customer_request")
            .returning(Ticket)
        )
        if ticket is None:
            ticket = session.scalars(
                select(Ticket).where(
                    Ticket.customer_id == customer_id,
                    Ticket.request_id == payload.request_id,
                )
            ).one()
            if ticket.initial_input != request:
                raise HTTPException(409, "Request ID already used for different input")
        return TicketView.model_validate(ticket)


@router.get("/{ticket_id}")
def read_ticket(
    ticket_id: UUID, customer_id: CustomerIdentity, session: DatabaseSession
) -> TicketView:
    ticket = session.scalar(
        select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.customer_id == customer_id,
        )
    )
    if ticket is None:
        raise HTTPException(404, "Ticket not found")
    return TicketView.model_validate(ticket)


@router.post("/{ticket_id}/clarification", status_code=202)
def clarify_ticket(
    ticket_id: UUID, payload: TicketInput, customer_id: CustomerIdentity, session: DatabaseSession
) -> TicketView:
    with session.begin():
        ticket = session.scalar(
            select(Ticket)
            .where(
                Ticket.id == ticket_id,
                Ticket.customer_id == customer_id,
            )
            .with_for_update()
        )
        if ticket is None:
            raise HTTPException(404, "Ticket not found")
        if ticket.status != "needs_clarification":
            raise HTTPException(409, "Ticket is not awaiting clarification")
        check_owned_order(session, customer_id, payload.order_id)
        ticket.input = payload.model_dump(mode="json")
        ticket.run_id = uuid4()
        ticket.status = "queued"
        ticket.attempts = 0
        ticket.available_at = datetime.now(UTC)
        ticket.outcome = None
        ticket.record("clarification_received")
        return TicketView.model_validate(ticket)


@router.get("", dependencies=operator)
def list_tickets(
    session: DatabaseSession,
    status: TicketStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[TicketView]:
    query = select(Ticket).order_by(Ticket.created_at.desc(), Ticket.id).limit(limit)
    if status is not None:
        query = query.where(Ticket.status == status)
    return [TicketView.model_validate(ticket) for ticket in session.scalars(query)]


@router.get("/{ticket_id}/operator", dependencies=operator)
def read_ticket_as_operator(ticket_id: UUID, session: DatabaseSession) -> TicketView:
    ticket = session.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(404, "Ticket not found")
    return TicketView.model_validate(ticket)


@router.post("/{ticket_id}/decision", status_code=202, dependencies=operator)
def decide_ticket(
    ticket_id: UUID, decision: OperatorDecision, session: DatabaseSession
) -> TicketView:
    with session.begin():
        ticket = session.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
        if ticket is None:
            raise HTTPException(404, "Ticket not found")
        recorded = decision.model_dump(mode="json")
        if ticket.decision is not None:
            if ticket.decision != recorded:
                raise HTTPException(409, "A different decision is already recorded")
            return TicketView.model_validate(ticket)
        if ticket.status != "awaiting_approval" or ticket.outcome is None:
            raise HTTPException(409, "Ticket is not awaiting a decision")
        if ticket.outcome.get("proposal_id") != str(decision.proposal_id):
            raise HTTPException(409, "Decision must refer to the current proposal")
        ticket.decision = recorded
        ticket.status = "queued"
        ticket.attempts = 0
        ticket.available_at = datetime.now(UTC)
        ticket.record("approved" if decision.approved else "rejected_by_operator")
        return TicketView.model_validate(ticket)
