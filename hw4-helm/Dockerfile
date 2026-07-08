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
COPY ./app /app

ENV PATH="/.venv/bin:$PATH"
ENTRYPOINT ["python", "-m", "app.main"]
#CMD ["python", "-m", "app.main"]

# docker push cianoid/otus-msa:hw4-20260708-v1
# minikube image load cianoid/otus-msa:hw4-20260708-v1