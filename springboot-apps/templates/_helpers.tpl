{{/*
Common labels stamped on every resource.
app.kubernetes.io/* are the standard K8s recommended labels — they power
kubectl selectors, Grafana dashboards, and cost-allocation tooling.
*/}}
{{- define "pos.commonLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
