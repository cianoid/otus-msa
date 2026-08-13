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

#### Создание БД для новых сервисов
```shell
kubectl exec -n postgres postgres-0 -- psql -U postgres -c "CREATE DATABASE app_warehouse OWNER dba;"
kubectl exec -n postgres postgres-0 -- psql -U postgres -c "CREATE DATABASE app_delivery OWNER dba;"
kubectl exec -n postgres postgres-0 -- psql -U postgres -d app_warehouse -c "GRANT ALL PRIVILEGES ON SCHEMA public TO dba;"
kubectl exec -n postgres postgres-0 -- psql -U postgres -d app_delivery -c "GRANT ALL PRIVILEGES ON SCHEMA public TO dba;"
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

#### Прописать локальный домен
```shell
sudo echo '127.0.0.1 grafana.local' >> /etc/hosts
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
kubectl apply -f https://strimzi.io/examples/latest/kafka/kafka-single-node.yaml -n kafka
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
helm upgrade ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --reuse-values \
  --values infra/nginx-ingress-controller/values.yaml

helm install ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --create-namespace --values values.yaml
```

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
