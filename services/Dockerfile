FROM python:3.14-alpine AS builder

ENV UV_INSTALL_DIR=/opt/uv
ENV PATH="$UV_INSTALL_DIR:$PATH"

# Install uv — fast Python package installer
COPY --from=ghcr.io/astral-sh/uv:latest /uv /opt/uv/uv

WORKDIR /build

RUN apk add --no-cache gcc musl-dev python3-dev zlib-dev

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

#ENTRYPOINT ["python", "-m", "uvicorn", "src.main:app", "--workers", "4", "--port", "8000", "--host", "0.0.0.0"]
ENTRYPOINT ["python", "-m", "uvicorn", "src.main:app", "--port", "8000", "--host", "0.0.0.0"]
