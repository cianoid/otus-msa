from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ────────────────────────────────────────────────
    app_title: str = "App Order"

    # ── Database ───────────────────────────────────────────
    db_user: str
    db_pass: str
    db_host: str
    db_port: int = 5432
    db_name: str

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

    # ── JWT ────────────────────────────────────────────────
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"

    # ── Kafka ──────────────────────────────────────────────
    kafka_bootstrap_servers: str | None = None
    kafka_user_create_topic: str = "user.create"
    kafka_send_email_topic: str = "message.send.email"

    # ── Service URLs (internal cluster DNS) ─────────────────
    billing_service_url: str = "http://app-billing.default.svc.cluster.local:80"
    user_service_url: str = "http://app-user.default.svc.cluster.local:80"
    warehouse_service_url: str = "http://app-warehouse.default.svc.cluster.local:80"
    delivery_service_url: str = "http://app-delivery.default.svc.cluster.local:80"

    # ── Saga retry / circuit breaker ───────────────────────
    saga_retry_max_attempts: int = 5
    saga_retry_min_seconds: float = 0.5
    saga_retry_max_seconds: float = 30.0
    saga_retry_jitter: float = 1.0

    circuit_breaker_fail_max: int = 5
    circuit_breaker_timeout: int = 60

    # ── Outbox worker ──────────────────────────────────────
    outbox_poll_interval_seconds: int = 5
    outbox_batch_size: int = 10
    outbox_max_attempts: int = 10
    outbox_retry_min_seconds: float = 1.0
    outbox_retry_max_seconds: float = 300.0

    # ── Saga recovery worker ───────────────────────────────
    saga_recovery_poll_interval_seconds: int = 30
    saga_recovery_batch_size: int = 10
    # Order is considered stuck only after this delay; must exceed the worst-case
    # duration of the request-path saga (retries with backoff) to avoid races.
    saga_stuck_threshold_seconds: int = 900
    # TTL of the service JWT minted by the recovery worker for downstream calls.
    saga_recovery_token_ttl_seconds: int = 600


settings = Settings()
