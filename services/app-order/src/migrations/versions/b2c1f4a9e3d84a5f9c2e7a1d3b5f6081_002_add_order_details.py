"""002 add order details

Revision ID: b2c1f4a9e3d84a5f9c2e7a1d3b5f6081
Revises: 0c74c619a8924a459adc2b834ed73493
Create Date: 2026-08-10 19:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c1f4a9e3d84a5f9c2e7a1d3b5f6081"
down_revision: Union[str, Sequence[str], None] = "0c74c619a8924a459adc2b834ed73493"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("orders", sa.Column("product_id", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("quantity", sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("slot_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("orders", "slot_id")
    op.drop_column("orders", "quantity")
    op.drop_column("orders", "product_id")
