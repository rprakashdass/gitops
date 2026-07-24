# Platform Applications Chart

Central management of all platform applications using the **"Apps of Apps"** pattern.

## What is "Apps of Apps"?

Instead of applying individual Application manifests one by one, we use a single Helm chart to **generate all Applications dynamically**.

**Benefits:**
- ✅ Single source of truth (values.yaml lists all apps)
- ✅ Enable/disable apps with one line (`enabled: true/false`)
- ✅ Easy to see what's deployed at a glance
- ✅ Atomic deployments (all apps sync together)
- ✅ Central management with Sync Waves
- ✅ Easy to add new applications

## Architecture

```
┌─────────────────────────────────────────┐
│ platform-applications Helm Chart        │
│                                         │
│ (This chart generates ArgoCD Apps)      │
└────────────────┬────────────────────────┘
                 │ Helm template
                 ▼
┌─────────────────────────────────────────┐
│ ArgoCD Applications (generated)         │
│                                         │
│ ├── Application: home-hello-world       │
│ ├── Application: home-k8s-health-...    │
│ ├── Application: home-notion-monthly    │
│ └── (more as enabled in values)         │
└────────────────┬────────────────────────┘
                 │ Deploys
                 ▼
┌─────────────────────────────────────────┐
│ Kubernetes Cluster (home namespace)     │
│                                         │
│ ├── CronJob: hello-world                │
│ ├── CronJob: k8s-health-report          │
│ ├── CronJob: notion-monthly             │
│ └── ...                                 │
└─────────────────────────────────────────┘
```

## Usage

### 1. Enable/Disable an Application

Edit `values.yaml`:

```yaml
applications:
  hello-world:
    enabled: true    # ← Enable

  github-summary:
    enabled: false   # ← Disable
```

Then deploy:

```bash
helm template platform-applications platform/applications-chart \
  > /tmp/apps.yaml
kubectl apply -f /tmp/apps.yaml -n argocd

# Or let ArgoCD manage it:
kubectl apply -f infrastructure/argocd/applications/platform-applications.yaml
```

### 2. Add a New Application

1. Create the chart in `charts/my-app/`
2. Add to `values.yaml`:

```yaml
applications:
  my-app:
    enabled: true
    description: "My new automation"
    path: charts/my-app
    syncWave: "2"
```

3. Commit and push
4. ArgoCD automatically creates the Application

### 3. View All Applications

```bash
# See what's configured
helm values platform/applications-chart | grep enabled

# See what's actually deployed
kubectl get applications -n argocd
```

### 4. Check Sync Status

```bash
# Watch all apps syncing
kubectl get applications -n argocd -w

# See details
kubectl get applications -n argocd -o wide
```

## Values Reference

### Top-level Configuration

```yaml
repository:
  url: https://github.com/YOUR_USERNAME/homelab-gitops.git
  branch: main

deploymentNamespace: home      # Where apps are deployed
argocdNamespace: argocd        # Where Applications live
argocdProject: home            # ArgoCD Project to use
```

### Sync Policy

Default policy (applied to all apps):

```yaml
syncPolicy:
  automated:
    prune: true        # Delete resources removed from git
    selfHeal: true     # Revert manual cluster changes
  syncOptions:
    - ServerSideApply=true
  retry:
    limit: 3
    backoff:
      duration: 5s
      factor: 2
      maxDuration: 3m
```

### Application Properties

Each application in the `applications` map has:

```yaml
hello-world:
  enabled: true              # Create Application manifest?
  description: "..."        # Annotation describing what it does
  path: charts/hello-world  # Path in repo to the Helm chart
  syncWave: "1"             # Sync order (0 = first, then 1, 2, etc)
```

**Sync Waves**: Control deployment order
- Wave 0: Infrastructure (Prometheus, storage)
- Wave 1: Core automations (hello-world, k8s-health-report)
- Wave 2: Secondary automations (GitHub summary, backups)

## Common Tasks

### Enable GitHub Summary

```yaml
github-summary:
  enabled: true    # ← Change from false to true
```

Push and watch it deploy:

```bash
git add platform/applications-chart/values.yaml
git commit -m "feat: enable github-summary automation"
git push

# Watch it deploy
kubectl get applications -n argocd -w
```

### Disable Notion Monthly Temporarily

```yaml
notion-monthly:
  enabled: false   # ← Temporarily disabled
```

The Application will be deleted from the cluster.

### Check Which Apps Are Enabled

```bash
kubectl get applications -n argocd -o custom-columns=\
NAME:.metadata.name,\
SYNC_STATUS:.status.sync.status,\
HEALTH:.status.health.status
```

### See All Configuration at Once

```bash
helm values platform/applications-chart | less
```

## Deploying Platform Applications

You need one bootstrap Application that manages everything else:

### Create Bootstrap Application

```yaml
# infrastructure/argocd/applications/platform-applications.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: platform-applications
  namespace: argocd
spec:
  project: home
  source:
    repoURL: https://github.com/YOUR_USERNAME/homelab-gitops.git
    targetRevision: main
    path: platform/applications-chart
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

Deploy it:

```bash
kubectl apply -f infrastructure/argocd/applications/platform-applications.yaml
```

Now everything is managed by one Application. Change `values.yaml` and let ArgoCD sync!

## Status and Monitoring

### See All Enabled Applications

```bash
kubectl get applications -n argocd
```

### See Detailed Status

```bash
kubectl describe application home-hello-world -n argocd
```

### Watch Sync in Real-time

```bash
kubectl get applications -n argocd -w
```

### Check Logs

```bash
# ArgoCD controller logs
kubectl logs -n argocd -l app.argoproj.io=argocd-application-controller -f

# Application sync logs
kubectl logs -n argocd deployment/argocd-application-controller -f | grep hello-world
```

## Best Practices

1. **Use meaningful sync waves**
   - 0: Infrastructure components
   - 1: Core automations
   - 2: Secondary/optional automations

2. **Document each app**
   - Always fill in the `description` field
   - Someone reading values.yaml should understand what each app does

3. **Keep values.yaml organized**
   - Group related apps
   - Comment sections for each phase
   - List disabled apps (to document future plans)

4. **Review before enabling**
   - Check that the chart exists at `path:`
   - Verify the chart has proper values
   - Test locally first: `helm template platform/applications-chart`

5. **Use descriptive names**
   - Clear chart names → clear application names
   - `hello-world`, not `app1`
   - `k8s-health-report`, not `report`

## Troubleshooting

### Application Not Created

Check if it's enabled:

```bash
helm template platform/applications-chart | grep "name: home-MY_APP"
```

If not in output, it's disabled in values.yaml.

### Application Created But Not Syncing

```bash
# Check Application status
kubectl describe application home-MY_APP -n argocd

# Check if the chart path exists
git show HEAD:charts/MY_APP/Chart.yaml

# Check chart validation
helm lint charts/MY_APP
```

### Too Many Applications Syncing at Once

Use sync waves to stagger deployments:

```yaml
applications:
  prometheus:
    syncWave: "0"    # Deploy first
  hello-world:
    syncWave: "1"    # Deploy after
  github-summary:
    syncWave: "2"    # Deploy last
```

## Migration from Individual Applications

If you currently have individual Application manifests:

1. Keep `platform-applications` values.yaml in sync with your current manifests
2. Deploy `platform-applications` Application
3. Verify all apps deploy correctly
4. Delete old Application manifests:
   ```bash
   kubectl delete -f infrastructure/argocd/applications/*.yaml
   # except keep platform-applications.yaml
   ```

## Examples

### Example 1: Bootstrap Setup

```bash
# 1. Deploy the bootstrap Application
kubectl apply -f infrastructure/argocd/applications/platform-applications.yaml

# 2. Watch it create all Applications
kubectl get applications -n argocd -w

# Expected output:
# NAME                       SYNC STATUS   HEALTH STATUS
# platform-applications      Synced        Healthy
# home-hello-world           Synced        Healthy
# home-k8s-health-report     Synced        Healthy
# home-notion-monthly        Synced        Healthy
```

### Example 2: Enable New App

```yaml
# Edit platform/applications-chart/values.yaml
github-summary:
  enabled: true   # ← Changed from false
```

```bash
# Commit and push
git add platform/applications-chart/values.yaml
git commit -m "feat: enable github-summary"
git push

# Watch ArgoCD detect the change (within 3 minutes)
kubectl get applications -n argocd -w
# home-github-summary should appear and sync
```

### Example 3: Disable App Temporarily

```yaml
# Disable for maintenance
hello-world:
  enabled: false
```

```bash
git add platform/applications-chart/values.yaml
git commit -m "ops: temporarily disable hello-world for maintenance"
git push

# Watch it disappear
kubectl get applications -n argocd -w
```

## Advanced: Custom Sync Policy Per App

Currently all apps use the global sync policy. To customize per-app:

Edit `templates/applications.yaml` to support per-app overrides:

```yaml
{{- if $app.syncPolicy }}
  syncPolicy:
    {{- toYaml $app.syncPolicy | nindent 4 }}
{{- else }}
  syncPolicy:
    {{- toYaml .Values.syncPolicy | nindent 4 }}
{{- end }}
```

Then in values.yaml:

```yaml
hello-world:
  enabled: true
  syncPolicy:
    automated:
      prune: false  # Don't auto-prune for this app
```

---

**This is the scalable way to manage ArgoCD Applications.**

As your platform grows from 3 to 50 automations, you'll just update `values.yaml`.
No more individual Application manifests. One chart to rule them all.

See also: [../../README.md](../../README.md), [../../QUICKSTART.md](../../QUICKSTART.md)
