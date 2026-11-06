import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import AnyHttpUrl, SecretStr
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.orm import Session
from supportops import worker
from supportops.config import Settings
from supportops.database import create_database_engine
from supportops.foundry import Draft, FoundryClient
from supportops.main import create_app
from supportops.policies import index_policy
from supportops.retail import Customer, Order, OrderAction
from supportops.tickets import CompletionEvent, Ticket

CUSTOMER = {"Authorization": "Bearer customer-test-token"}
OPERATOR = {"Authorization": "Bearer operator-test-token"}
OTHER = {"Authorization": "Bearer other-test-token"}
AUTOMATION = {"Authorization": "Bearer completion-test-token"}
pytestmark = pytest.mark.integration


@dataclass
class Demo:
    client: TestClient
    engine: Engine
    settings: Settings
    order_id: str

    def submit(self, **overrides: object) -> dict[str, Any]:
        payload = {
            "request_id": str(uuid4()),
            "message": "I ordered by mistake. Please cancel.",
            "intent": "cancel",
            "order_id": self.order_id,
            "cancellation_reason": "ordered by mistake",
            "customer_confirmed": True,
            **overrides,
        }
        response = self.client.post("/api/tickets", json=payload, headers=CUSTOMER)
        assert response.status_code == 202, response.text
        return response.json()

    def ticket(self, ticket_id: str) -> dict[str, Any]:
        response = self.client.get(f"/api/tickets/{ticket_id}", headers=CUSTOMER)
        assert response.status_code == 200, response.text
        return response.json()

    def step(self) -> bool:
        return worker.process_one(self.engine, self.settings)


@pytest.fixture
def demo() -> Iterator[Demo]:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated test PostgreSQL database")
    identifier = uuid4().hex
    customer_id = f"t-{identifier}"
    order_id = f"o-{identifier}"
    settings = Settings(
        database_url=SecretStr(database_url),
        demo_customer_tokens={
            customer_id: SecretStr("customer-test-token"),
            "other": SecretStr("other-test-token"),
        },
        demo_operator_token=SecretStr("operator-test-token"),
        n8n_completion_token=SecretStr("completion-test-token"),
    )
    engine = create_database_engine(settings)
    with Session(engine) as session, session.begin():
        index_policy(session)
        session.add(Customer(id=customer_id))
        session.flush()
        session.add(
            Order(
                id=order_id,
                customer_id=customer_id,
                status="pending",
                items=[{"id": "item-1", "name": "Mug", "price": "8.00"}],
                tracking_ids=["track-123"],
                payment_sources=["credit_card"],
            )
        )
    try:
        with TestClient(create_app(settings)) as client:
            yield Demo(client, engine, settings, order_id)
    finally:
        with Session(engine) as session, session.begin():
            query = select(Ticket.id).where(Ticket.customer_id == customer_id)
            runs = list(
                session.scalars(select(Ticket.run_id).where(Ticket.customer_id == customer_id))
            )
            session.execute(delete(CompletionEvent).where(CompletionEvent.ticket_id.in_(query)))
            session.execute(delete(Ticket).where(Ticket.customer_id == customer_id))
            session.execute(delete(OrderAction).where(OrderAction.order_id == order_id))
            session.execute(delete(Order).where(Order.id == order_id))
            session.execute(delete(Customer).where(Customer.id == customer_id))
        with worker.open_checkpointer(settings) as checkpointer:
            for run_id in runs:
                checkpointer.delete_thread(str(run_id))
        engine.dispose()


def test_status_intake_replay_and_isolation(demo: Demo) -> None:
    request_id = str(uuid4())
    submitted = demo.submit(request_id=request_id, intent="status")
    ticket_id = submitted["id"]
    assert demo.submit(request_id=request_id, intent="status")["id"] == ticket_id
    assert demo.client.get(f"/api/tickets/{ticket_id}", headers=OTHER).status_code == 404
    assert demo.client.get("/api/tickets", headers=CUSTOMER).status_code == 401
    assert demo.step()
    outcome = demo.ticket(ticket_id)["outcome"]
    assert outcome["status"] == "completed"
    assert "track-123" in outcome["response"]
    assert outcome["evidence"][0]["citation"].endswith("#order-access")
    assert not demo.step()


def test_hosted_draft_is_operator_only(demo: Demo, monkeypatch: pytest.MonkeyPatch) -> None:
    demo.settings = Settings(
        database_url=demo.settings.database_url,
        foundry_enabled=True,
        foundry_endpoint=AnyHttpUrl("https://example.openai.azure.com/openai/v1"),
        foundry_api_key=SecretStr("test-foundry-key"),
        foundry_chat_deployment="chat-test",
        foundry_embedding_deployment=None,
        supportops_langsmith_enabled=False,
    )
    calls: list[dict[str, object]] = []

    def draft(_client: FoundryClient, facts: dict[str, object], evidence: dict[str, str]) -> Draft:
        calls.append(facts)
        citation = "data/policies/retail.md#cancellation"
        assert citation in evidence
        return Draft(text="The action awaits operator approval.", citation=citation)

    monkeypatch.setattr(FoundryClient, "draft", draft)
    unconfirmed = demo.submit(customer_confirmed=False)["id"]
    assert demo.step()
    assert demo.ticket(unconfirmed)["status"] == "needs_clarification"
    assert calls == []

    ticket_id = demo.submit(message="Private customer message")["id"]
    assert demo.step()
    customer = demo.ticket(ticket_id)
    assert customer["status"] == "awaiting_approval"
    assert customer["outcome"]["draft"] is None
    response = demo.client.get(f"/api/tickets/{ticket_id}/operator", headers=OPERATOR)
    assert response.status_code == 200, response.text
    assert response.json()["outcome"]["draft"]["citation"].endswith("#cancellation")
    assert calls == [
        {"intent": "cancel", "order_status": "pending", "workflow_status": "awaiting_approval"}
    ]
    decision = {"approved": False, "proposal_id": customer["outcome"]["proposal_id"]}
    response = demo.client.post(
        f"/api/tickets/{ticket_id}/decision", json=decision, headers=OPERATOR
    )
    assert response.status_code == 202, response.text
    assert demo.step()
    response = demo.client.get(f"/api/tickets/{ticket_id}/operator", headers=OPERATOR)
    assert response.json()["status"] == "rejected"
    assert response.json()["outcome"]["draft"] is None


def test_approval_survives_restart_and_projection_crash(
    demo: Demo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticket_id = demo.submit()["id"]
    assert demo.step()
    waiting = demo.ticket(ticket_id)
    assert waiting["status"] == "awaiting_approval", waiting
    assert not demo.step()
    decision = {"approved": True, "proposal_id": waiting["outcome"]["proposal_id"]}
    endpoint = f"/api/tickets/{ticket_id}/decision"
    assert demo.client.post(endpoint, json=decision, headers=CUSTOMER).status_code == 401
    assert (
        demo.client.post(
            endpoint, json={**decision, "proposal_id": str(uuid4())}, headers=OPERATOR
        ).status_code
        == 409
    )
    assert demo.client.post(endpoint, json=decision, headers=OPERATOR).status_code == 202
    assert demo.client.post(endpoint, json=decision, headers=OPERATOR).status_code == 202

    def crash(*args: object) -> None:
        raise RuntimeError("Simulated process loss after graph checkpoint")

    # The checkout uses a fresh PostgreSQL checkpointer connection on each call.
    # The injected crash rolls back only the projection, after the action committed.
    with monkeypatch.context() as patch:
        patch.setattr(worker, "project_outcome", crash)
        with pytest.raises(RuntimeError, match="process loss"):
            demo.step()
    assert demo.ticket(ticket_id)["status"] == "queued"
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [executor.submit(demo.step) for _ in range(2)]
        assert sorted(result.result(timeout=20) for result in results) == [False, True]
    finished = demo.ticket(ticket_id)
    assert finished["status"] == "completed"
    assert finished["outcome"]["result"]["order"]["status"] == "cancelled"
    with Session(demo.engine) as session:
        actions = (
            select(func.count())
            .select_from(OrderAction)
            .where(
                OrderAction.order_id == demo.order_id,
            )
        )
        assert session.scalar(actions) == 1
        assert session.get(CompletionEvent, UUID(ticket_id)) is not None


@pytest.mark.parametrize("approve", [True, False])
def test_return_rejects_or_escalates_stale_approval(demo: Demo, approve: bool) -> None:
    with Session(demo.engine) as session, session.begin():
        order = session.get(Order, demo.order_id)
        assert order is not None
        order.status = "delivered"
    ticket_id = demo.submit(intent="return", item_ids=["item-1"])["id"]
    assert demo.step()
    waiting = demo.ticket(ticket_id)
    assert waiting["status"] == "awaiting_approval", waiting
    with Session(demo.engine) as session, session.begin():
        order = session.get(Order, demo.order_id)
        assert order is not None
        order.version += 1
    response = demo.client.post(
        f"/api/tickets/{ticket_id}/decision",
        headers=OPERATOR,
        json={"proposal_id": waiting["outcome"]["proposal_id"], "approved": approve},
    )
    assert response.status_code == 202, response.text
    assert demo.step()
    assert demo.ticket(ticket_id)["status"] == ("escalated" if approve else "rejected")
    with Session(demo.engine) as session:
        order = session.get(Order, demo.order_id)
        assert order is not None and order.status == "delivered"


def test_missing_order_clarification_requeues(demo: Demo) -> None:
    ticket_id = demo.submit(intent="status", order_id=None)["id"]
    assert demo.step()
    assert demo.ticket(ticket_id)["status"] == "needs_clarification"
    with Session(demo.engine) as session:
        ticket = session.get(Ticket, UUID(ticket_id))
        assert ticket is not None
        prior_run = ticket.run_id
    response = demo.client.post(
        f"/api/tickets/{ticket_id}/clarification",
        headers=CUSTOMER,
        json={"message": "Where is my order?", "intent": "status", "order_id": demo.order_id},
    )
    assert response.status_code == 202
    assert demo.step()
    assert demo.ticket(ticket_id)["status"] == "completed"
    with worker.open_checkpointer(demo.settings) as checkpointer:
        checkpointer.delete_thread(str(prior_run))


def test_approved_return_preserves_original_payment_route(demo: Demo) -> None:
    with Session(demo.engine) as session, session.begin():
        order = session.get(Order, demo.order_id)
        assert order is not None
        order.status = "delivered"
    ticket_id = demo.submit(intent="return", item_ids=["item-1"])["id"]
    assert demo.step()
    waiting = demo.ticket(ticket_id)
    proposal = waiting["outcome"]["proposal"]
    assert proposal["action"]["refund_destination"] == "original payment"
    response = demo.client.post(
        f"/api/tickets/{ticket_id}/decision",
        headers=OPERATOR,
        json={"proposal_id": waiting["outcome"]["proposal_id"], "approved": True},
    )
    assert response.status_code == 202
    assert demo.step()
    outcome = demo.ticket(ticket_id)["outcome"]
    assert outcome["status"] == "completed"
    assert outcome["result"]["order"]["status"] == "return requested"


def test_checkpoint_failure_preserves_committed_action(
    demo: Demo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticket_id = demo.submit()["id"]
    assert demo.step()
    waiting = demo.ticket(ticket_id)
    response = demo.client.post(
        f"/api/tickets/{ticket_id}/decision",
        headers=OPERATOR,
        json={"proposal_id": waiting["outcome"]["proposal_id"], "approved": True},
    )
    assert response.status_code == 202
    run_ticket = worker.run_ticket

    def lost_checkpoint_response(*args: Any) -> None:
        run_ticket(*args)
        raise ConnectionError("Checkpoint acknowledgement lost")

    monkeypatch.setattr(worker, "run_ticket", lost_checkpoint_response)
    for _ in range(worker.MAX_ATTEMPTS):
        assert demo.step()
        with Session(demo.engine) as session, session.begin():
            ticket = session.get(Ticket, UUID(ticket_id))
            assert ticket is not None
            ticket.available_at = datetime.now(UTC)
    finished = demo.ticket(ticket_id)
    assert finished["status"] == "completed"
    assert finished["outcome"]["result"]["order"]["version"] == 1


def test_completion_feed_is_scoped_and_acknowledgement_is_idempotent(demo: Demo) -> None:
    ticket_id = demo.submit(intent="status")["id"]
    assert demo.step()
    feed = "/api/integrations/completions"
    endpoint = f"{feed}/{ticket_id}/ack"
    assert demo.client.get(feed).status_code == 401
    assert demo.client.get(feed, headers=OPERATOR).status_code == 401
    assert demo.client.post(endpoint, headers=CUSTOMER).status_code == 401
    events = demo.client.get(feed, headers=AUTOMATION).json()["events"]
    event = next(entry for entry in events if entry["ticket_id"] == ticket_id)
    assert set(event) == {"ticket_id", "status", "created_at", "delivered_at"}
    assert event["delivered_at"] is None

    def deliver() -> dict[str, Any]:
        response = demo.client.post(endpoint, headers=AUTOMATION)
        assert response.status_code == 200
        return response.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = [executor.submit(deliver) for _ in range(2)]
        receipt = first.result(timeout=15)
        assert receipt == second.result(timeout=15)
    assert receipt["delivered_at"] is not None
    assert all(
        entry["ticket_id"] != ticket_id
        for entry in demo.client.get(feed, headers=AUTOMATION).json()["events"]
    )
    assert demo.client.post(f"{feed}/{uuid4()}/ack", headers=AUTOMATION).status_code == 404


def test_transient_tool_failure_retries_are_bounded(
    demo: Demo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(*args: object) -> None:
        raise ConnectionError("test tool is offline")

    monkeypatch.setattr(worker, "run_ticket", unavailable)
    ticket_id = demo.submit()["id"]
    for attempt in range(worker.MAX_ATTEMPTS):
        assert demo.step()
        with Session(demo.engine) as session, session.begin():
            ticket = session.get(Ticket, UUID(ticket_id))
            assert ticket is not None and ticket.attempts == attempt + 1
            ticket.available_at = datetime.now(UTC)
    failed = demo.ticket(ticket_id)
    assert failed["status"] == "failed"
    assert sum(entry["event"] == "retry_scheduled" for entry in failed["history"]) == 2
    assert not demo.step()
