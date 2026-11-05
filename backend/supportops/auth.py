from collections.abc import Iterator
from hmac import compare_digest
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from supportops.config import Settings

bearer = HTTPBearer(auto_error=False)


def customer_identity(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    settings: Settings = request.app.state.settings
    if credentials is not None:
        presented = credentials.credentials.encode()
        for customer_id, token in settings.demo_customer_tokens.items():
            expected = token.get_secret_value().encode()
            if expected and compare_digest(presented, expected):
                return customer_id
    raise HTTPException(
        401, "A valid demo customer token is required", {"WWW-Authenticate": "Bearer"}
    )


def database_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


def require_operator(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    settings: Settings = request.app.state.settings
    operator_token = settings.demo_operator_token
    if credentials is not None and operator_token is not None:
        presented = credentials.credentials.encode()
        expected = operator_token.get_secret_value().encode()
        if expected and compare_digest(presented, expected):
            # A mistakenly reused customer credential must not grant approval privileges.
            if not any(
                compare_digest(presented, token.get_secret_value().encode())
                for token in settings.demo_customer_tokens.values()
            ):
                return
    raise HTTPException(401, "A valid operator token is required", {"WWW-Authenticate": "Bearer"})
