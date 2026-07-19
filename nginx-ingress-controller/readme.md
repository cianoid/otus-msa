# Nginx Ingress Controller
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

```bash
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --values values.yaml
```

```bash
helm upgrade ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --reuse-values \
  --values values.yaml

```


По умолчанию Ingress работает только с HTTP/HTTPS (порты 80 и 443). Чтобы пробросить другие порты (например, для Redis, MySQL), нужно отредактировать специальные ConfigMap'ы.

    Для TCP:
    bash

    kubectl patch configmap tcp-services -n ingress-nginx --patch '{"data":{"6379":"default/redis-service:6379"}}'

    Где 6379 — внешний порт, а default/redis-service:6379 — внутренний сервис.

    Для UDP:
    Аналогично, но используется ConfigMap udp-services.