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


## Установка API Gateway (из папки nginx-ingress-controller): 
```bash
! cd nginx-ingress-controller
! helm install ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --create-namespace --values values.yaml
```

## Установка приложения
```shell
helm upgrade romashka ./chart --timeout 2m --debug --install --wait --atomic --namespace default --values ./chart/values.yaml
```
