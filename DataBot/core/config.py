from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    slack_signing_secret: str = "development_secret"
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    database_url: str = ""
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    port: int = 3000
    query_row_limit: int = 20
    sql_preview_char_limit: int = 600
    debug_sql: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
