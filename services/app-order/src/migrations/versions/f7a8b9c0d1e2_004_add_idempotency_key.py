"""add_idempotency_key

Revision ID: f7a8b9c0d1e2
Revises: c0b370f3d21a
Create Date: 2026-08-15 15:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: str | Sequence[str] | None = "c0b370f3d21a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("orders", sa.Column("idempotency_key", sa.String(), nullable=True))
    op.create_unique_constraint("uq_orders_username_idempotency_key", "orders", ["username", "idempotency_key"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_orders_username_idempotency_key", "orders", type_="unique")
    op.drop_column("orders", "idempotency_key")
