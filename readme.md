# Установка

## Установка инфраструктуры

### Установка Postgres
#### Удаление старой БД
! Если нужно создать БД с нуля с параметрами из values.yaml, то нужно сперва удалить старую, так как init-скрипт не запустится
```shell
helm uninstall postgres -n postgres
```

```shell
helm dependency build infra/postgres
kubectl create namespace postgres
kubectl create configmap pg-init-scripts --namespace postgres --from-file=infra/postgres/initdb.d/init.sql --dry-run=client -o yaml | kubectl apply -f -
helm upgrade postgres infra/postgres --install --namespace postgres --values infra/postgres/values.yaml
```

#### Создание БД для новых сервисов (если БД уже есть)
```shell
kubectl exec -n postgres postgres-0 -- psql -U dba -c "CREATE DATABASE app_warehouse1 OWNER dba;"
kubectl exec -n postgres postgres-0 -- psql -U dba -c "CREATE DATABASE app_delivery OWNER dba;"
kubectl exec -n postgres postgres-0 -- psql -U dba -d app_warehouse -c "GRANT ALL PRIVILEGES ON SCHEMA public TO dba;"
kubectl exec -n postgres postgres-0 -- psql -U dba -d app_delivery -c "GRANT ALL PRIVILEGES ON SCHEMA public TO dba;"
```


#### Получить доступ к БД
```shell
minikube service postgres -n postgres --url
```

### Установка Prometheus + Grafana

```shell
kubectl create namespace prometheus
helm upgrade prometheus prometheus/kube-prometheus-stack --install --namespace prometheus --values infra/prometheus/values.yaml
```

Настройка алертов, SLO/SLI и Kafka Exporter описана в
[infra/prometheus/readme.md](infra/prometheus/readme.md).

#### Прописать локальные домены
```shell
sudo echo '127.0.0.1 arch.homework' >> /etc/hosts
sudo echo '127.0.0.1 grafana.local' >> /etc/hosts
sudo echo '127.0.0.1 prometheus.local' >> /etc/hosts
sudo echo '127.0.0.1 jaeger.local' >> /etc/hosts
```

#### Вытащить пароль админа
```shell
kubectl --namespace prometheus get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo
```

### Установка Kafka

```shell
kubectl create namespace kafka
kubectl create -f 'https://strimzi.io/install/latest?namespace=kafka' -n kafka
kubectl get pod -n kafka --watch
kubectl apply -f infra/kafka/kafka-cluster.yaml
kubectl apply -f infra/kafka/kafka-exporter-servicemonitor.yaml
kubectl wait kafka/my-cluster --for=condition=Ready --timeout=300s -n kafka
```

#### Удаление Kafka
```shell
kubectl delete kafka my-cluster -n kafka
kubectl delete -f 'https://strimzi.io/install/latest?namespace=kafka' -n kafka
kubectl get pvc -n kafka
kubectl delete pvc -n kafka --all
kubectl get pv | grep kafka
kubectl delete namespace kafka
```

### Установка API Gateway (из папки nginx-ingress-controller): 
```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
kubectl create namespace ingress-nginx
helm upgrade ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --install \
  --reuse-values \
  --values infra/nginx-ingress-controller/values.yaml
```

### Установка Jaeger

```shell
kubectl apply -f infra/jaeger/namespace.yaml
kubectl apply -f infra/jaeger/deployment.yaml
kubectl apply -f infra/jaeger/service.yaml
```

Подождать пару минут и запустить Ingress (иначе манифест не применяется)
```shell
kubectl apply -f infra/jaeger/ingress.yaml
```

#### Прописать локальный домен

UI Jaeger будет доступен по адресу `http://jaeger.local`.

Бэкенд-сервисы уже настроены на экспорт трассировок в `http://jaeger-collector.jaeger.svc.cluster.local:4318` через значение `otel.endpoint` в Helm-чартах (по умолчанию задано в `values.yaml`).

## Установка приложения

Приложение устанавливается в namespace **`default`** (задан в `helmfile.yaml.gotmpl` для всех 8 релизов).

```shell
# если изменился код
./install.py build
# если изменился только манифест
./install.py
```

### Frontend

Frontend-приложение (React + TypeScript + Vite) находится в папке `services/app-frontend/`

Для локальной разработки:
```shell
cd services/app-frontend
npm install
npm run dev
```

Приложение будет доступно по адресу `http://localhost:7100`. API-запросы проксируются через Vite на `http://arch.homework`.

### Сервисы

- `app-auth` — регистрация/логин, публикует `user.create`.
- `app-billing` — счёт пользователя (`deposit`, `withdraw`), слушает `user.create`.
- `app-delivery` — доставка.
- `app-frontend` — React SPA с личным кабинетом (профиль, баланс, заказы, уведомления).
- `app-notification` — слушает `message.send.email`, сохраняет письмо в БД.
- `app-order` — создание заказа, синхронно вызывает `app-billing/withdraw`, публикует `message.send.email`. Оркестратор Саги в части заказа товара: резервирует товар, затем курьера и после списывает деньги. При отказе любого из шагов начинается запуск компенсационных шагов
- `app-user` — профиль пользователя, слушает `user.create`.
- `app-warehouse` — склад. 

## Архитектура взаимодействия сервисов

- **HTTP** — синхронное списание денег при оформлении заказа (`app-order` → `app-billing`).
- **Kafka** — событийное взаимодействие:
  - `user.create` (`app-auth` → `app-billing`, `app-user`) — создание счёта и профиля.
  - `message.send.email` (`app-order` → `app-notification`) — письмо о результате заказа.

Схема взаимодействия сервисов: [docs/hw7-architecture.png](docs/hw7-architecture.png) (исходник Mermaid: [docs/hw7-architecture.mermaid](docs/hw7-architecture.mermaid)).

сдкл