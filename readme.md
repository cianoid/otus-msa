# Установка

## Установка Postgres
### Удаление старой БД
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

### Получить доступ к БД
```shell
minikube service postgres -n postgres --url
```

## Установка Prometheus + Grafana
```shell
kubectl create namespace prometheus
helm upgrade prometheus prometheus/kube-prometheus-stack --install --namespace prometheus --values infra/prometheus/values.yaml
```

### Прописать локальный домен
```shell
sudo echo '127.0.0.1 grafana.local' >> /etc/hosts
```

### Вытащить пароль админа
```shell
kubectl --namespace prometheus get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo
```

## Установка Kafka
```shell
kubectl create namespace kafka
kubectl create -f 'https://strimzi.io/install/latest?namespace=kafka' -n kafka
kubectl get pod -n kafka --watch
kubectl apply -f https://strimzi.io/examples/latest/kafka/kafka-single-node.yaml -n kafka
kubectl wait kafka/my-cluster --for=condition=Ready --timeout=300s -n kafka
```

### Удаление Kafka
```shell
kubectl delete kafka my-cluster -n kafka
kubectl delete -f 'https://strimzi.io/install/latest?namespace=kafka' -n kafka
kubectl get pvc -n kafka
kubectl delete pvc -n kafka --all
kubectl get pv | grep kafka
kubectl delete namespace kafka
```

## Установка API Gateway (из папки nginx-ingress-controller): 
```bash
helm upgrade ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --reuse-values \
  --values infra/nginx-ingress-controller/values.yaml

helm install ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --create-namespace --values values.yaml
```

## Установка приложения

Приложение устанавливается в namespace **`default`** (задан в `helmfile.yaml.gotmpl` для всех 5 релизов).

```shell
# если изменился код
./install.sh build
# если изменился только манифест
./install.sh
```

## Архитектура взаимодействия сервисов

Реализован гибридный вариант:

- **HTTP** — синхронное списание денег при оформлении заказа (`app-order` → `app-billing`).
- **Kafka** — событийное взаимодействие:
  - `user.create` (`app-auth` → `app-billing`, `app-user`) — создание счёта и профиля.
  - `message.send.email` (`app-order` → `app-notification`) — письмо о результате заказа.

Схема взаимодействия сервисов: [docs/hw7-architecture.png](docs/hw7-architecture.png) (исходник Mermaid: [docs/hw7-architecture.mermaid](docs/hw7-architecture.mermaid)).

Теоретическая часть (4 варианта взаимодействия, sequence-диаграммы, IDL): [docs/hw7-theory.md](docs/hw7-theory.md).

### Сервисы

- `app-auth` — регистрация/логин, публикует `user.create`.
- `app-user` — профиль пользователя, слушает `user.create`.
- `app-billing` — счёт пользователя (`deposit`, `withdraw`), слушает `user.create`.
- `app-order` — создание заказа, синхронно вызывает `app-billing/withdraw`, публикует `message.send.email`.
- `app-notification` — слушает `message.send.email`, сохраняет письмо в БД.

### Запуск тестов Postman

Коллекция: [postman/otus-msa-hw7.postman_collection.json](postman/otus-msa-hw7.postman_collection.json)

```shell
newman run postman/otus-msa-hw7.postman_collection.json
```

`baseUrl` уже задан в коллекции (`arch.homework`). При необходимости его можно переопределить через environment-файл.

