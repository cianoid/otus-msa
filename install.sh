#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-deploy}"

get_current_tag() {
  app_name="$1"
  helm get values "${app_name}" -n default -o json | jq '.image.tag'
}

deploy() {
  local tag_auth="$1"
  local tag_user="$2"
  local tag_order="$3"

  echo "Деплой приложений: ${tag_user}, ${tag_auth}, ${tag_order}"
  helmfile \
    --state-values-set app_auth.image.tag="${tag_auth}" \
    --state-values-set app_user.image.tag="${tag_user}" \
    --state-values-set app_order.image.tag="${tag_order}" \
    sync
}

if [ "$MODE" = "build" ]; then
  DATE=$(date +%Y-%m-%d-%H%M)
  TAG_AUTH="auth-${DATE}"
  TAG_USER="user-${DATE}"
  TAG_ORDER="order-${DATE}"

  echo "Сборка образов"
  echo ".. сборка cianoid/otus-msa:${TAG_AUTH}"
  docker build -q -t cianoid/otus-msa:"${TAG_AUTH}" -f services/Dockerfile services/app-auth
  echo ".. сборка cianoid/otus-msa:${TAG_USER}"
  docker build -q -t cianoid/otus-msa:"${TAG_USER}" -f services/Dockerfile services/app-user
  echo ".. сборка cianoid/otus-msa:${TAG_ORDER}"
  docker build -q -t cianoid/otus-msa:"${TAG_ORDER}" -f services/Dockerfile services/app-order

  echo ".. загрузка образа cianoid/otus-msa:${TAG_AUTH} в кубер"
  minikube image load cianoid/otus-msa:"${TAG_AUTH}"
  echo ".. загрузка образа cianoid/otus-msa:${TAG_USER} в кубер"
  minikube image load cianoid/otus-msa:"${TAG_USER}"
  echo ".. загрузка образа cianoid/otus-msa:${TAG_ORDER} в кубер"
  minikube image load cianoid/otus-msa:"${TAG_ORDER}"

  deploy "${TAG_AUTH}" "${TAG_USER}" "${TAG_ORDER}"
else
  TAG_AUTH=$(get_current_tag "app-auth")
  TAG_USER=$(get_current_tag "app-user")
  TAG_ORDER=$(get_current_tag "app-order")
  if [ -z "$TAG_AUTH" ]; then
    echo "Ошибка: не удалось определить текущий тег. Возможно, приложение ещё не было установлено."
    echo "Запустите 'install.sh build' для первой установки."
    exit 1
  fi
  if [ -z "$TAG_USER" ]; then
    echo "Ошибка: не удалось определить текущий тег. Возможно, приложение ещё не было установлено."
    echo "Запустите 'install.sh build' для первой установки."
    exit 1
  fi
  if [ -z "$TAG_ORDER" ]; then
    echo "Ошибка: не удалось определить текущий тег. Возможно, приложение ещё не было установлено."
    echo "Запустите 'install.sh build' для первой установки."
    exit 1
  fi
  deploy "${TAG_AUTH}" "${TAG_USER}" "${TAG_ORDER}"
fi
