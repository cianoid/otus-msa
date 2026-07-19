FROM python:3.14-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apk add --update --no-cache postgresql-dev libpq

WORKDIR /

COPY ./requirements.txt /
RUN python -m pip install -U pip && \
    python -m pip install -r requirements.txt

COPY ./alembic.ini  /
COPY ./migrations /migrations
COPY ./src /app

ENV PATH="/.venv/bin:$PATH"
ENTRYPOINT ["uvicorn", "src.main:app", "--workers", "4", "--port", "8000", "--host", "0.0.0.0"]

# docker build -t cianoid/otus-msa:hw4-20260717-v2 . && minikube image load cianoid/otus-msa:hw4-20260717-v2
# docker push cianoid/otus-msa:hw4-20260717-v2
