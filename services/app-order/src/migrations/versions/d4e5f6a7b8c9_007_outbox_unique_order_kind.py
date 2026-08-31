"""007 outbox unique (order_id, kind)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-24 12:00:00.000000

Уникальный constraint на (order_id, kind) в outbox:
- одна компенсация каждого вида и одно уведомление на заказ;
- защищает от дублей при гонке между обработчиком запроса
  и фоновым воркером восстановления зависших саг (ON CONFLICT DO NOTHING).
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint("uq_outbox_order_kind", "outbox", ["order_id", "kind"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_outbox_order_kind", "outbox", type_="unique")
