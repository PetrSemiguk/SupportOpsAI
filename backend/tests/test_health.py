import os

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from supportops.config import Settings
from supportops.main import create_app


def test_liveness_does_not_require_a_database() -> None:
    settings = Settings(database_url=SecretStr("postgresql+psycopg://demo:private@127.0.0.1:1/db"))
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unavailable_database_has_sanitized_readiness() -> None:
    settings = Settings(database_url=SecretStr("postgresql+psycopg://demo:private@127.0.0.1:1/db"))
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unavailable"}
    assert "private" not in response.text


@pytest.mark.integration
def test_postgres_schema_and_vector_extension_are_ready() -> None:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set TEST_DATABASE_URL to a migrated PostgreSQL database")
    with TestClient(create_app(Settings(database_url=SecretStr(database_url)))) as client:
        response = client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ready"}
