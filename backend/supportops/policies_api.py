from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from supportops.auth import database_session
from supportops.policies import PolicySearchResult, search_policies

router = APIRouter(prefix="/api/policies", tags=["Policies"])


@router.get("/search")
def search(
    q: Annotated[str, Query(min_length=1, max_length=500)],
    session: Annotated[Session, Depends(database_session)],
) -> PolicySearchResult:
    return search_policies(session, q)
