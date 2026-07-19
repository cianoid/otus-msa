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
helm upgrade --install prometheus prometheus/kube-prometheus-stack -f ./values.yaml
```

```shell
helm upgrade --install prometheus prometheus/kube-prometheus-stack -f ./values.yaml

```


Прописать в /etc/hosts запись
```shell
127.0.0.1 grafana.local
```

# Начало работы
## Пароль
```shell
kubectl --namespace default get secrets prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo
```

Grafana доступна по адресу http://grafana.local:8080/

## Настроить Grafana

## Запустить нагрузочное тестирование

### Установить утилиту k6


```shell
k6 run test_config.js
```
