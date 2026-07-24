# bootstrap/

One-command cluster bootstrap. Installs Argo CD + KEDA, then applies the root
"App of Apps" — after which Argo CD syncs everything else from git.

Targets **k3s** (traefik ingress, local-path storage, and metrics-server are
bundled, so this does not install an ingress controller or StorageClass).

| File | Purpose |
|------|---------|
| `bootstrap.sh` | The bootstrap script (idempotent — safe to re-run) |
| `argocd-values.yaml` | Helm values for the Argo CD install |
| `README.md` | This file |

The root Application lives at [`argocd/root.yaml`](../argocd/root.yaml) — a
plain manifest you can `kubectl apply -f argocd/root.yaml` directly. Once
applied, it's self-managing: it's synced from `argocd/` (with
`exclude: 'applications/**'`) by the same Application it defines, so future
edits just need a git commit.

`bootstrap.sh` applies this same file (via `sed`, to honor `--repo-url` /
`--revision` / `--namespace` overrides on first bootstrap) rather than
keeping its own inline copy, to avoid two sources of truth.

## Run

```bash
chmod +x bootstrap/bootstrap.sh
./bootstrap/bootstrap.sh                       # auto-detects git remote as repoURL
# or pin the repo/branch explicitly:
./bootstrap/bootstrap.sh --repo-url https://github.com/rprakashdass/gitops.git --revision main
```

For **reproducible** re-bootstraps, pin the chart versions (otherwise you get
"latest"):

```bash
helm search repo argo/argo-cd --versions | head      # find a version
ARGOCD_CHART_VERSION=<x.y.z> KEDA_CHART_VERSION=<x.y.z> ./bootstrap/bootstrap.sh
```

## After bootstrap

```bash
# admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d; echo

# UI (traefik ingress → http://argocd.local once DNS/hosts points at the node),
# or just port-forward:
kubectl port-forward svc/argocd-server -n argocd 8080:80   # http://localhost:8080

# watch apps sync
kubectl get applications -n argocd -w
```

## Customize

Edit `argocd-values.yaml` (ingress class, resources, HA replicas, SSO). On a
non-k3s cluster, install an ingress controller + default StorageClass first and
set `server.ingress.ingressClassName` to match.

## Troubleshooting

```bash
helm status argocd -n argocd
kubectl get pods -n argocd
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server --tail=100
```
