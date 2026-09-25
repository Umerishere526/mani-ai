# ABOUTME: Application settings loaded from the environment and backend/.env.
# ABOUTME: Import get_settings() rather than reading os.environ anywhere else.

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field, field_validator, model_validator
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
    #
    # Every secret below is repr=False. An AttributeError on Settings prints the whole object,
    # and that text lands in logs, tracebacks and Sentry events - confirmed live, where it
    # printed the OpenRouter key. The URL carries the database password.
    database_url: str = Field(repr=False)

    # Supabase hosts Auth and Storage; the database is addressed via database_url.
    supabase_url: str
    supabase_service_role_key: str = Field(repr=False)

    # Supabase signs JWTs either with the project secret (HS256) or with a
    # rotating key pair published as JWKS. Set whichever the project uses.
    supabase_jwt_secret: str = Field(default="", repr=False)
    supabase_jwks_url: str = ""

    # Not used by this backend at runtime - it only ever acts as service-role or verifies
    # a token someone else holds. Read only by the account-lifecycle integration test,
    # which calls GoTrue's public signup/signin endpoints the way a real client would.
    supabase_anon_key: str = ""

    # OpenRouter is the only model provider. Its key lives here and never in the
    # database, so it is not decrypted per request and cannot reach a client.
    # The OpenAI SDK is the client because OpenRouter speaks that protocol.
    openrouter_api_key: str = Field(default="", repr=False)
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

    sentry_dsn: str = Field(default="", repr=False)

    # Includes the model's technique reasoning in responses, for conversation testing.
    ai_debug_mode: bool = False

    # Compared against the Authorization header Vercel Cron sends automatically when this
    # is set as the CRON_SECRET env var on the project. Empty means the endpoint refuses
    # every request - there is no host where an unset secret should mean "open".
    cron_secret: str = Field(default="", repr=False)

    # When false the crisis panel still appears but the user can keep chatting.
    crisis_blocks_chat: bool = True

    # Paid replies one person may get in 24 hours. 0 turns it off. muhammad's number is 300,
    # off for now so testing is not capped; set it before real traffic. Only turns that call
    # the model count, and the safety screen runs before it - a crisis is always answered.
    daily_message_limit: int = Field(default=0, ge=0)

    prompt_cache_ttl_seconds: int = Field(default=0)

    @field_validator("prompt_cache_ttl_seconds", mode="before")
    @classmethod
    def _blank_means_unset(cls, value: object) -> object:
        # `KEY=` in a .env arrives as an empty string. For an optional override that
        # should mean "use the default", not refuse to start.
        if isinstance(value, str) and not value.strip():
            return 0
        return value

    @model_validator(mode="after")
    def _production_needs_its_secrets(self) -> "Settings":
        """Refuse to start a production process that cannot do its job.

        Both of these default to empty so local development and the test suite can run
        without them. In production that default is the dangerous answer: the process
        boots, /health and /health/ready both report ok because neither touches the
        provider or verifies a token, and every real request fails - a chat turn at the
        model call, any authenticated request at the JWKS fetch. Failing at import is the
        difference between a deploy that never goes live and one that looks healthy while
        serving nothing.
        """
        if self.environment != "production":
            return self
        missing = [
            name
            for name, value in (
                ("OPENROUTER_API_KEY", self.openrouter_api_key),
                ("SUPABASE_JWT_SECRET or SUPABASE_JWKS_URL", self.supabase_jwt_secret or self.supabase_jwks_url),
            )
            if not value.strip()
        ]
        if missing:
            raise ValueError(f"production requires: {', '.join(missing)}")
        return self

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
