"""
AI Workspace API — Application Configuration

Centralized settings management using pydantic-settings.
All values are loaded from environment variables or .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    app_env: str = "development"
    app_secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:3000"

    # ── LLM Provider ────────────────────────────────────────────────────
    llm_provider: str = "openai"  # "openai" or "ollama"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    ollama_base_url: str = "http://localhost:11434"

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_workspace"
    )
    db_echo: bool = False

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Vector Database (Qdrant) ─────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    # ── Rust Parser Service ──────────────────────────────────────────────
    parser_service_url: str = "http://localhost:8080"

    # ── Embeddings ───────────────────────────────────────────────────────
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # ── Authentication ───────────────────────────────────────────────────
    session_cookie_name: str = "ai_workspace_session"
    session_ttl_hours: int = 24 * 7
    session_cookie_secure: bool = False
    admin_email: str = ""
    admin_password: str = ""

    # ── Skills ───────────────────────────────────────────────────────────
    skills_dir: str = "skills"

    # ── Logging ──────────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_json: bool = False

    # ── Rate limiting ────────────────────────────────────────────────────
    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = 60
    rate_limit_api: int = 120
    rate_limit_auth: int = 10
    rate_limit_upload: int = 20

    # ── Uploads ──────────────────────────────────────────────────────────
    max_upload_mb: int = 25
    allowed_upload_extensions: str = (
        "pdf,md,markdown,csv,txt,json,yaml,yml,py,js,jsx,ts,tsx,rs,go,java"
    )

    @property
    def allowed_upload_extension_set(self) -> set[str]:
        """Normalized set of allowed upload extensions."""
        return {
            item.strip().lower().lstrip(".")
            for item in self.allowed_upload_extensions.split(",")
            if item.strip()
        }

    @property
    def json_logs(self) -> bool:
        """Use JSON logs in production unless explicitly disabled."""
        return self.log_json or self.app_env == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def secure_cookies(self) -> bool:
        """Cookies are always secure in production."""
        return self.session_cookie_secure or self.app_env == "production"


# Singleton instance
settings = Settings()
