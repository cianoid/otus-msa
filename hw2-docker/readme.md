Сборка для ARM

```
docker login
docker build --platform linux/arm64 . -t cianoid/otus-msa:hw2-20260222-v1
docker push cianoid/otus-msa:hw2-20260222-v1
```

Сборка для amd64

```
docker login
docker build --platform linux/amd64 . -t cianoid/otus-msa:hw2-20260222-v1-amd64
docker push cianoid/otus-msa:hw2-20260222-v1-amd64
```