- Установить minikube, newman
- Запустить кубик командой `minikube start`
- Добавить запись в /etc/hosts (чтобы можно было по домену ходить к кубику) `127.0.0.1 arch.homework`
- В папке `hw3-k8s/k8s` применить команду `kubectl apply -f .`
- Проверить что все поднялось командами
  - `kubectl get svc` - должен быть сервис `hw3-service-v1`
  - `kubectl get deploy` - должен быть деплоймент `hw3-dp`
  - `kubectl get po` - должно быть два пода с именами, начинающимеся с `hw3-dp-...`
- Запустить туннелирование трафика от ноды миникуба на локальную машину командой `minikube tunnel`
- В папке `hw3-k8s/tests` запустить команду `newman run hw3.postman_collection.json`
- Для удаления ресурсов с кластера сказать `kubectl delete -f .`

Примеры вывода команд:
```bash
% kubectl get svc
NAME             TYPE           CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE
hw3-service-v1   LoadBalancer   10.102.81.98   127.0.0.1     80:32363/TCP   15m
kubernetes       ClusterIP      10.96.0.1      <none>        443/TCP        8d

% kubectl get deploy
NAME     READY   UP-TO-DATE   AVAILABLE   AGE
hw3-dp   2/2     2            2           15m

% kubectl get pod
NAME                     READY   STATUS    RESTARTS   AGE
hw3-dp-fdf6f88cc-8fqxs   1/1     Running   0          16m
hw3-dp-fdf6f88cc-tkgmt   1/1     Running   0          16m
```

Оставшиеся вопросы:
- Не ясно как заставить работать ingress-contoller. Он запускается, но работает и без него все
