import os

from dotenv import load_dotenv

load_dotenv()

_user = os.environ.get("DB_USER", "")
_pass = os.environ.get("DB_PASS", "")
_host = os.environ.get("APP_AUTH_POSTGRES_SERVICE_HOST", "")
_port = os.environ.get("APP_AUTH_POSTGRES_SERVICE_PORT", "")
_name = os.environ.get("DB_NAME", "")

DATABASE_URL = f"postgresql+asyncpg://{_user}:{_pass}@{_host}"
if _port:
    DATABASE_URL += f":{_port}"
DATABASE_URL += f"/{_name}"


JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
