FROM python:3.14-alpine AS builder

ENV UV_INSTALL_DIR=/opt/uv
ENV PATH="$UV_INSTALL_DIR:$PATH"

# Install uv — fast Python package installer
COPY --from=ghcr.io/astral-sh/uv:latest /uv /opt/uv/uv

WORKDIR /build

# Install dependencies (layer caching: copy only lock files first)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --no-editable

# ── Runtime stage ──────────────────────────────────────────────
FROM python:3.14-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/.venv/bin:$PATH"

COPY --from=builder /build/.venv /.venv

WORKDIR /
COPY ./alembic.ini  /
COPY ./src /src

ENTRYPOINT ["uvicorn", "src.main:app", "--workers", "4", "--port", "8000", "--host", "0.0.0.0"]

# uv export --format requirements.txt --output-file requirements.txt
# docker build -t cianoid/otus-msa:hw6-20260725-v1 . && minikube image load cianoid/otus-msa:hw6-20260725-v1
# docker push cianoid/otus-msa:hw6-20260725-v1
