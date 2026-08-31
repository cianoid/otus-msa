"""002 partition products by HASH(id)

Revision ID: b2c3d4e5f6a7
Revises: fd142c59e417
Create Date: 2026-08-24 12:00:00.000000

Конвертирует таблицу products в секционированную (HASH по id, 4 секции).
HASH выбран потому, что у товара нет естественного некоррелированного
атрибута для RANGE/LIST, а нагрузка — точечные чтения и «горячие»
обновления stock по id: хеш даёт равномерное распределение и распределяет
блокировки строк по секциям. Заодно это шаг к будущему шардированию по id.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "fd142c59e417"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NUM_PARTITIONS = 4


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE products RENAME TO products_old")
    # Имена констрейнтов/индексов глобальны в схеме — освобождаем их.
    op.execute("ALTER TABLE products_old RENAME CONSTRAINT products_pkey TO products_old_pkey")

    op.execute(
        """
        CREATE TABLE products (LIKE products_old INCLUDING DEFAULTS)
        PARTITION BY HASH (id)
        """
    )
    op.execute("ALTER TABLE products ADD CONSTRAINT products_pkey PRIMARY KEY (id)")

    for i in range(NUM_PARTITIONS):
        op.execute(
            f"CREATE TABLE products_p{i} PARTITION OF products "
            f"FOR VALUES WITH (MODULUS {NUM_PARTITIONS}, REMAINDER {i})"
        )

    # Переносим владение sequence на новую таблицу, иначе DROP products_old
    # удалит и sequence (OWNED BY).
    op.execute("ALTER SEQUENCE products_id_seq OWNED BY products.id")

    op.execute(
        "INSERT INTO products (id, name, stock, created_at) SELECT id, name, stock, created_at FROM products_old"
    )
    op.execute("SELECT setval('products_id_seq', COALESCE((SELECT max(id) FROM products), 1))")

    # FK reservations.product_id должен указывать на новую таблицу.
    op.execute("ALTER TABLE reservations DROP CONSTRAINT reservations_product_id_fkey")
    op.execute("DROP TABLE products_old")
    op.execute(
        "ALTER TABLE reservations ADD CONSTRAINT reservations_product_id_fkey "
        "FOREIGN KEY (product_id) REFERENCES products (id)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE reservations DROP CONSTRAINT reservations_product_id_fkey")
    op.execute("ALTER TABLE products RENAME TO products_partitioned")
    op.execute(
        """
        CREATE TABLE products (LIKE products_partitioned INCLUDING DEFAULTS INCLUDING INDEXES)
        """
    )
    op.execute("ALTER SEQUENCE products_id_seq OWNED BY products.id")
    op.execute(
        "INSERT INTO products (id, name, stock, created_at) SELECT id, name, stock, created_at FROM products_partitioned"
    )
    op.execute("SELECT setval('products_id_seq', COALESCE((SELECT max(id) FROM products), 1))")
    op.execute("DROP TABLE products_partitioned")
    op.execute(
        "ALTER TABLE reservations ADD CONSTRAINT reservations_product_id_fkey "
        "FOREIGN KEY (product_id) REFERENCES products (id)"
    )
