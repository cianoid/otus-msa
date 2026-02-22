FROM python:3.14-alpine
LABEL authors="cianoid"

COPY ./requirements.txt /requirements.txt
RUN python -m pip install -U pip && pip install --no-cache-dir -r /requirements.txt

COPY ./app /app
COPY ./entrypoint.sh /entrypoint.sh
EXPOSE 8000

ENTRYPOINT ["sh", "/entrypoint.sh"]
