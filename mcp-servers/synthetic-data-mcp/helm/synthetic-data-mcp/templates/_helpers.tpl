{{/*
Expand the name of the chart.
*/}}
{{- define "synthetic-data-mcp.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "synthetic-data-mcp.fullname" -}}
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
{{- define "synthetic-data-mcp.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "synthetic-data-mcp.labels" -}}
helm.sh/chart: {{ include "synthetic-data-mcp.chart" . }}
{{ include "synthetic-data-mcp.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- with .Values.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "synthetic-data-mcp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "synthetic-data-mcp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "synthetic-data-mcp.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "synthetic-data-mcp.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the secret to use
*/}}
{{- define "synthetic-data-mcp.secretName" -}}
{{- if .Values.secrets.existingSecret }}
{{- .Values.secrets.existingSecret }}
{{- else }}
{{- include "synthetic-data-mcp.fullname" . }}-secret
{{- end }}
{{- end }}

{{/*
Create the name of the configmap to use
*/}}
{{- define "synthetic-data-mcp.configMapName" -}}
{{- if .Values.configMaps.existingConfigMap }}
{{- .Values.configMaps.existingConfigMap }}
{{- else }}
{{- include "synthetic-data-mcp.fullname" . }}-config
{{- end }}
{{- end }}

{{/*
Generate certificates for TLS
*/}}
{{- define "synthetic-data-mcp.generateCerts" -}}
{{- $altNames := list ( printf "%s.%s" (include "synthetic-data-mcp.fullname" .) .Release.Namespace ) ( printf "%s.%s.svc" (include "synthetic-data-mcp.fullname" .) .Release.Namespace ) -}}
{{- $ca := genCA "synthetic-data-mcp-ca" 365 -}}
{{- $cert := genSignedCert ( include "synthetic-data-mcp.fullname" . ) nil $altNames 365 $ca -}}
tls.crt: {{ $cert.Cert | b64enc }}
tls.key: {{ $cert.Key | b64enc }}
ca.crt: {{ $ca.Cert | b64enc }}
{{- end }}

{{/*
Return the proper image name
*/}}
{{- define "synthetic-data-mcp.image" -}}
{{- if .Values.global.imageRegistry }}
{{- printf "%s/%s:%s" .Values.global.imageRegistry .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) }}
{{- else }}
{{- printf "%s/%s:%s" .Values.image.registry .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) }}
{{- end }}
{{- end }}

{{/*
Return the proper Storage Class
*/}}
{{- define "synthetic-data-mcp.storageClass" -}}
{{- if .Values.global.storageClass }}
{{- .Values.global.storageClass }}
{{- else if .Values.persistence.storageClass }}
{{- .Values.persistence.storageClass }}
{{- end }}
{{- end }}

{{/*
Validate configuration
*/}}
{{- define "synthetic-data-mcp.validateConfig" -}}
{{- if and .Values.ingress.enabled (not .Values.ingress.hosts) }}
{{- fail "Ingress is enabled but no hosts are configured" }}
{{- end }}
{{- if and .Values.autoscaling.enabled (lt (.Values.autoscaling.minReplicas | int) 1) }}
{{- fail "Autoscaling minReplicas must be at least 1" }}
{{- end }}
{{- if and .Values.autoscaling.enabled (gt (.Values.autoscaling.minReplicas | int) (.Values.autoscaling.maxReplicas | int)) }}
{{- fail "Autoscaling minReplicas cannot be greater than maxReplicas" }}
{{- end }}
{{- end }}