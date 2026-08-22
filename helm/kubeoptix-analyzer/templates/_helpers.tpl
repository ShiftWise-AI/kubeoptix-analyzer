{{- define "kubeoptix-analyzer.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "kubeoptix-analyzer.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := include "kubeoptix-analyzer.name" . -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "kubeoptix-analyzer.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "kubeoptix-analyzer.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "kubeoptix-analyzer.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kubeoptix-analyzer.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "kubeoptix-analyzer.namespace" -}}
{{- default .Release.Namespace .Values.namespace.name -}}
{{- end -}}

{{- define "kubeoptix-analyzer.imageStreamName" -}}
{{- default (include "kubeoptix-analyzer.fullname" .) .Values.build.imageStreamName -}}
{{- end -}}

{{- define "kubeoptix-analyzer.image" -}}
{{- if and .Values.image.useBuildOutput .Values.build.enabled -}}
{{- printf "%s/%s/%s:%s" .Values.build.registryHost (include "kubeoptix-analyzer.namespace" .) (include "kubeoptix-analyzer.imageStreamName" .) (.Values.build.outputTag | default "latest") -}}
{{- else -}}
{{- printf "%s:%s" .Values.image.repository .Values.image.tag -}}
{{- end -}}
{{- end -}}

{{- define "kubeoptix-analyzer.secretEnvName" -}}
{{- default (printf "%s-env" (include "kubeoptix-analyzer.fullname" .)) .Values.secretEnv.name -}}
{{- end -}}

