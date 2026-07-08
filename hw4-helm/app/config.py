import os

from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = (
        "postgresql+asyncpg://" +
        os.environ.get("DB_USER", "") + ":" +
        os.environ.get("DB_PASS", "") + "@" +
        os.environ.get("HW4_APP_POSTGRES_SERVICE_HOST", "") + ":" +
        os.environ.get("HW4_APP_POSTGRES_SERVICE_PORT", "") + "/" +
        os.environ.get("DB_NAME", "")
)
