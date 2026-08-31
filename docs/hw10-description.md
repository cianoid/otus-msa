# HW10 — Горизонтальное партиционирование

## Заказы (app-order): RANGE по `created_at`

Миграция `a1b2c3d4e5f6_005_partition_orders_by_created_at.py` конвертирует `orders`
в секционированную таблицу `PARTITION BY RANGE (created_at)`:

- месячные секции `orders_YYYY_MM` (±12 месяцев от текущей даты, генерируются циклом в миграции);
- `orders_default` — DEFAULT-секция на будущее/прошлое вне диапазона;
- данные переносятся `INSERT ... SELECT` из переименованной старой таблицы.

Особенности:

- PK становится `(id, created_at)`, unique idempotency — `(username, idempotency_key, created_at)`:
  в партиционированных таблицах уникальные ограничения обязаны включать ключ партиционирования.
  Побочный эффект: idempotency гарантируется в пределах одной секции (месяца), а не глобально.
- Запросы списка заказов (`WHERE username = ... ORDER BY created_at DESC`) идут по индексу
  `ix_orders_username` внутри каждой секции; выборки с фильтром по дате получают partition pruning.
- Новые месячные секции создаются автоматически pg_partman (см. ниже).

## Управление секциями: pg_partman (premake=2)

Миграция `c3d4e5f6a7b8_006_pg_partman_orders.py` передаёт `orders` под управление
pg_partman: `create_parent(..., p_interval := '1 month', p_premake := 2)` —
фоновый воркер `pg_partman_bgw` всегда держит 2 пустые секции впереди текущей.

Особенности:

- pg_partman 5.x: интервал задаётся в формате PostgreSQL (`'1 month'`, не `'monthly'`);
- pg_partman требует сам управлять DEFAULT-секцией, поэтому созданная в миграции 005
  `orders_default` на время `create_parent` отсоединяется (данные возвращаются после);
- ранее созданные вручную секции `orders_YYYY_MM` остаются неуправляемыми — premake
  считается от текущей даты, запас в 2 секции поддерживается за их границей;
- `p_start_partition` сдвинут за последнюю ручную секцию (+12 мес.), чтобы избежать
  пересечения диапазонов.

Инфраструктура (`infra/postgres`):

- `docker/Dockerfile` — образ `postgres-partman:18` = `postgres:18` + пакет
  `postgresql-18-partman` из PGDG;
- `values.yaml` — `image: postgres-partman:18` и args:
  `shared_preload_libraries=pg_partman_bgw`, `pg_partman_bgw.dbname=app_order`,
  `pg_partman_bgw.interval=3600`.

Сборка и деплой:

```bash
docker build -t postgres-partman:18 infra/postgres/docker
minikube image load postgres-partman:18
# дальше обычный deploy postgres + миграции app-order
```


## Товары (app-warehouse): HASH по `id`, 4 секции

Миграция `b2c3d4e5f6a7_002_partition_products_by_hash.py` конвертирует `products`
в `PARTITION BY HASH (id)` с 4 секциями `products_p0..p3`.

Почему HASH, а не RANGE/LIST:

- у товара нет естественного равномерного атрибута: категории/тенанта в модели нет,
  LIST по категории дал бы перекос (skew), RANGE по id смысла не имеет (id — монотонный счётчик,
  «старые» товары не архивируются);
- нагрузка склада — точечные чтения и «горячие» обновления `stock` по `id`:
  хеш равномерно разносит строки и блокировки по секциям;
- точечные запросы `WHERE id = ?` получают partition pruning (проверено планом: сканируется
  одна секция);
- HASH по `id` — естественный шаг к будущему шардированию каталога по тому же ключу.

Особенности:

- PK остаётся `(id)` — ключ партиционирования входит в него, поэтому FK
  `reservations.product_id → products.id` сохраняется (пересоздаётся в миграции);
- sequence `products_id_seq` переназначается на новую таблицу (`OWNED BY`), иначе
  `DROP products_old` удалил бы его;
- число секций HASH менять «на горячую» нельзя — увеличение требует ребалансировки
  (пересоздания с новым MODULUS), поэтому 4 выбрано с запасом.

## Проверка

Обе миграции (upgrade и downgrade) прогнаны на PostgreSQL 16 в Docker с тестовыми данными:
перенос строк без потерь, работа вставок, FK, partition pruning в `EXPLAIN`.
