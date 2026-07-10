from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: str
    redis_url: str

    # Monitoring: durable SQLite metrics store + a token guarding the dashboard.
    metrics_db_path: str = "data/metrics.db"
    admin_token: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
