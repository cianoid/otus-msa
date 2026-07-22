import os

from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = (
        "postgresql+asyncpg://" +
        os.environ.get("DB_USER", "") + ":" +
        os.environ.get("DB_PASS", "") + "@" +
        os.environ.get("APP_POSTGRES_SERVICE_HOST", "") + ":" +
        os.environ.get("APP_POSTGRES_SERVICE_PORT", "") + "/" +
        os.environ.get("DB_NAME", "")
)

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
