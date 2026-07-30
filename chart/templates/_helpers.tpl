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
{{- define "app-auth.fullname" -}}
{{- if .Values.fullnameOverrideAppAuth }}
{{- .Values.fullnameOverrideAppAuth | trunc 63 | trimSuffix "-" }}
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
{{- default (include "app-auth.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}


---
{{- define "app-user.envs" -}}
env:
  - name: DB_HOST
    value: "postgres.postgres"
  - name: DB_PORT
    value: "5432"
  - name: DB_NAME
    value: "app_user"
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
{{- end -}}

---
{{- define "app-auth.envs" -}}
env:
  - name: DB_HOST
    value: "postgres.postgres"
  - name: DB_PORT
    value: "5432"
  - name: DB_NAME
    value: "app_auth"
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
{{- end -}}
