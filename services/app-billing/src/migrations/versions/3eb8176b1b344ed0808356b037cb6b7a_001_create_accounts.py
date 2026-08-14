"""001 create accounts

Revision ID: 3eb8176b1b344ed0808356b037cb6b7a
Revises:
Create Date: 2026-08-03 18:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3eb8176b1b344ed0808356b037cb6b7a"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "accounts",
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("balance", sa.Numeric(18, 2), server_default=sa.text("0.00"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("username"),
    )
    op.create_index(op.f("ix_accounts_username"), "accounts", ["username"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_accounts_username"), table_name="accounts")
    op.drop_table("accounts")
