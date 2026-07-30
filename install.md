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
! cd nginx-ingress-controller
! helm install ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --create-namespace --values values.yaml
```

## Установка приложения
```shell
./install.sh build
```
