echo "Установка приложения"
helm upgrade app \
  ./chart \
  --timeout 2m \
  --debug \
  --install \
  --wait \
  --atomic \
  --namespace default \
  --values ./chart/values.yaml
