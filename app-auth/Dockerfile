FROM python:3.14-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apk add --update --no-cache postgresql-dev libpq gcc musl-dev

WORKDIR /

COPY ./requirements.txt /
RUN python -m pip install -U pip && \
    python -m pip install -r requirements.txt

COPY ./src /app

ENTRYPOINT ["uvicorn", "src.main:app", "--workers", "2", "--port", "8001", "--host", "0.0.0.0"]

# docker build -t cianoid/otus-msa-auth:latest -f app-auth/Dockerfile app-auth/
