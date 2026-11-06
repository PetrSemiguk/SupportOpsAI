import argparse
import json
import os
from math import ceil
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Literal
from uuid import uuid4

from langgraph.checkpoint.postgres import PostgresSaver
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from supportops.config import Settings
from supportops.database import create_database_engine
from supportops.policies import index_policy
from supportops.retail import Customer, Order, OrderAction, OrderStatus
from supportops.tickets import Intent, OperatorDecision, Ticket, TicketInput, TicketStatus
from supportops.worker import open_checkpointer
from supportops.workflow import run_ticket

CASES = Path("data/evaluation/cases_v1.jsonl")


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    message: str
    intent: Intent
    order_status: OrderStatus
    include_order: bool = True
    confirmed: bool = False
    reason: Literal["no longer needed", "ordered by mistake"] | None = None
    item_ids: list[str] = Field(default_factory=list)
    approval: Literal["approve", "reject", "stale"] | None = None
    expected_status: TicketStatus
    expected_proposal: Literal["cancel", "return"] | None = None
    expected_mutation: OrderStatus | None = None
    expected_citation: str | None


class Result(BaseModel):
    id: str
    passed: bool
    status: TicketStatus
    proposal: str | None
    final_order_status: str
    actions_written: int
    citations: list[str]
    expected_citation: str | None
    citation_matched: bool
    policy_violation: bool
    duration_ms: float


def evaluate_case(engine: Engine, checkpointer: PostgresSaver, case: Case) -> Result:
    order_id = uuid4().hex
    customer_id = uuid4().hex
    ticket = Ticket(
        id=uuid4(),
        run_id=uuid4(),
        customer_id=customer_id,
        input=TicketInput(
            message=case.message,
            intent=case.intent,
            order_id=order_id if case.include_order else None,
            customer_confirmed=case.confirmed,
            cancellation_reason=case.reason,
            item_ids=case.item_ids,
        ).model_dump(mode="json"),
        decision=None,
    )
    with Session(engine) as session, session.begin():
        session.add(Customer(id=customer_id))
        session.flush()
        session.add(
            Order(
                id=order_id,
                customer_id=customer_id,
                status=case.order_status,
                items=[
                    {"id": item_id, "name": f"Demo {item_id}", "price": "10.00"}
                    for item_id in ("item-1", "item-2")
                ],
                tracking_ids=["demo-tracking"],
                payment_sources=["demo-card"],
            )
        )

    try:
        started = perf_counter()
        outcome = run_ticket(engine, checkpointer, ticket)
        duration = perf_counter() - started
        with Session(engine) as session, session.begin():
            order = session.get_one(Order, order_id)
            early_write = order.version != 0 or order.status != case.order_status
            if case.approval == "stale":
                order.version += 1

        first_status = outcome.status
        if (
            case.approval is not None
            and first_status == "awaiting_approval"
            and outcome.proposal_id
        ):
            ticket.decision = OperatorDecision(
                proposal_id=outcome.proposal_id, approved=case.approval != "reject"
            ).model_dump(mode="json")
            started = perf_counter()
            outcome = run_ticket(engine, checkpointer, ticket)
            duration += perf_counter() - started

        with Session(engine) as session:
            order = session.get_one(Order, order_id)
            writes = (
                session.scalar(
                    select(func.count())
                    .select_from(OrderAction)
                    .where(OrderAction.order_id == order_id)
                )
                or 0
            )
        proposal = outcome.proposal.action.kind if outcome.proposal else None
        citations = [excerpt.citation for excerpt in outcome.evidence]
        cited = case.expected_citation in citations if case.expected_citation else not citations
        expected_writes = int(case.expected_mutation is not None)
        expected_version = expected_writes + int(case.approval == "stale")
        expected_order = case.expected_mutation or case.order_status
        violation = (
            early_write
            or writes > expected_writes
            or order.version > expected_version
            or (order.status != case.order_status and order.status != case.expected_mutation)
            or (proposal is not None and proposal != case.expected_proposal)
        )
        return Result(
            id=case.id,
            passed=(
                not violation
                and outcome.status == case.expected_status
                and (case.approval is None or first_status == "awaiting_approval")
                and proposal == case.expected_proposal
                and order.status == expected_order
                and order.version == expected_version
                and writes == expected_writes
                and cited
            ),
            status=outcome.status,
            proposal=proposal,
            final_order_status=order.status,
            actions_written=writes,
            citations=citations,
            expected_citation=case.expected_citation,
            citation_matched=cited,
            policy_violation=violation,
            duration_ms=round(duration * 1000, 2),
        )
    finally:
        with Session(engine) as session, session.begin():
            session.execute(delete(OrderAction).where(OrderAction.order_id == order_id))
            session.execute(delete(Order).where(Order.id == order_id))
            session.execute(delete(Customer).where(Customer.id == customer_id))
        checkpointer.delete_thread(str(ticket.run_id))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SupportOps offline workflow evaluations")
    parser.add_argument("--output", type=Path, help="Write the full per-case JSON report")
    args = parser.parse_args()
    database_url = os.environ.get("EVAL_DATABASE_URL", "")
    if not database_url or not (make_url(database_url).database or "").endswith("_eval"):
        parser.error("Set EVAL_DATABASE_URL to a dedicated database with a name ending in _eval")
    settings = Settings(
        database_url=SecretStr(database_url),
        foundry_enabled=False,
        supportops_langsmith_enabled=False,
    )
    cases = [
        Case.model_validate_json(line)
        for line in CASES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(cases) < 50 or len({case.id for case in cases}) != len(cases):
        parser.error("Expected at least 50 uniquely identified cases")
    engine = create_database_engine(settings)
    try:
        with Session(engine) as session, session.begin():
            index_policy(session)
        with open_checkpointer(settings) as checkpointer:
            results = [evaluate_case(engine, checkpointer, case) for case in cases]
    finally:
        engine.dispose()

    durations = sorted(result.duration_ms for result in results)
    retrieval = [result for result in results if result.expected_citation is not None]
    passed = sum(result.passed for result in results)
    summary = {
        "dataset": CASES.as_posix(),
        "mode": "offline",
        "cases": len(results),
        "passed": passed,
        "policy_violations": sum(result.policy_violation for result in results),
        "expected_citations": len(retrieval),
        "citation_hits": sum(result.citation_matched for result in retrieval),
        "latency_ms_p50": round(median(durations), 2),
        "latency_ms_p95": durations[ceil(0.95 * len(durations)) - 1],
        "failed_ids": [result.id for result in results if not result.passed],
    }
    if args.output:
        report = {**summary, "results": [result.model_dump(mode="json") for result in results]}
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if passed != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
