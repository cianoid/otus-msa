import os
import sys

from dotenv import load_dotenv

load_dotenv()

_db_user = os.environ.get("DB_USER")
_db_pass = os.environ.get("DB_PASS")
_db_host = os.environ.get("DB_HOST")
_db_port = os.environ.get("DB_PORT")
_db_name = os.environ.get("DB_NAME")


if not all([_db_host, _db_pass, _db_name, _db_port, _db_user]):
    _pass_repl = _db_pass.replace(r".*", "*") if isinstance(_db_pass, str) else "--none--"
    print(f"ERROR! Database configuration is incomplete: {_db_user}:{_pass_repl}@{_db_host}:{_db_port}/{_db_name}")
    sys.exit()

DATABASE_URL = f"postgresql+asyncpg://{_db_user}:{_db_pass}@{_db_host}:{_db_port}/{_db_name}"
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

KAFKA_BOOTSTRAP_SERVERS = os.environ.get(
    "KAFKA_BOOTSTRAP_SERVERS"
)
KAFKA_USER_CREATE_TOPIC = os.environ.get("KAFKA_USER_CREATE_TOPIC", "user.create")
