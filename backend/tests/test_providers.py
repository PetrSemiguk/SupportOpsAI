import json
from typing import Any

import httpx
import pytest
from langsmith.run_trees import RunTree
from pydantic import AnyHttpUrl, SecretStr
from supportops import observability
from supportops.config import Settings
from supportops.foundry import VECTOR_DIMENSIONS, FoundryClient, FoundryEmbeddings, FoundryError

CITATION = "data/policies/retail.md#cancellation"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url=SecretStr("unused"),
        foundry_enabled=True,
        foundry_endpoint=AnyHttpUrl("https://example.openai.azure.com/openai/v1"),
        foundry_api_key=SecretStr("test-foundry-key"),
        foundry_chat_deployment="chat-test",
        supportops_langsmith_enabled=False,
    )


@pytest.mark.parametrize("citation", [CITATION, "invented-policy"])
def test_foundry_checks_draft_citations(settings: Settings, citation: str) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/openai/v1/chat/completions"
        assert request.headers["api-key"] == "test-foundry-key"
        body = json.loads(request.content)
        assert body["model"] == "chat-test"
        assert body["response_format"]["json_schema"]["strict"] is True
        assert json.loads(body["messages"][1]["content"]) == {
            "facts": {"intent": "cancel"},
            "evidence": {CITATION: "Only pending orders can be cancelled."},
        }
        draft = json.dumps({"text": "This request awaits review.", "citation": citation})
        return httpx.Response(200, json={"choices": [{"message": {"content": draft}}]})

    client = FoundryClient(settings, httpx.MockTransport(respond))
    evidence = {CITATION: "Only pending orders can be cancelled."}
    if citation == CITATION:
        assert client.draft({"intent": "cancel"}, evidence).citation == citation
    else:
        with pytest.raises(FoundryError, match="unknown source"):
            client.draft({"intent": "cancel"}, evidence)


@pytest.mark.parametrize("size", [VECTOR_DIMENSIONS, 1])
def test_foundry_embedding_batch(settings: Settings, size: int) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/openai/v1/embeddings"
        assert json.loads(request.content) == {
            "model": "embedding-test",
            "input": ["first", "second"],
            "dimensions": VECTOR_DIMENSIONS,
        }
        return httpx.Response(
            200, json={"data": [{"index": i, "embedding": [i + 1.0] * size} for i in (1, 0)]}
        )

    client = FoundryClient(settings, httpx.MockTransport(respond))
    embeddings = FoundryEmbeddings(client, "embedding-test")
    if size == VECTOR_DIMENSIONS:
        assert embeddings.embed_documents(["first", "second"]) == [[1.0] * size, [2.0] * size]
    else:
        with pytest.raises(FoundryError, match="dimensions"):
            embeddings.embed_documents(["first", "second"])


def test_foundry_error_excludes_response_body(settings: Settings) -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(429, text="private provider details"))
    with pytest.raises(FoundryError, match="^Foundry returned HTTP 429$"):
        FoundryClient(settings, transport).draft({}, {})


def test_trace_only_publishes_allowlisted_fields(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    posted: list[dict[str, Any]] = []
    monkeypatch.setattr(RunTree, "post", lambda run: posted.append(run.model_dump()))
    monkeypatch.setattr(observability.Client, "flush", lambda _: None)

    def order_agent(message: str) -> str:
        return message

    disabled = observability.WorkflowTrace(settings)
    assert disabled.node(order_agent) is order_agent
    disabled.publish("completed")
    assert posted == []

    enabled = settings.model_copy(
        update={
            "supportops_langsmith_enabled": True,
            "supportops_langsmith_api_key": SecretStr("test-trace-key"),
        }
    )
    trace = observability.WorkflowTrace(enabled)
    assert trace.node(order_agent)("private customer text") == "private customer text"
    trace.publish("completed")
    assert [run["name"] for run in posted] == ["SupportOps ticket workflow", "order_agent"]
    assert [run["inputs"] for run in posted] == [{}, {}]
    assert [run["outputs"] for run in posted] == [{"status": "completed"}, {"status": "ok"}]
    assert "private customer text" not in repr(posted)
    assert "test-trace-key" not in repr(posted)
