"""
Application configuration.

Settings are loaded from environment variables (optionally via a .env file
in the project root). See .env.example for the full list of variables.
"""
from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:pass@localhost:5432/pulse"

    # Gemini
    gemini_api_key: str = "your-key-here"
    gemini_model: str = "gemini-1.5-pro"

    # App
    secret_key: str = "your-secret-key"
    environment: str = "development"
    # Comma-separated browser origins allowed to call the API. Keep this
    # explicit in production rather than using a wildcard with credentials.
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Export
    resolve_frame_rate: float = 24.0

    # Media storage
    media_storage_path: str = "./media"
    max_upload_size_mb: int = 2048

    # Transcription
    transcription_provider: str = "gemini"  # "gemini" or "whisper"
    openai_api_key: str = "your-openai-key-here"
    whisper_model: str = "whisper-1"

    # Coloring (Night 4)
    # Gemini vision model used to suggest grading parameters from a
    # reference image + episode frame. Same key as gemini_api_key.
    gemini_vision_model: str = "gemini-1.5-pro"
    luts_dir: str = "app/assets/luts"
    user_luts_dir: str = "./media/luts"  # user-uploaded .cube files

    # Sprint 6: Postiz + Reddit
    postiz_url: str = "http://localhost:3000"
    postiz_api_key: str = "your-key-here"
    reddit_client_id: str = "your-client-id"
    reddit_client_secret: str = "your-client-secret"
    reddit_user_agent: str = "PULSE/1.0 (podcast production tool)"

    # Sprint 8: user management
    # SECRET_KEY (already defined above) signs session tokens. No email
    # provider is integrated — magic links are logged/returned in dev
    # mode only. See app/models/user.py.
    max_users: int = 8
    session_token_ttl_hours: int = 24 * 7
    magic_link_ttl_minutes: int = 15
    invite_ttl_days: int = 7
    # Bootstraps the first admin on startup if no users exist yet (an
    # invite requires an existing admin, so something has to seed the
    # first one). If bootstrap_admin_password is left unset, a random
    # password is generated and printed to the server log ONCE — save it,
    # it isn't stored anywhere in retrievable form.
    bootstrap_admin_email: str = "admin@example.com"
    bootstrap_admin_password: str = ""

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.environment.lower() == "production":
            if len(self.secret_key) < 32 or self.secret_key == "your-secret-key":
                raise ValueError("SECRET_KEY must be a random value of at least 32 characters in production.")
            if self.database_url.startswith("postgresql://user:pass@"):
                raise ValueError("DATABASE_URL must be configured for production.")
            if not self.cors_origins.strip() or "*" in {o.strip() for o in self.cors_origins.split(",") if o.strip()}:
                raise ValueError("CORS_ORIGINS must be an explicit origin allowlist in production; wildcard is not allowed.")
            if not self.bootstrap_admin_password or len(self.bootstrap_admin_password) < 12:
                raise ValueError("BOOTSTRAP_ADMIN_PASSWORD must be at least 12 characters in production.")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor so we don't re-parse the environment on
    every request."""
    return Settings()
