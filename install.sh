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

  echo "Деплой приложений: ${tag_user}, ${tag_auth}"
  helmfile \
    --state-values-set app_auth.image.tag="${tag_auth}" \
    --state-values-set app_user.image.tag="${tag_user}" \
    sync
}

if [ "$MODE" = "build" ]; then
  TAG_AUTH="auth-"$(date +%Y-%m-%d-%H%M)
  TAG_USER="user-"$(date +%Y-%m-%d-%H%M)

  echo "Сборка образов"
  echo ".. сборка cianoid/otus-msa:${TAG_AUTH}"
  docker build -q -t cianoid/otus-msa:"${TAG_AUTH}" -f services/Dockerfile services/app-auth
  echo ".. сборка cianoid/otus-msa:${TAG_USER}"
  docker build -q -t cianoid/otus-msa:"${TAG_USER}" -f services/Dockerfile services/app-user

  echo ".. загрузка образа cianoid/otus-msa:${TAG_AUTH} в кубер"
  minikube image load cianoid/otus-msa:"${TAG_AUTH}"
  echo ".. загрузка образа cianoid/otus-msa:${TAG_USER} в кубер"
  minikube image load cianoid/otus-msa:"${TAG_USER}"

  deploy "${TAG_AUTH}" "${TAG_USER}"
else
  TAG_AUTH=$(get_current_tag "app-auth")
  TAG_USER=$(get_current_tag "app-user")
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
  deploy "${TAG_AUTH}" "${TAG_USER}"
fi
