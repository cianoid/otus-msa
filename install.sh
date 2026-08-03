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
  local tag_billing="$3"
  local tag_order="$4"
  local tag_notification="$5"

  echo "Деплой приложений: ${tag_auth}, ${tag_user}, ${tag_billing}, ${tag_order}, ${tag_notification}"
  helmfile \
    --state-values-set app_auth.image.tag="${tag_auth}" \
    --state-values-set app_user.image.tag="${tag_user}" \
    --state-values-set app_billing.image.tag="${tag_billing}" \
    --state-values-set app_order.image.tag="${tag_order}" \
    --state-values-set app_notification.image.tag="${tag_notification}" \
    sync
}

if [ "$MODE" = "build" ]; then
  DATE=$(date +%Y-%m-%d-%H%M)
  TAG_AUTH="auth-${DATE}"
  TAG_USER="user-${DATE}"
  TAG_BILLING="billing-${DATE}"
  TAG_ORDER="order-${DATE}"
  TAG_NOTIFICATION="notification-${DATE}"

  echo "Сборка образов"
  echo ".. сборка cianoid/otus-msa:${TAG_AUTH}"
  docker build -q -t cianoid/otus-msa:"${TAG_AUTH}" -f services/Dockerfile services/app-auth
  echo ".. сборка cianoid/otus-msa:${TAG_USER}"
  docker build -q -t cianoid/otus-msa:"${TAG_USER}" -f services/Dockerfile services/app-user
  echo ".. сборка cianoid/otus-msa:${TAG_BILLING}"
  docker build -q -t cianoid/otus-msa:"${TAG_BILLING}" -f services/Dockerfile services/app-billing
  echo ".. сборка cianoid/otus-msa:${TAG_ORDER}"
  docker build -q -t cianoid/otus-msa:"${TAG_ORDER}" -f services/Dockerfile services/app-order
  echo ".. сборка cianoid/otus-msa:${TAG_NOTIFICATION}"
  docker build -q -t cianoid/otus-msa:"${TAG_NOTIFICATION}" -f services/Dockerfile services/app-notification

  echo ".. загрузка образа cianoid/otus-msa:${TAG_AUTH} в кубер"
  minikube image load cianoid/otus-msa:"${TAG_AUTH}"
  echo ".. загрузка образа cianoid/otus-msa:${TAG_USER} в кубер"
  minikube image load cianoid/otus-msa:"${TAG_USER}"
  echo ".. загрузка образа cianoid/otus-msa:${TAG_BILLING} в кубер"
  minikube image load cianoid/otus-msa:"${TAG_BILLING}"
  echo ".. загрузка образа cianoid/otus-msa:${TAG_ORDER} в кубер"
  minikube image load cianoid/otus-msa:"${TAG_ORDER}"
  echo ".. загрузка образа cianoid/otus-msa:${TAG_NOTIFICATION} в кубер"
  minikube image load cianoid/otus-msa:"${TAG_NOTIFICATION}"

  deploy "${TAG_AUTH}" "${TAG_USER}" "${TAG_BILLING}" "${TAG_ORDER}" "${TAG_NOTIFICATION}"
else
  TAG_AUTH=$(get_current_tag "app-auth")
  TAG_USER=$(get_current_tag "app-user")
  TAG_BILLING=$(get_current_tag "app-billing")
  TAG_ORDER=$(get_current_tag "app-order")
  TAG_NOTIFICATION=$(get_current_tag "app-notification")

  for tag in TAG_AUTH TAG_USER TAG_BILLING TAG_ORDER TAG_NOTIFICATION; do
    eval "value=\${$tag}"
    if [ -z "$value" ]; then
      echo "Ошибка: не удалось определить текущий тег для ${tag}. Возможно, приложение ещё не было установлено."
      echo "Запустите 'install.sh build' для первой установки."
      exit 1
    fi
  done

  deploy "${TAG_AUTH}" "${TAG_USER}" "${TAG_BILLING}" "${TAG_ORDER}" "${TAG_NOTIFICATION}"
fi
