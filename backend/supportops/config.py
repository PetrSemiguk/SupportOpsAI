from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    database_url: SecretStr
    demo_customer_tokens: dict[str, SecretStr] = Field(default_factory=dict)
    demo_operator_token: SecretStr | None = None
