from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from supportops.auth import customer_identity, database_session
from supportops.retail import OrderDetails, OrderNotFound, customer_order, customer_orders

router = APIRouter(prefix="/api/orders", tags=["Orders"])
CustomerIdentity = Annotated[str, Depends(customer_identity)]
DatabaseSession = Annotated[Session, Depends(database_session)]


@router.get("")
def list_orders(customer_id: CustomerIdentity, session: DatabaseSession) -> list[OrderDetails]:
    return customer_orders(session, customer_id)


@router.get("/{order_id}")
def get_order(
    order_id: str, customer_id: CustomerIdentity, session: DatabaseSession
) -> OrderDetails:
    try:
        return customer_order(session, customer_id, order_id)
    except OrderNotFound:
        raise HTTPException(404, "Order not found") from None
