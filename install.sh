#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-deploy}"

get_current_tag_auth() {
  helm get values app -n default -o json 2>/dev/null \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('image',{}).get('tag','').get('auth',''))" 2>/dev/null \
    || true
}

deploy() {
  local tag="$1"
  echo "Деплой приложения с тегом ${tag}"
  helm upgrade app \
    ./chart \
    --timeout 1m \
    --install \
    --wait \
    --debug \
    --rollback-on-failure \
    --namespace default \
    --values ./chart/values.yaml \
    --set image.tag.auth="${tag}" \
    --set fullnameOverrideAppAuth="app-auth"
}

if [ "$MODE" = "build" ]; then
  TAG_AUTH="auth-"$(date +%Y-%m-%d-%H%M)
  echo "Сборка образов"
  echo ".. сборка cianoid/otus-msa:${TAG_AUTH}"

  docker build  -t cianoid/otus-msa:"${TAG_AUTH}" -f Dockerfile app-auth

  echo ".. загрузка образа cianoid/otus-msa:${TAG_AUTH} в кубер"
  minikube image load cianoid/otus-msa:"${TAG_AUTH}"

  deploy "${TAG_AUTH}"
else
  TAG_AUTH=$(get_current_tag_auth)
  if [ -z "$TAG_AUTH" ]; then
    echo "Ошибка: не удалось определить текущий тег. Возможно, приложение ещё не было установлено."
    echo "Запустите 'install.sh build' для первой установки."
    exit 1
  fi
  deploy "${TAG_AUTH}"
fi
