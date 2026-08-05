{{/* Common naming helpers */}}
{{- define "kubeoptix-analyzer.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "kubeoptix-analyzer.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "kubeoptix-analyzer.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "kubeoptix-analyzer.labels" -}}
helm.sh/chart: {{ include "kubeoptix-analyzer.chart" . }}
{{ include "kubeoptix-analyzer.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "kubeoptix-analyzer.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kubeoptix-analyzer.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "kubeoptix-analyzer.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "kubeoptix-analyzer.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "kubeoptix-analyzer.image" -}}
{{- if .Values.buildConfig.enabled -}}
{{- $isName := default (include "kubeoptix-analyzer.fullname" .) .Values.buildConfig.output.imageStreamName -}}
{{- $isTag := default "latest" .Values.buildConfig.output.tag -}}
{{- printf "image-registry.openshift-image-registry.svc:5000/%s/%s:%s" .Release.Namespace $isName $isTag -}}
{{- else -}}
{{- printf "%s:%s" .Values.image.repository .Values.image.tag -}}
{{- end -}}
{{- end -}}

{{- define "kubeoptix-analyzer.pvcClaimName" -}}
{{- $existing := trim (default "" .Values.persistence.existingClaim) -}}
{{- if $existing -}}
{{- $existing -}}
{{- else -}}
{{- $claimName := trim (default "" .Values.persistence.claimName) -}}
{{- if $claimName -}}
{{- $claimName -}}
{{- else -}}
{{- printf "%s-data" (include "kubeoptix-analyzer.fullname" .) -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "kubeoptix-analyzer.storageClassName" -}}
{{- $explicit := trim (default "" .Values.persistence.storageClassName) -}}
{{- if and $explicit (ne $explicit "auto") -}}
{{- $explicit -}}
{{- else -}}
{{- $classes := (lookup "storage.k8s.io/v1" "StorageClass" "" "") -}}
{{- $selected := dict "name" "" -}}
{{- if $classes -}}
{{- range $sc := $classes.items -}}
{{- $annotations := default dict $sc.metadata.annotations -}}
{{- $isDefault := or (eq (get $annotations "storageclass.kubernetes.io/is-default-class") "true") (eq (get $annotations "storageclass.beta.kubernetes.io/is-default-class") "true") -}}
{{- if and $isDefault (eq (get $selected "name") "") -}}
{{- $_ := set $selected "name" $sc.metadata.name -}}
{{- end -}}
{{- end -}}
{{- if and (eq (get $selected "name") "") (gt (len $classes.items) 0) -}}
{{- $_ := set $selected "name" ((index $classes.items 0).metadata.name) -}}
{{- end -}}
{{- end -}}
{{- get $selected "name" -}}
{{- end -}}
{{- end -}}
