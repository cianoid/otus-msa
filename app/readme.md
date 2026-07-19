## что сделано

Реализован RESTful CRUD для управления пользователями (создание, получение, обновление, удаление, список) на Python/FastAPI.

- **База данных**: PostgreSQL, поднимается как dependency Helm-чарта.
- **Конфигурация**: вынесена в `values.yaml`, шаблонизируется через ConfigMap.
- **Доступы к БД**: Secrets, шаблонизированные из `values.yaml`.
- **Миграции**: Alembic, запускаются как Job при деплое.
- **Ingress**: настроен на `arch.homework`.
- **Helm-чарт с шаблонизацией**: полный чарт `hw4-app/` с зависимостью от postgres, deployment, service, HPA, migration-job, secret, ingress.
- **Postman-коллекция**: `tests/hw4-app.postman_collection.json` с базовым URL `arch.homework`.
- **Newman**: все 11 запросов успешны, 17/17 assertions пройдены (результат в `tests/test-result.txt`).

## Проверка
- Установить minikube, newman
- Запустить кубик командой 
  ```
  minikube start
  ```
- Добавить запись в /etc/hosts (чтобы можно было по домену ходить к кубику) 
  ```
  127.0.0.1 arch.homework
  ```
- Переходим в папку `hw4-helm` 
- Запускаем установку с помощью `sh ./install.sh` или 
  ```
  helm upgrade hw4-app ./hw4-app --timeout 1m  --install \
  --wait --atomic --namespace default --values ./hw4-app/values.yaml
  ```
- Проверить что все поднялось командами
  - `kubectl get svc` - должен быть сервис `hw4-app` и `hw4-app-postgres`
  - `kubectl get deploy` - должен быть деплоймент `hw4-app`
  - `kubectl get po` - должно быть два пода с именами, начинающимся с `hw4-app-postgres-...` и `hw4-app-...`
- Запустить туннелирование трафика от ноды миникуба на локальную машину командой `minikube tunnel`
- В папке `hw4-k8s/tests` запустить команду `newman run tests/hw4-app.postman_collection.json`
- Для удаления ресурсов с кластера сказать `helm uninstall hw4-app`

## Примеры вывода команд
```bash
% kubectl get svc
NAME               TYPE           CLUSTER-IP       EXTERNAL-IP   PORT(S)          AGE
hw4-app            LoadBalancer   10.106.175.144   127.0.0.1     80:32643/TCP     38m
hw4-app-postgres   NodePort       10.102.230.32    <none>        5432:31111/TCP   38m
kubernetes         ClusterIP      10.96.0.1        <none>        443/TCP          12h

% kubectl get deploy
NAME      READY   UP-TO-DATE   AVAILABLE   AGE
hw4-app   2/2     2            2           39m

% kubectl get pod
NAME                     READY   STATUS    RESTARTS   AGE
hw4-app-7b54d4754b-cpmj7   1/1     Running   0             17m
hw4-app-7b54d4754b-z6pgj   1/1     Running   0             17m
hw4-app-postgres-0         1/1     Running   1 (39m ago)   39m
```

## Подключение в БД с локальной машины
Если надо зацепиться к БД, то прокидываем порт из пода СУБД на локальную машину

```
minikube service hw4-app-postgres --url
http://127.0.0.1:65009
❗  Because you are using a Docker driver on darwin, the terminal needs to be open to run it.
```

Подключаемся к БД по порту из вывода команды
