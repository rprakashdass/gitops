# ArgoCD Bootstrap - Helm Installation

Install ArgoCD using its **official Helm chart** for easy customization and GitOps management.

## 🚀 Quick Installation

```bash
# 1. Add ArgoCD Helm repo
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

# 2. Install ArgoCD with your custom values
helm install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace \
  --values boostrap/argocd-values.yaml

# 3. Wait for pods to be ready
kubectl wait --for=condition=available --timeout=300s \
  deployment/argocd-server -n argocd

# 4. Get admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d; echo

# 5. Access ArgoCD
# Option A: NodePort (already configured in values.yaml)
MINIKUBE_IP=$(minikube ip)
echo "ArgoCD UI: https://$MINIKUBE_IP:30443"
echo "Username: admin"

# Option B: Port-forward
kubectl port-forward svc/argocd-server -n argocd 8080:443
# https://localhost:8080

# 6. Deploy root app (activate GitOps!)
kubectl apply -f boostrap/root-app.yaml

# 7. Watch applications being created
kubectl get applications -n argocd -w
```

---

## 📁 Files in This Directory

| File | Purpose |
|------|---------|
| `argocd-namespace.yaml` | Creates argocd namespace |
| `argocd-values.yaml` | **Helm values** - customize ArgoCD here |
| `argocd-install.yaml` | Installation commands reference |
| `root-app.yaml` | Root application (App-of-Apps) |
| `README.md` | This file |

---

## ⚙️ Customization

Edit `argocd-values.yaml` to customize ArgoCD:

### Change Service Type

```yaml
server:
  service:
    type: LoadBalancer  # or ClusterIP
```

### Enable Ingress

```yaml
server:
  ingress:
    enabled: true
    ingressClassName: nginx
    hosts:
      - argocd.example.com
    tls:
      - secretName: argocd-tls
        hosts:
          - argocd.example.com
```

### Enable High Availability

```yaml
controller:
  replicas: 2
server:
  replicas: 2
repoServer:
  replicas: 2
```

### Increase Resources

```yaml
controller:
  resources:
    limits:
      cpu: 1000m
      memory: 2Gi
    requests:
      cpu: 500m
      memory: 1Gi
```

---

## 🔄 Update ArgoCD

```bash
# Pull latest chart
helm repo update

# Upgrade ArgoCD
helm upgrade argocd argo/argo-cd \
  --namespace argocd \
  --values boostrap/argocd-values.yaml

# Or upgrade to specific version
helm upgrade argocd argo/argo-cd \
  --version 6.7.3 \
  --namespace argocd \
  --values boostrap/argocd-values.yaml
```

---

## 🔍 Verify Installation

```bash
# Check Helm release
helm list -n argocd

# Check pods
kubectl get pods -n argocd

# Get ArgoCD version
helm get values argocd -n argocd | grep version

# Check service
kubectl get svc argocd-server -n argocd
```

---

## 🎯 Benefits of Helm Installation

| Feature | Benefit |
|---------|---------|
| **Easy Updates** | `helm upgrade` command |
| **Templating** | Helm values for customization |
| **Rollback** | `helm rollback argocd` |
| **Version Control** | Pin chart versions |
| **Less Verbose** | Values file vs raw manifests |

---

## 📝 Complete Bootstrap Flow

```bash
# Step 1: Install ArgoCD via Helm
helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace \
  --values boostrap/argocd-values.yaml

# Step 2: Get credentials
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# Step 3: Access UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
# https://localhost:8080 (admin + password)

# Step 4: Deploy root app
kubectl apply -f boostrap/root-app.yaml

# Step 5: Everything else syncs automatically!
```

---

## 🐛 Troubleshooting

### Check Helm release status

```bash
helm status argocd -n argocd
helm get values argocd -n argocd
```

### See what Helm will install

```bash
helm template argocd argo/argo-cd \
  --namespace argocd \
  --values boostrap/argocd-values.yaml
```

### Reinstall if needed

```bash
# Uninstall
helm uninstall argocd -n argocd

# Clean up
kubectl delete namespace argocd

# Reinstall
helm install argocd argo/argo-cd \
  --namespace argocd \
  --create-namespace \
  --values boostrap/argocd-values.yaml
```

### Check ArgoCD logs

```bash
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server --tail=100
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller --tail=100
```

---

## 🔒 Security Best Practices

After installation:

1. **Change admin password**
   ```bash
   argocd login localhost:8080
   argocd account update-password
   ```

2. **Delete initial secret**
   ```bash
   kubectl delete secret argocd-initial-admin-secret -n argocd
   ```

3. **Enable SSO** (edit argocd-values.yaml)
   ```yaml
   configs:
     cm:
       dex.config: |
         connectors:
         - type: github
           id: github
           name: GitHub
   ```

4. **Enable RBAC** (already configured in values)

---

## 📚 Resources

- [ArgoCD Helm Chart](https://github.com/argoproj/argo-helm/tree/main/charts/argo-cd)
- Local users + RBAC runbook: ARGOCD-LOCAL-USERS-RBAC.md
- Values snippet: argocd-local-users-rbac-example.yaml
- [Chart Values Reference](https://github.com/argoproj/argo-helm/blob/main/charts/argo-cd/values.yaml)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)

---

## ✅ What Happens After Bootstrap

1. ✅ ArgoCD installed via Helm
2. ✅ Accessible via NodePort (30443) or port-forward
3. ✅ Root app deployed → watches Git repo
4. ✅ All applications auto-created and synced:
   - POS System (backend, frontend, MySQL)
   - Monitoring (Grafana, Prometheus, Loki, Mimir, MinIO)
   - Platform Ingress
5. ✅ Future changes via Git + `helm upgrade`