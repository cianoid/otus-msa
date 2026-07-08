helm upgrade hw4-app \
  ./hw4-app \
  --timeout 1m \
  --debug \
  --install \
  --wait \
  --atomic \
  --namespace default \
  --values ./hw4-app/values.yaml