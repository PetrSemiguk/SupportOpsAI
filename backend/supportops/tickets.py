from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from supportops.policies import PolicyExcerpt
from supportops.retail import ActionResult, OrderDetails, ProposedAction, RetailBase

TicketStatus = Literal[
    "queued",
    "awaiting_approval",
    "needs_clarification",
    "completed",
    "rejected",
    "escalated",
    "failed",
]
Intent = Literal["status", "cancel", "return", "other"]
TERMINAL_STATUSES = frozenset({"completed", "rejected", "escalated", "failed"})


class TicketInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1500)]
    intent: Intent
    order_id: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)] | None
    ) = None
    cancellation_reason: Literal["no longer needed", "ordered by mistake"] | None = None
    item_ids: list[Annotated[str, StringConstraints(min_length=1, max_length=40)]] = Field(
        default_factory=list,
        max_length=50,
    )
    customer_confirmed: bool = False


class TicketCreate(TicketInput):
    request_id: UUID


class OperatorDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: UUID
    approved: bool


class TicketOutcome(BaseModel):
    status: TicketStatus
    response: str
    order: OrderDetails | None = None
    evidence: list[PolicyExcerpt] = Field(default_factory=list)
    proposal: ProposedAction | None = None
    proposal_id: UUID | None = None
    result: ActionResult | None = None


class HistoryEntry(BaseModel):
    at: datetime
    event: str


class Ticket(RetailBase):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("customer_id", "request_id", name="uq_ticket_customer_request"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"))
    request_id: Mapped[UUID]
    initial_input: Mapped[dict[str, object]] = mapped_column(JSONB)
    input: Mapped[dict[str, object]] = mapped_column(JSONB)
    run_id: Mapped[UUID] = mapped_column(default=uuid4)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    outcome: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    decision: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    history: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)

    def record(self, event: str) -> None:
        entry = HistoryEntry(at=datetime.now(UTC), event=event).model_dump(mode="json")
        self.history = [*(self.history or []), entry]


class CompletionEvent(RetailBase):
    """Durable event for later n8n delivery, written with the ticket projection."""

    __tablename__ = "completion_events"

    ticket_id: Mapped[UUID] = mapped_column(ForeignKey("tickets.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TicketView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: str
    status: TicketStatus
    input: TicketInput
    outcome: TicketOutcome | None
    decision: OperatorDecision | None
    history: list[HistoryEntry]
    created_at: datetime
