# Установка
## Подготовка репозитория
```
helm repo add prometheus https://prometheus-community.github.io/helm-charts
```

https://artifacthub.io/packages/helm/prometheus-community/kube-prometheus-stack

## Скачивание шаблона значений
```
helm show values prometheus/kube-prometheus-stack > ./values.yaml
```

Необходимо отредактировать значения. Итоговый файл находится - `./values.yaml`. Все измененные параметры отмечены комментарием `# TODO changed`

## Установка 
```
helm upgrade --install prometheus prometheus/kube-prometheus-stack -f ./values.yaml
```

Прописать в /etc/hosts запись
```
127.0.0.1 grafana.local
```

# Начало работы
## Пароль
```
kubectl --namespace default get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo
```

Grafana доступна по адресу http://grafana.local:8080/

## Настроить Grafana

## Запустить нагрузочное тестирование

100.000 запросов в 10 потоков, не останавливаться при ошибке

```
ab -n 100000 -r -c 10 http://arch.homework/test
```

