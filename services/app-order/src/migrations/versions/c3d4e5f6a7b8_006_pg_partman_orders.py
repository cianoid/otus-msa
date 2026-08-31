"""006 manage orders partitions with pg_partman (premake=2)

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-08-24 13:00:00.000000

Передаёт управление секциями orders расширению pg_partman:
- pg_partman поддерживает premake=2 пустых секций вперёд автоматически
  (фоновой воркер pg_partman_bgw, настраивается в инфраструктуре Postgres);
- существующая DEFAULT-секция отсоединяется на время create_parent —
  pg_partman требует управлять DEFAULT-секцией сам; её данные возвращаются;
- ранее созданные вручную месячные секции orders_YYYY_MM остаются
  неуправляемыми, но покрытыми: premake считается от текущей даты, так что
  «запас в 2 секции» pg_partman будет держать за границей уже существующих.

Требует: shared_preload_libraries='pg_partman_bgw',
pg_partman_bgw.dbname='app_order' (см. infra/postgres).
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE SCHEMA IF NOT EXISTS partman")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_partman SCHEMA partman")

    # pg_partman должен сам создать DEFAULT-секцию — временно отсоединяем нашу.
    op.execute("ALTER TABLE public.orders DETACH PARTITION public.orders_default")
    op.execute("ALTER TABLE public.orders_default RENAME TO orders_default_legacy")

    # Стартовая секция — первый месяц за границей ранее созданных вручную
    # (миграция 005 создала ±12 месяцев), чтобы не было пересечения диапазонов.
    op.execute(
        """
        SELECT partman.create_parent(
            p_parent_table := 'public.orders',
            p_control := 'created_at',
            p_interval := '1 month',
            p_premake := 2,
            p_start_partition := to_char(
                date_trunc('month', now())::date + interval '12 months', 'YYYY-MM-DD'
            )
        )
        """
    )

    op.execute("INSERT INTO public.orders SELECT * FROM public.orders_default_legacy")
    op.execute("DROP TABLE public.orders_default_legacy")


def downgrade() -> None:
    """Downgrade schema: убирает orders из-под управления pg_partman.

    Сами секции остаются на месте — таблица продолжает работать.
    """
    op.execute("DELETE FROM partman.part_config WHERE parent_table = 'public.orders'")
    op.execute("DROP TABLE IF EXISTS partman.template_public_orders")
    op.execute("DROP EXTENSION IF EXISTS pg_partman")
    op.execute("DROP SCHEMA IF EXISTS partman")
