TAG=$(date +%Y-%m-%d-%H%M)
echo "Сборка образов"
cd app || exit 1
uv export --quiet --format requirements.txt --output-file requirements.txt
docker build -q -t cianoid/otus-msa:"${TAG}" .

echo "Загрузка образа cianoid/otus-msa:${TAG} в кубер"
minikube image load cianoid/otus-msa:"${TAG}"
cd ..
#TAG=2026-07-25-1521
echo "Установка приложения"
helm upgrade app \
  ./chart \
  --timeout 2m \
  --debug \
  --install \
  --wait \
  --rollback-on-failure \
  --namespace default \
  --values ./chart/values.yaml \
  --set image.tag="${TAG}"
