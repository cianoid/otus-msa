Вариант 1 (С КОДОМ)

Сделать простейший RESTful CRUD по созданию, удалению, просмотру и обновлению пользователей.

Пример API - https://app.swaggerhub.com/apis/otus55/users/1.0.0


Добавить базу данных для приложения.

Конфигурация приложения должна хранится в Configmaps.

Доступы к БД должны храниться в Secrets.

Первоначальные миграции должны быть оформлены в качестве Job-ы, если это требуется.

Ingress-ы должны также вести на url arch.homework/ (как и в прошлом задании)


На выходе должны быть предоставлена

    ссылка на директорию в github, где находится директория с манифестами кубернетеса (в виде pull request)
    инструкция по запуску приложения.
        команда установки БД из helm, вместе с файлом values.yaml.
        команда применения первоначальных миграций
        команда kubectl apply -f, которая запускает в правильном порядке манифесты кубернетеса
    Postman коллекция, в которой будут представлены примеры запросов к сервису на создание, получение, изменение и удаление пользователя. Важно: в postman коллекции использовать базовый url - arch.homework.
    Проверить корректность работы приложения используя созданную коллекцию newman run коллекция_постман и приложить скриншот/вывод исполнения корректной работы


Задание со звездочкой:

Добавить шаблонизацию приложения в helm чартах



helm template
helm install --dry-run


helm repo add groundhog2k https://groundhog2k.github.io/helm-charts/
helm repo update
helm dependency build ./hw4app

./install.sh
minikube tunnel



% minikube service list
┌─────────────┬──────────────────┬───────────────┬─────┐
│  NAMESPACE  │       NAME       │  TARGET PORT  │ URL │
├─────────────┼──────────────────┼───────────────┼─────┤
│ default     │ hw4-app          │ http/8000     │     │
│ default     │ hw4-app-postgres │ postgres/5432 │     │
│ default     │ kubernetes       │ No node port  │     │
│ kube-system │ kube-dns         │ No node port  │     │
└─────────────┴──────────────────┴───────────────┴─────┘

 minikube service hw4-app-postgres --url
http://127.0.0.1:65009
❗  Because you are using a Docker driver on darwin, the terminal needs to be open to run it.

## Запуск тестов
newman run hw4-app.postman_collection.json --env-var "baseUrl=arch.homework:8000"
