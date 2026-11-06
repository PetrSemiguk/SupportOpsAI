import argparse
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from time import sleep

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from sqlalchemy import Engine, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from supportops.config import Settings
from supportops.database import create_database_engine
from supportops.retail import ActionResult, OrderAction
from supportops.tickets import (
    TERMINAL_STATUSES,
    CompletionEvent,
    OperatorDecision,
    Ticket,
    TicketOutcome,
)
from supportops.workflow import run_ticket

LOGGER = logging.getLogger(__name__)
MAX_ATTEMPTS = 3


@contextmanager
def open_checkpointer(settings: Settings) -> Iterator[PostgresSaver]:
    uri = make_url(settings.database_url.get_secret_value()).set(drivername="postgresql")
    with psycopg.connect(
        uri.render_as_string(hide_password=False),
        autocommit=True,
        row_factory=dict_row,
        options="-c search_path=supportops_graph",
        connect_timeout=5,
        prepare_threshold=0,
    ) as connection:
        yield PostgresSaver(connection)


def project_outcome(session: Session, ticket: Ticket, outcome: TicketOutcome) -> None:
    ticket.status = outcome.status
    ticket.outcome = outcome.model_dump(mode="json")
    ticket.record(outcome.status)
    if outcome.status in TERMINAL_STATUSES:
        session.execute(
            insert(CompletionEvent)
            .values(
                ticket_id=ticket.id,
                status=outcome.status,
            )
            .on_conflict_do_nothing(index_elements=[CompletionEvent.ticket_id])
        )


def failed_outcome(session: Session, ticket: Ticket, message: str) -> TicketOutcome:
    outcome = (
        TicketOutcome.model_validate(ticket.outcome)
        if ticket.outcome is not None
        else TicketOutcome(status="failed", response=message)
    )
    outcome.status = "failed"
    outcome.response = message
    if ticket.decision is None or outcome.proposal is None:
        return outcome
    decision = OperatorDecision.model_validate(ticket.decision)
    if not decision.approved or decision.proposal_id != outcome.proposal_id:
        return outcome
    # An order mutation can commit before its final graph checkpoint is written.
    applied = session.get(OrderAction, decision.proposal_id)
    if applied is not None and applied.request == outcome.proposal.model_dump(mode="json"):
        result = ActionResult.model_validate(applied.result)
        outcome.status = "completed"
        outcome.response = f"Order {result.order.id} is now {result.order.status}."
        outcome.result = result
        outcome.order = result.order
    return outcome


def process_one(engine: Engine, settings: Settings) -> bool:
    with Session(engine) as session, session.begin():
        # The lock serializes one ticket across workers. A crashed worker releases
        # it and the next worker reconciles against the persisted graph checkpoint.
        ticket = session.scalar(
            select(Ticket)
            .where(
                Ticket.status == "queued",
                Ticket.available_at <= func.now(),
            )
            .order_by(Ticket.available_at, Ticket.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if ticket is None:
            return False
        ticket.attempts += 1
        try:
            with open_checkpointer(settings) as checkpointer:
                outcome = run_ticket(engine, checkpointer, ticket, settings)
        except (OperationalError, psycopg.OperationalError, ConnectionError) as error:
            LOGGER.warning("Transient ticket failure %s (%s)", ticket.id, type(error).__name__)
            if ticket.attempts < MAX_ATTEMPTS:
                ticket.available_at = datetime.now(UTC) + timedelta(seconds=2**ticket.attempts)
                ticket.record("retry_scheduled")
                return True
            outcome = failed_outcome(session, ticket, "Processing failed after three attempts.")
        except Exception as error:
            LOGGER.error("Ticket processing failed %s (%s)", ticket.id, type(error).__name__)
            outcome = failed_outcome(
                session, ticket, "Processing failed. Operator review is required."
            )
        project_outcome(session, ticket, outcome)
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the durable SupportOps ticket worker")
    parser.add_argument("--setup", action="store_true", help="Install checkpoint tables and exit")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    engine = create_database_engine(settings)
    try:
        if args.setup:
            with open_checkpointer(settings) as checkpointer:
                checkpointer.setup()
            return
        while True:
            if not process_one(engine, settings):
                sleep(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
