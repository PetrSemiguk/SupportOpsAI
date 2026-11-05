from datetime import UTC, datetime
from hmac import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from supportops.auth import bearer
from supportops.config import Settings
from supportops.orders_api import DatabaseSession
from supportops.tickets import CompletionEvent


def require_completion_token(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    settings: Settings = request.app.state.settings
    configured = settings.n8n_completion_token
    if configured and credentials:
        expected = configured.get_secret_value().encode()
        if expected and compare_digest(credentials.credentials.encode(), expected):
            return
    raise HTTPException(401, "A valid completion token is required", {"WWW-Authenticate": "Bearer"})


class CompletionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: UUID
    status: str
    created_at: datetime
    delivered_at: datetime | None


class CompletionBatch(BaseModel):
    events: list[CompletionView]


router = APIRouter(
    prefix="/api/integrations/completions",
    tags=["n8n integration"],
    dependencies=[Depends(require_completion_token)],
)


@router.get("")
def pending_completions(
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> CompletionBatch:
    query = (
        select(CompletionEvent)
        .where(CompletionEvent.delivered_at.is_(None))
        .order_by(CompletionEvent.created_at, CompletionEvent.ticket_id)
        .limit(limit)
    )
    return CompletionBatch(
        events=[CompletionView.model_validate(event) for event in session.scalars(query)]
    )


@router.post("/{ticket_id}/ack")
def acknowledge_completion(ticket_id: UUID, session: DatabaseSession) -> CompletionView:
    with session.begin():
        event = session.scalar(
            select(CompletionEvent).where(CompletionEvent.ticket_id == ticket_id).with_for_update()
        )
        if event is None:
            raise HTTPException(404, "Completion event not found")
        if event.delivered_at is None:
            event.delivered_at = datetime.now(UTC)
        return CompletionView.model_validate(event)
