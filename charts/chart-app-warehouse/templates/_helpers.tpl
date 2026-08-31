{{/*
Expand the name of the chart.
*/}}
{{- define "app.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "app.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "app.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "app.labels" -}}
helm.sh/chart: {{ include "app.chart" . }}
{{ include "app.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "app.selectorLabels" -}}
app.kubernetes.io/name: {{ include "app.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "app.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "app.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

---
{{- define "app.envs" -}}
env:
  - name: DB_HOST
    value: "postgres.postgres"
  - name: DB_PORT
    value: "5432"
  - name: DB_NAME
    value: "app_warehouse"
  - name: DB_USER
    valueFrom:
      secretKeyRef:
        name: {{ include "app.name" . }}-secrets
        key: DB_USER
  - name: DB_PASS
    valueFrom:
      secretKeyRef:
        name: {{ include "app.name" . }}-secrets
        key: DB_PASS
  - name: JWT_SECRET
    valueFrom:
      secretKeyRef:
        name: {{ include "app.name" . }}-secrets
        key: JWT_SECRET
  - name: KAFKA_BOOTSTRAP_SERVERS
    value: {{ .Values.kafka.bootstrapServers | default "kafka.kafka:9092" | quote }}
  - name: REDIS_HOST
    value: {{ .Values.redis.host | default "redis.redis" | quote }}
  - name: REDIS_PORT
    value: {{ .Values.redis.port | default 6379 | quote }}
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: {{ .Values.otel.endpoint | default "http://jaeger-collector.jaeger.svc.cluster.local:4318" | quote }}
  - name: OTEL_SERVICE_NAME
    value: {{ include "app.name" . | quote }}
{{- end -}}
