# Helm
1. `helm template` - проверяем корректность манифестов
2. `helm install --dry-run` - проверяем, что манифест установится в кластер 

# Minikube
1. `minikube start --driver=vfkit` (для Apple Silicon. Но нужно пакет поставить сперва `brew install vfkit`)
2. `minikube start --driver=docker` (или другой вариант, если первый не завелся)
