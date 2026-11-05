import os
from collections.abc import Iterator

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from supportops.config import Settings
from supportops.database import create_database_engine
from supportops.policies import (
    OFFLINE_MODEL,
    POLICY_FILE,
    PolicySection,
    index_policy,
    search_policies,
)


@pytest.fixture
def policy_store() -> Iterator[Session]:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated PostgreSQL database")
    engine = create_database_engine(Settings(database_url=SecretStr(database_url)))
    try:
        with Session(engine) as session:
            index_policy(session)
            yield session
    finally:
        engine.dispose()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("query", "section_id"),
    [
        ("Can I cancel a pending order?", "cancellation"),
        ("Return delivered items to the original payment source", "return"),
        ("Track shipment references and status for my order", "order-access"),
    ],
)
def test_retrieval_returns_ranked_versioned_citations(
    policy_store: Session, query: str, section_id: str
) -> None:
    result = search_policies(policy_store, query)
    assert result.embedding_model == OFFLINE_MODEL
    assert result.excerpts[0].citation == f"{POLICY_FILE.as_posix()}#{section_id}"
    assert len(result.excerpts[0].revision) == 64
    assert result.excerpts[0].content


@pytest.mark.integration
@pytest.mark.parametrize("query", ["what is the", "quantum entanglement", "..."])
def test_retrieval_abstains_without_relevant_terms(policy_store: Session, query: str) -> None:
    assert search_policies(policy_store, query).excerpts == []


@pytest.mark.integration
def test_reindex_preserves_one_row_per_section(policy_store: Session) -> None:
    assert index_policy(policy_store) == 4
    count = policy_store.scalar(
        select(func.count())
        .select_from(PolicySection)
        .where(
            PolicySection.document == POLICY_FILE.as_posix(),
            PolicySection.model_id == OFFLINE_MODEL,
        )
    )
    assert count == 4
