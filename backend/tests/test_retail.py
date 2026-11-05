import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker
from supportops.config import Settings
from supportops.database import create_database_engine
from supportops.main import create_app
from supportops.retail import (
    ActionConflict,
    ActionResult,
    Cancellation,
    Customer,
    Order,
    OrderAction,
    OrderDetails,
    OrderItem,
    OrderNotFound,
    ProposedAction,
    ReturnRequest,
    execute_approved_action,
    validate_action,
)
from supportops.seed_retail import SourceStore, seed_orders


def test_cancellation_requires_supported_reason() -> None:
    with pytest.raises(ValidationError):
        Cancellation.model_validate({"reason": "delivery took too long"})


def test_ineligible_status_and_return_item() -> None:
    order = OrderDetails(
        id="order-1",
        status="delivered",
        version=0,
        tracking_ids=[],
        items=[OrderItem.model_validate({"id": "item-1", "name": "Mug", "price": "8.00"})],
    )
    with pytest.raises(ActionConflict, match="pending"):
        validate_action(
            order,
            ProposedAction(
                order_id=order.id,
                customer_id="a",
                order_version=0,
                action=Cancellation(reason="ordered by mistake"),
            ),
        )
    with pytest.raises(ActionConflict, match="belong"):
        validate_action(
            order,
            ProposedAction(
                order_id=order.id,
                customer_id="a",
                order_version=0,
                action=ReturnRequest(item_ids=("other-item",)),
            ),
        )


@pytest.fixture
def store() -> Iterator[tuple[sessionmaker[Session], Settings, str, str]]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated PostgreSQL database")
    identifier = uuid4().hex
    customer_id, order_id = f"t-{identifier}", f"o-{identifier}"
    settings = Settings(
        database_url=SecretStr(url),
        demo_customer_tokens={
            customer_id: SecretStr("owner-token"),
            "other": SecretStr("other-token"),
        },
    )
    engine = create_database_engine(settings)
    sessions = sessionmaker(engine)
    with sessions.begin() as session:
        session.add(Customer(id=customer_id))
        session.flush()
        session.add(
            Order(
                id=order_id,
                customer_id=customer_id,
                status="pending",
                items=[{"id": "item-1", "name": "Mug", "price": "8.00"}],
                tracking_ids=[],
                payment_sources=["credit_card"],
            )
        )
    try:
        yield sessions, settings, customer_id, order_id
    finally:
        with sessions.begin() as session:
            session.execute(delete(OrderAction).where(OrderAction.order_id == order_id))
            session.execute(delete(Order).where(Order.id == order_id))
            session.execute(delete(Customer).where(Customer.id == customer_id))
        engine.dispose()


@pytest.mark.integration
def test_order_api_enforces_customer_ownership(
    store: tuple[sessionmaker[Session], Settings, str, str],
) -> None:
    _, settings, _, order_id = store
    with TestClient(create_app(settings)) as client:
        assert client.get(f"/api/orders/{order_id}").status_code == 401
        assert (
            client.get(
                f"/api/orders/{order_id}", headers={"Authorization": "Bearer other-token"}
            ).status_code
            == 404
        )
        response = client.get(
            f"/api/orders/{order_id}", headers={"Authorization": "Bearer owner-token"}
        )
        assert response.status_code == 200
        assert response.json()["id"] == order_id
        assert response.json()["items"][0]["price"] == "8.00"
        assert "customer_id" not in response.json()


@pytest.mark.integration
def test_concurrent_replay_mutates_once(
    store: tuple[sessionmaker[Session], Settings, str, str],
) -> None:
    sessions, _, customer_id, order_id = store
    action_id = uuid4()
    proposal = ProposedAction(
        order_id=order_id,
        customer_id=customer_id,
        order_version=0,
        action=Cancellation(reason="no longer needed"),
    )

    def deliver() -> ActionResult:
        with sessions.begin() as session:
            return execute_approved_action(session, action_id, proposal)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = [executor.submit(deliver) for _ in range(2)]
        assert first.result(timeout=10) == second.result(timeout=10)
        assert first.result().order.status == "cancelled"

    with sessions.begin() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(OrderAction)
                .where(OrderAction.order_id == order_id)
            )
            == 1
        )
        order = session.get(Order, order_id)
        assert order is not None and order.version == 1
        with pytest.raises(ActionConflict, match="changed"):
            execute_approved_action(session, uuid4(), proposal)
        changed = proposal.model_copy(update={"action": Cancellation(reason="ordered by mistake")})
        with pytest.raises(ActionConflict, match="different request"):
            execute_approved_action(session, action_id, changed)
        wrong_customer = proposal.model_copy(update={"customer_id": "other"})
        with pytest.raises(OrderNotFound):
            execute_approved_action(session, action_id, wrong_customer)


@pytest.mark.integration
def test_return_and_result_rollback_together(
    store: tuple[sessionmaker[Session], Settings, str, str],
) -> None:
    sessions, _, customer_id, order_id = store
    with sessions.begin() as session:
        order = session.get(Order, order_id)
        assert order is not None
        order.status = "delivered"
    proposal = ProposedAction(
        order_id=order_id,
        customer_id=customer_id,
        order_version=0,
        action=ReturnRequest(item_ids=("item-1",)),
    )
    action_id = uuid4()
    with sessions() as session:
        assert (
            execute_approved_action(session, action_id, proposal).order.status == "return requested"
        )
        session.rollback()
    with sessions.begin() as session:
        assert session.get(OrderAction, action_id) is None
        result = execute_approved_action(session, action_id, proposal)
        assert result.order.status == "return requested"
        assert result.order.version == 1


@pytest.mark.integration
def test_seed_preserves_existing_order_state(
    store: tuple[sessionmaker[Session], Settings, str, str],
) -> None:
    sessions, _, customer_id, order_id = store
    source = SourceStore.model_validate(
        {
            "orders": {
                order_id: {
                    "order_id": order_id,
                    "user_id": "source-user",
                    "status": "pending",
                    "items": [],
                    "fulfillments": [],
                    "payment_history": [],
                }
            }
        }
    )
    with sessions() as session:
        order = session.get(Order, order_id)
        assert order is not None
        order.status = "cancelled"
        session.flush()
        assert seed_orders(session, source).inserted_orders == 0
        session.refresh(order)
        assert order.status == "cancelled" and order.customer_id == customer_id
        session.rollback()
