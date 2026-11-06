from typing import Self

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    database_url: SecretStr
    demo_customer_tokens: dict[str, SecretStr] = Field(default_factory=dict)
    demo_operator_token: SecretStr | None = None
    n8n_completion_token: SecretStr | None = None
    foundry_enabled: bool = False
    foundry_endpoint: AnyHttpUrl | None = None
    foundry_api_key: SecretStr | None = None
    foundry_chat_deployment: str | None = None
    foundry_embedding_deployment: str | None = Field(default=None, max_length=80)
    foundry_max_completion_tokens: int = Field(default=300, ge=64, le=1000)
    supportops_langsmith_enabled: bool = False
    supportops_langsmith_api_key: SecretStr | None = None
    supportops_langsmith_project: str = "supportops-ai"

    @model_validator(mode="after")
    def validate_providers(self) -> Self:
        if self.foundry_enabled:
            if not (
                self.foundry_endpoint and self.foundry_api_key and self.foundry_chat_deployment
            ):
                raise ValueError("Foundry requires an endpoint, API key and chat deployment")
            endpoint = self.foundry_endpoint
            host = endpoint.host or ""
            if (
                endpoint.scheme != "https"
                or not host.endswith((".openai.azure.com", ".services.ai.azure.com"))
                or (endpoint.path or "").rstrip("/") != "/openai/v1"
                or endpoint.query
                or endpoint.fragment
                or endpoint.username
                or endpoint.password
            ):
                raise ValueError("Use an HTTPS Azure Foundry /openai/v1 endpoint")
        if self.supportops_langsmith_enabled and not self.supportops_langsmith_api_key:
            raise ValueError("LangSmith requires a tracing API key")
        return self
