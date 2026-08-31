# Установка

## Подготовка репозитория

```shell
helm repo add prometheus https://prometheus-community.github.io/helm-charts
```

https://artifacthub.io/packages/helm/prometheus-community/kube-prometheus-stack

## Скачивание шаблона значений

```shell
helm show values prometheus/kube-prometheus-stack > ./values.yaml
```

Необходимо отредактировать значения. Итоговый файл находится - `./values.yaml`. Все измененные параметры отмечены комментарием `# TODO changed`

## Установка

```shell
helm upgrade --install prometheus prometheus/kube-prometheus-stack -f ./values.yaml -n prometheus
```

Прописать в /etc/hosts запись

```shell
127.0.0.1 grafana.local
```

# Начало работы

## Пароль

```shell
kubectl --namespace prometheus get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo
```

Grafana доступна по адресу http://grafana.local/

## Настроить Grafana

### Импорт алертов

Актуальные алерты хранятся в `alerts/alerts.yaml` и `alerts/alerts.json`.  
При старте Grafana они автоматически загружаются из ConfigMap `grafana-alerting`:

```shell
kubectl apply -f infra/prometheus/grafana-provisioning/alerting-configmap.yaml
```

ConfigMap монтируется в `/etc/grafana/provisioning/alerting` и содержит:
- `alerts.yaml` — правила Unified Alerting;
- `contact-points.yaml` — точку контакта `events`.

Если нужно обновить алерты вручную (без переустановки Grafana), можно запустить:

```shell
cd infra/prometheus/alerts
export GRAFANA_URL=http://grafana.local
export GRAFANA_PASSWORD=$(kubectl --namespace prometheus get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d)
python3 import-alerts.py
```

> После ручного импорта правила будут сброшены при пересоздании пода Grafana, если не обновлён ConfigMap.

### Настройка точки контакта

В Grafana должен существовать contact point с именем `events`.  
Он provisioned из ConfigMap `grafana-alerting` и в Alertmanager конфигурируется в `values.yaml`.
URL по умолчанию:

```text
http://app-notification.default.svc.cluster.local:80/api/v1/notification/alerts/events
```

Если нужно направить алерты в другую систему, измените URL в ConfigMap
`infra/prometheus/grafana-provisioning/contact-points.yaml`, в `values.yaml`
в блоке `alertmanager.config` и пересоздайте ConfigMap/Helm-релиз.

## SLO / SLI

SLO и SLI описаны в `values.yaml` через `additionalPrometheusRulesMap`:

| SLI | PromQL-запись | SLO |
|---|---|---|
| API latency P95 | `slo:api_latency_p95_5m` | < 300 мс |
| API error rate | `slo:api_error_rate_5m` | < 1 % |
| Order failure rate | `slo:order_failure_rate_5m` | < 5 % |
| Kafka consumer max lag | `slo:kafka_consumer_max_lag` | < 1000 сообщений |

Алерты на бизнес-метрики (`OrderFailureRateHigh`, `KafkaConsumerLagHigh`,
`OrderCompensationRateHigh`, `OutboxDLQMessages`, `OutboxPendingMessagesHigh`)
также развёрнуты как PrometheusRule и уходят в Alertmanager.

## Kafka Exporter

Для получения метрик Kafka (consumer lag, topic offsets и др.) в кластере
развёрнут Strimzi Kafka Exporter:

```shell
kubectl apply -f ../kafka/kafka-cluster.yaml
kubectl apply -f ../kafka/kafka-exporter-servicemonitor.yaml
```

## Бизнес-метрики

Сервис `app-order` экспортирует собственные метрики:

- `orders_total{status}` — созданные, оплаченные и упавшие заказы;
- `order_compensations_total{kind}` — компенсации саги;
- `outbox_messages_total{kind,status}` — переходы состояний outbox;
- `outbox_dlq_messages_total{kind}` — сообщения, попавшие в DLQ;
- `outbox_pending_messages{kind}` — текущее количество pending-сообщений.

## Запустить нагрузочное тестирование

Скрипт `test_config.js` нагружает основной бизнес-сценарий — создание заказа через сагу `app-order`.

Перед запуском убедитесь, что приложение развёрнуто и доступно по адресу `http://arch.homework` (или переопределите `BASE_URL`).

### Установить утилиту k6

https://grafana.com/docs/k6/latest/set-up/install-k6/

### Запуск с параметрами по умолчанию

```shell
cd infra/prometheus
k6 run test_config.js
```

### Настройка параметров через переменные окружения

| Переменная | Описание | Значение по умолчанию |
|---|---|---|
| `BASE_URL` | Базовый URL приложения | `http://arch.homework` |
| `VUS` | Целевое количество виртуальных пользователей | `50` |
| `DURATION` | Длительность основной фазы нагрузки | `5m` |
| `RAMP_UP` | Длительность разгона | `1m` |
| `RAMP_DOWN` | Длительность снижения нагрузки | `1m` |

Пример короткой проверки:

```shell
cd infra/prometheus
k6 run -e BASE_URL=http://arch.homework -e VUS=10 -e DURATION=30s test_config.js
```

### Что измеряет скрипт

- `http_req_duration` — задержка HTTP-запросов, SLO: P95 < 300 мс.
- `http_req_failed` — доля HTTP-ошибок, SLO: < 1 %.
- `order_success_rate` — доля заказов со статусом `paid`.
- `order_duration` — длительность выполнения `POST /api/v1/order` (полный цикл саги).
