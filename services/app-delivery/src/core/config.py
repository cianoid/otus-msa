from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ────────────────────────────────────────────────
    app_title: str = "App Delivery"

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


settings = Settings()
