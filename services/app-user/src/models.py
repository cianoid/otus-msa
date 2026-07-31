from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class UserDB(Base):
    __tablename__ = "users"

    username = Column(String, primary_key=True, index=True, nullable=False)
    telegram = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
