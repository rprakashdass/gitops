# Base Chart

Reusable Helm chart for all personal platform services.

Supports:
- **Workloads**: Deployment, StatefulSet, CronJob, Job
- **Networking**: Service, Ingress
- **Storage**: PersistentVolumeClaim, ConfigMap, Secret
- **Scaling**: HorizontalPodAutoscaler
- **Security**: ServiceAccount, Role, RoleBinding, securityContext
- **Health**: Liveness, Readiness, Startup probes

## Usage

Every service chart in `services/` and `apps/` should extend this base chart.

### Example: Create a new service chart

```bash
mkdir -p charts/my-automation
```

Create `charts/my-automation/Chart.yaml`:

```yaml
apiVersion: v2
name: my-automation
description: "My personal automation"
type: application
version: 0.1.0
appVersion: "1.0"
dependencies:
  - name: base-chart
    version: "0.1.0"
    repository: "file://../../../platform/base-chart"
```

Create `charts/my-automation/values.yaml`:

```yaml
base-chart:
  kind: cronjob
  schedule: "0 7 * * *"
  image:
    repository: my-org/my-automation
    tag: "1.0"
  env:
    LOG_LEVEL: "info"
```

Then create templates that use values from `base-chart`.

### Common Patterns

#### CronJob

```yaml
# values.yaml
base-chart:
  kind: cronjob
  schedule: "0 7 * * *"  # daily at 7am UTC
  image:
    repository: my-image
  resources:
    limits:
      memory: "256Mi"
```

#### Deployment with Service

```yaml
base-chart:
  kind: deployment
  replicaCount: 2
  image:
    repository: my-image
  service:
    enabled: true
    port: 8080
    targetPort: 8080
  ingress:
    enabled: true
    hosts:
      - host: my-app.home
        paths:
          - path: /
            pathType: Prefix
```

#### StatefulSet with Storage

```yaml
base-chart:
  kind: statefulset
  image:
    repository: my-image
  persistence:
    enabled: true
    size: 10Gi
    mountPath: /data
```

#### ConfigMap + Secret

```yaml
base-chart:
  configMap:
    enabled: true
    data:
      config.yaml: |
        key: value
  secret:
    enabled: true
    data:
      API_KEY: YWJjMTIz  # base64-encoded
```

#### RBAC

```yaml
base-chart:
  rbac:
    create: true
    rules:
      - apiGroups: [""]
        resources: ["pods"]
        verbs: ["get", "list", "watch"]
```

## Best Practices

1. **Minimal overrides**: Only override what differs from defaults
2. **DRY**: Don't repeat labels, annotations, or security settings
3. **Production-ready**: Every chart includes:
   - Resource requests/limits
   - Security context (non-root, read-only filesystem)
   - RBAC (least privilege)
   - Health probes (when applicable)
   - Labels and annotations

## Template Files

| File | Purpose |
|------|---------|
| `workload.yaml` | Deployment, StatefulSet, CronJob, Job |
| `service.yaml` | Kubernetes Service |
| `ingress.yaml` | Ingress for external access |
| `configmap.yaml` | ConfigMap for config files |
| `secret.yaml` | Secret for sensitive data |
| `pvc.yaml` | PersistentVolumeClaim (non-StatefulSet) |
| `hpa.yaml` | HorizontalPodAutoscaler |
| `serviceaccount.yaml` | ServiceAccount for RBAC |
| `role.yaml` | Role with custom rules |
| `rolebinding.yaml` | RoleBinding connecting ServiceAccount to Role |

## Development

To test changes to base-chart:

```bash
cd platform/base-chart
helm lint
helm template test . -f values.yaml
```

Update the version in `Chart.yaml` when making changes.
