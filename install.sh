helm upgrade app \
  ./helm \
  --timeout 2m \
  --debug \
  --install \
  --wait \
  --atomic \
  --namespace default \
  --values ./helm/values.yaml
