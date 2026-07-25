#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-deploy}"

get_current_tag() {
  helm get values app -n default -o json 2>/dev/null \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('image',{}).get('tag',''))" 2>/dev/null \
    || true
}

deploy() {
  local tag="$1"
  echo "Деплой приложения с тегом ${tag}"
  helm upgrade app \
    ./chart \
    --timeout 2m \
    --install \
    --wait \
    --rollback-on-failure \
    --namespace default \
    --values ./chart/values.yaml \
    --set image.tag="${tag}"
}

if [ "$MODE" = "build" ]; then
  TAG=$(date +%Y-%m-%d-%H%M)
  echo "Сборка образов"

  cd app || exit 1
  uv export --quiet --format requirements.txt --output-file requirements.txt
  docker build -q -t cianoid/otus-msa:"${TAG}" .
  cd ..

  echo "Загрузка образа cianoid/otus-msa:${TAG} в кубер"
  minikube image load cianoid/otus-msa:"${TAG}"

  deploy "${TAG}"
else
  TAG=$(get_current_tag)
  if [ -z "$TAG" ]; then
    echo "Ошибка: не удалось определить текущий тег. Возможно, приложение ещё не было установлено."
    echo "Запустите 'install.sh build' для первой установки."
    exit 1
  fi
  deploy "${TAG}"
fi
