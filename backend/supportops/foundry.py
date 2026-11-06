import json
from hashlib import sha256
from math import isfinite
from typing import Annotated

import httpx
from langchain_core.embeddings import Embeddings
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from supportops.config import Settings

VECTOR_DIMENSIONS = 256


class FoundryError(Exception):
    """Provider is unavailable or returned an invalid result."""


class Draft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    citation: str


class _Embedding(BaseModel):
    index: int
    embedding: list[float] = Field(min_length=VECTOR_DIMENSIONS, max_length=VECTOR_DIMENSIONS)


class _EmbeddingResponse(BaseModel):
    data: list[_Embedding]


class FoundryClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        if (
            not settings.foundry_enabled
            or not settings.foundry_endpoint
            or not settings.foundry_api_key
        ):
            raise ValueError("Foundry must be explicitly configured and enabled")
        self.endpoint = str(settings.foundry_endpoint).rstrip("/")
        self.api_key = settings.foundry_api_key
        self.deployment = settings.foundry_chat_deployment
        self.max_tokens = settings.foundry_max_completion_tokens
        self.transport = transport

    def _post(self, route: str, payload: dict[str, object]) -> object:
        try:
            with httpx.Client(timeout=12, transport=self.transport) as client:
                response = client.post(
                    f"{self.endpoint}/{route}",
                    json=payload,
                    headers={"api-key": self.api_key.get_secret_value()},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as error:
            raise FoundryError(f"Foundry returned HTTP {error.response.status_code}") from None
        except (httpx.RequestError, ValueError):
            raise FoundryError("Foundry request or response failed") from None

    def draft(self, facts: dict[str, object], evidence: dict[str, str]) -> Draft:
        payload: dict[str, object] = {
            "model": self.deployment,
            "max_completion_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Write a short English draft using the supplied verified facts and policy. "
                        "Use one exact citation key from evidence. Never invent order details or "
                        "claim execution. Proposed actions await operator approval."
                    ),
                },
                {"role": "user", "content": json.dumps({"facts": facts, "evidence": evidence})},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "support_draft",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}, "citation": {"type": "string"}},
                        "required": ["text", "citation"],
                        "additionalProperties": False,
                    },
                },
            },
        }
        data = self._post("chat/completions", payload)
        try:
            if not isinstance(data, dict):
                raise TypeError
            result = Draft.model_validate_json(data["choices"][0]["message"]["content"])
        except (IndexError, KeyError, TypeError, ValidationError):
            raise FoundryError("Foundry returned an invalid support draft") from None
        if result.citation not in evidence:
            raise FoundryError("Foundry draft cited an unknown source")
        return result

    def embed(self, deployment: str, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        data = self._post(
            "embeddings",
            {
                "model": deployment,
                "input": texts,
                "dimensions": VECTOR_DIMENSIONS,
            },
        )
        try:
            result = sorted(
                _EmbeddingResponse.model_validate(data).data, key=lambda item: item.index
            )
        except ValidationError:
            raise FoundryError("Foundry returned invalid embedding dimensions") from None
        if [entry.index for entry in result] != list(range(len(texts))):
            raise FoundryError("Foundry returned an incomplete embedding batch")
        for entry in result:
            if not any(entry.embedding) or not all(isfinite(value) for value in entry.embedding):
                raise FoundryError("Foundry returned an invalid embedding vector")
        return [entry.embedding for entry in result]


class FoundryEmbeddings(Embeddings):
    def __init__(self, client: FoundryClient, deployment: str) -> None:
        self.client = client
        self.deployment = deployment
        key = f"{client.endpoint}\n{deployment}\n{VECTOR_DIMENSIONS}"
        self.model_id = "foundry-v1:" + sha256(key.encode()).hexdigest()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.client.embed(self.deployment, texts)

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
