# Инфраструктура

## Redis (кэш)

Чарт-обёртка `infra/redis/` над `groundhog2k/redis` (по образцу `infra/postgres/`).
Standalone Deployment без PVC (кэш не требует персистентности), сервис `redis.redis:6379`,
метрики `redis_exporter` собираются в Prometheus через ServiceMonitor.

```bash
helm dependency build infra/redis
helm install redis infra/redis -n redis --create-namespace

# проверка
kubectl get pods -n redis
kubectl exec -it deploy/redis -n redis -- redis-cli ping
```

Обновление: `helm upgrade redis infra/redis -n redis`.
