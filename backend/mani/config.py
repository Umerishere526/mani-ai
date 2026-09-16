# ABOUTME: Application settings loaded from the environment and backend/.env.
# ABOUTME: Import get_settings() rather than reading os.environ anywhere else.

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_PROMPT_CACHE_TTL = 1
PROD_PROMPT_CACHE_TTL = 300


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env", extra="ignore"
    )

    environment: Literal["development", "test", "production"] = "development"

    # Postgres, reached directly rather than through PostgREST, so the chat turn
    # can hold its writes in one transaction.
    database_url: str

    # Supabase hosts Auth and Storage; the database is addressed via database_url.
    supabase_url: str
    supabase_service_role_key: str

    # Supabase signs JWTs either with the project secret (HS256) or with a
    # rotating key pair published as JWKS. Set whichever the project uses.
    supabase_jwt_secret: str = ""
    supabase_jwks_url: str = ""

    # OpenRouter is the only model provider. Its key lives here and never in the
    # database, so it is not decrypted per request and cannot reach a client.
    # The OpenAI SDK is the client because OpenRouter speaks that protocol.
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_timeout_seconds: float = 60.0

    # Used when a prompt row names no model of its own.
    default_chat_model: str = "google/gemini-3-flash-preview"
    default_summary_model: str = "openai/gpt-oss-120b"

    # Sent as OpenRouter routing preferences on every call. Conversations are
    # special-category health data, so upstream training use is refused here
    # rather than relying on a provider's default terms.
    openrouter_data_collection: Literal["deny", "allow"] = "deny"

    # Pin the upstream provider and refuse fallbacks. Without this OpenRouter may route
    # a conversation to any provider serving the model, under whatever terms that
    # provider applies. Defaults carried from the previous system's provider row; a
    # prompt row's `routing` column overrides them when it needs to.
    openrouter_provider_order: list[str] = Field(
        default_factory=lambda: ["google-ai-studio"]
    )
    openrouter_allow_fallbacks: bool = False

    def routing(self, overrides: dict | None = None) -> dict:
        """OpenRouter `provider` options for a call, with per-prompt overrides applied."""
        base = {
            "order": self.openrouter_provider_order,
            "allow_fallbacks": self.openrouter_allow_fallbacks,
            "data_collection": self.openrouter_data_collection,
        }
        return base | (overrides or {})

    # Browsers refuse a cross-origin request unless the server names the origin, so
    # web/ cannot call this at all until its origin is listed. Native mobile is not
    # subject to it. Comma-separated; no wildcard, because requests carry a token.
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    sentry_dsn: str = ""

    # Includes the model's technique reasoning in responses, for conversation testing.
    ai_debug_mode: bool = False

    # When false the crisis panel still appears but the user can keep chatting.
    crisis_blocks_chat: bool = True

    prompt_cache_ttl_seconds: int = Field(default=0)

    @field_validator("prompt_cache_ttl_seconds", mode="before")
    @classmethod
    def _blank_means_unset(cls, value: object) -> object:
        # `KEY=` in a .env arrives as an empty string. For an optional override that
        # should mean "use the default", not refuse to start.
        if isinstance(value, str) and not value.strip():
            return 0
        return value

    @computed_field
    @property
    def jwks_url(self) -> str:
        if self.supabase_jwks_url:
            return self.supabase_jwks_url
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    @computed_field
    @property
    def prompt_cache_ttl(self) -> int:
        if self.prompt_cache_ttl_seconds:
            return self.prompt_cache_ttl_seconds
        if self.environment == "development":
            return DEV_PROMPT_CACHE_TTL
        return PROD_PROMPT_CACHE_TTL


@lru_cache
def get_settings() -> Settings:
    return Settings()
