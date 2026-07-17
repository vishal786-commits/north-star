from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    redis_url: str

    # Monitoring: durable SQLite metrics store + a token guarding the dashboard.
    metrics_db_path: str = "data/metrics.db"
    admin_token: str | None = None

    # Abuse / cost guardrails.
    daily_ip_limit: int = 5              # combined /analyze + /fit per IP per day
    trusted_proxy_hops: int = 1          # ALB=1, CloudFront+ALB=2 (X-Forwarded-For)
    max_upload_bytes: int = 5 * 1024 * 1024   # 5 MB PDF cap
    max_message_chars: int = 4000        # chat message length cap
    max_jd_chars: int = 20000            # job-description length cap

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
