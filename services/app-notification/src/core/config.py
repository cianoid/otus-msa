from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ────────────────────────────────────────────────
    app_title: str = "App Notification"

    # ── Database ───────────────────────────────────────────
    db_user: str
    db_pass: str
    db_host: str
    db_port: int = 5432
    db_name: str

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}" f"@{self.db_host}:{self.db_port}/{self.db_name}"

    # ── JWT ────────────────────────────────────────────────
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── Kafka ──────────────────────────────────────────────
    kafka_bootstrap_servers: str | None = None
    kafka_send_email_topic: str = "message.send.email"
    kafka_send_email_topic_dlq: str = "message.send.email.dlq"

    # ── SMTP ───────────────────────────────────────────────
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from: str = "noreply@otus-msa.local"

    # ── Templates ──────────────────────────────────────────
    template_dir: str = "src/templates"


settings = Settings()
