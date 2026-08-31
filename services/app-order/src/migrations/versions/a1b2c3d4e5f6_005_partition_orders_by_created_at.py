"""005 partition orders by created_at (monthly RANGE)

Revision ID: a1b2c3d4e5f6
Revises: 375ac912f31a
Create Date: 2026-08-24 12:00:00.000000

Конвертирует таблицу orders в секционированную (RANGE по created_at,
месячные секции + DEFAULT). Данные переносятся из старой таблицы.
Первичный ключ и unique-ограничение обязаны включать ключ партиционирования,
поэтому PK становится (id, created_at), а idempotency-уникальность —
(username, idempotency_key, created_at).
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "375ac912f31a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE orders RENAME TO orders_old")
    # Имена констрейнтов/индексов глобальны в схеме — освобождаем их.
    op.execute("ALTER TABLE orders_old RENAME CONSTRAINT orders_pkey TO orders_old_pkey")
    op.execute("ALTER INDEX ix_orders_username RENAME TO ix_orders_username_old")

    op.execute(
        """
        CREATE TABLE orders (LIKE orders_old INCLUDING DEFAULTS)
        PARTITION BY RANGE (created_at)
        """
    )
    op.execute("ALTER TABLE orders ADD CONSTRAINT orders_pkey PRIMARY KEY (id, created_at)")
    op.execute(
        """
        ALTER TABLE orders ADD CONSTRAINT uq_orders_username_idempotency_key
        UNIQUE (username, idempotency_key, created_at)
        """
    )
    op.execute("CREATE INDEX ix_orders_username ON orders (username)")

    # Месячные секции за текущий год назад и год вперёд + DEFAULT на будущее.
    op.execute(
        """
        DO $$
        DECLARE
            start_date date := date_trunc('month', now())::date - interval '12 months';
            stop_date  date := date_trunc('month', now())::date + interval '12 months';
            cur date := start_date;
        BEGIN
            WHILE cur < stop_date LOOP
                EXECUTE format(
                    'CREATE TABLE orders_%s PARTITION OF orders FOR VALUES FROM (%L) TO (%L)',
                    to_char(cur, 'YYYY_MM'), cur, cur + interval '1 month'
                );
                cur := cur + interval '1 month';
            END LOOP;
        END $$
        """
    )
    op.execute("CREATE TABLE orders_default PARTITION OF orders DEFAULT")

    op.execute("INSERT INTO orders SELECT * FROM orders_old")
    op.execute("DROP TABLE orders_old")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE orders RENAME TO orders_partitioned")
    op.execute(
        """
        CREATE TABLE orders (LIKE orders_partitioned INCLUDING DEFAULTS INCLUDING INDEXES)
        """
    )
    op.execute("INSERT INTO orders SELECT * FROM orders_partitioned")
    op.execute("DROP TABLE orders_partitioned")
