from decimal import Decimal

from sqlalchemy import Column, DateTime, Numeric, String, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AccountDB(Base):
    __tablename__ = "accounts"

    username = Column(String, primary_key=True, index=True, nullable=False)
    balance = Column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
