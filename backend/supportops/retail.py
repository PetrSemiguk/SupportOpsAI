from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import ForeignKey, String, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

OrderStatus = Literal["pending", "processed", "delivered", "cancelled", "return requested"]


class RetailBase(DeclarativeBase):
    pass


class Customer(RetailBase):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)


class Order(RetailBase):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    status: Mapped[str] = mapped_column(String(24))
    items: Mapped[list[dict[str, str]]] = mapped_column(JSONB)
    tracking_ids: Mapped[list[str]] = mapped_column(JSONB)
    payment_sources: Mapped[list[str]] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(default=0, server_default="0")


class OrderAction(RetailBase):
    __tablename__ = "order_actions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"))
    request: Mapped[dict[str, object]] = mapped_column(JSONB)
    result: Mapped[dict[str, object]] = mapped_column(JSONB)


class OrderItem(BaseModel):
    id: str
    name: str
    price: Decimal


class OrderDetails(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: OrderStatus
    items: list[OrderItem]
    tracking_ids: list[str]
    version: int


class Cancellation(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["cancel"] = "cancel"
    reason: Literal["no longer needed", "ordered by mistake"]


class ReturnRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["return"] = "return"
    item_ids: tuple[str, ...] = Field(min_length=1)
    refund_destination: Literal["original payment"] = "original payment"


class ProposedAction(BaseModel):
    model_config = ConfigDict(frozen=True)

    order_id: str
    customer_id: str
    order_version: int = Field(ge=0)
    action: Annotated[Cancellation | ReturnRequest, Field(discriminator="kind")]


class ActionResult(BaseModel):
    action_id: UUID
    order: OrderDetails


class OrderNotFound(Exception):
    """The order is missing or belongs to a different customer."""


class ActionConflict(Exception):
    """The action is stale, ineligible or conflicts with a previous request."""


def customer_orders(session: Session, customer_id: str) -> list[OrderDetails]:
    query = select(Order).where(Order.customer_id == customer_id).order_by(Order.id)
    return [OrderDetails.model_validate(order) for order in session.scalars(query)]


def customer_order(session: Session, customer_id: str, order_id: str) -> OrderDetails:
    order = session.scalar(
        select(Order).where(Order.id == order_id, Order.customer_id == customer_id)
    )
    if order is None:
        raise OrderNotFound
    return OrderDetails.model_validate(order)


def validate_action(order: OrderDetails, proposal: ProposedAction) -> OrderStatus:
    """Evaluate the deterministic subset of the demo shop's cancellation and return policy."""
    if order.version != proposal.order_version or order.id != proposal.order_id:
        raise ActionConflict("The order changed after the action was proposed")
    if isinstance(proposal.action, Cancellation):
        if order.status != "pending":
            raise ActionConflict("Only pending orders can be cancelled")
        return "cancelled"
    if order.status != "delivered":
        raise ActionConflict("Only delivered orders can be returned")
    requested = proposal.action.item_ids
    available = {item.id for item in order.items}
    if len(set(requested)) != len(requested) or not set(requested).issubset(available):
        raise ActionConflict("Return items must be unique and belong to the order")
    return "return requested"


def execute_approved_action(
    session: Session, action_id: UUID, proposal: ProposedAction
) -> ActionResult:
    """Apply a caller-verified approval in the same transaction as its durable result."""
    order = session.scalar(
        select(Order)
        .where(Order.id == proposal.order_id, Order.customer_id == proposal.customer_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if order is None:
        raise OrderNotFound

    request = proposal.model_dump(mode="json")
    previous = session.get(OrderAction, action_id)
    if previous is not None:
        if previous.request != request:
            raise ActionConflict("The action identifier belongs to a different request")
        return ActionResult.model_validate(previous.result)

    current = OrderDetails.model_validate(order)
    status = validate_action(current, proposal)
    if isinstance(proposal.action, ReturnRequest) and not order.payment_sources:
        raise ActionConflict("The original payment source could not be verified")
    result = ActionResult(
        action_id=action_id,
        order=current.model_copy(update={"status": status, "version": order.version + 1}),
    )
    claimed = session.scalar(
        insert(OrderAction)
        .values(
            id=action_id, order_id=order.id, request=request, result=result.model_dump(mode="json")
        )
        .on_conflict_do_nothing(index_elements=[OrderAction.id])
        .returning(OrderAction.id)
    )
    if claimed is None:
        # Same-order retries are serialized by the row lock. A conflicting insert
        # here can only be an identifier reused against a different order.
        raise ActionConflict("The action identifier belongs to a different request")
    order.status = status
    order.version += 1
    return result
