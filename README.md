# GitOps (Argo CD) — Platform + Spring Boot Apps

## Objective
This repo bootstraps an Argo CD based GitOps setup and manages:
- Platform components (ingress, alerting, observability)
- Sample Spring Boot workloads (POS system)

The goal is a repeatable, reviewable workflow where cluster state is driven from Git.

## Repository Layout
- `boostrap/`: one-command cluster bootstrap (installs ingress-nginx, Argo CD, KEDA, then applies the root “App of Apps”)
- `argocd/`: Argo CD AppProjects, RBAC config, and the `argocd/applications` Helm chart that defines Applications
- `platform/`: platform manifests and Helm values (ingress + observability + alerting)
- `springboot-apps/`: Helm charts for application workloads

## Quickstart (Bootstrap)
Prereqs: a Kubernetes cluster + `kubectl` + `helm`.

```bash
chmod +x boostrap/bootstrap.sh
./boostrap/bootstrap.sh
```

To point Argo CD at a specific repo URL / branch:

```bash
./boostrap/bootstrap.sh \
  --repo-url https://github.com/<owner>/<repo>.git \
  --revision main
```

After bootstrap, Argo CD should create and sync Applications:

```bash
kubectl get applications -n argocd
```

## Configuration
- Argo CD Applications are defined in `argocd/applications/templates/` and toggled via `argocd/applications/values.yaml`.
- Repo and revision defaults for those Applications are set in `argocd/applications/values.yaml` under `global.repoURL` and `global.targetRevision`.

## Learnings
- The “App of Apps” pattern keeps Argo CD self-managing and makes onboarding clusters repeatable.
- Multi-source Applications (Helm + plain manifests) are a clean way to combine charts with repo-managed config.
- Splitting alerting config into global vs environment-specific directories keeps changes reviewable and reduces chart churn.

