# Postgres с расширением pg_partman.

# Версия PG должна совпадать с image.tag в infra/postgres/values.yaml
# (пакет postgresql-<major>-partman ставится из PGDG-репозитория базового образа).
FROM postgres:18

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-18-partman \
    && rm -rf /var/lib/apt/lists/*
