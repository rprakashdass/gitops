# GitOps — Homelab Platform (Argo CD)

A single Git repository that drives an entire Kubernetes cluster: platform
infrastructure, observability, demo workloads, and self-built homelab services.
Cluster state is declared here and reconciled by Argo CD — nothing is applied
by hand.

## How it works

`bootstrap/bootstrap.sh` installs ingress-nginx, Argo CD, and KEDA, then applies
one **root** Application (the "App of Apps"). The root app renders
[`argocd/applications`](argocd/applications), whose
[`values.yaml`](argocd/applications/values.yaml) is the **single source of truth**
for every workload. Each entry becomes one Argo CD Application; toggle it with
`enabled: true|false`.

```
bootstrap.sh ─► root Application ─► argocd/applications (Helm)
                                        ├─ observability: alloy, loki, mimir, tempo, grafana, minio
                                        ├─ platform:      ingress, alerting, argocd-rbac
                                        ├─ springboot:    pos-system (demo)
                                        └─ homelab:       telegram-bot, hello-world, … (services/**)
```

## Repository layout

| Path | Purpose |
|------|---------|
| [`bootstrap/`](bootstrap) | One-command cluster init + the root App-of-Apps |
| [`argocd/`](argocd) | Argo CD self-management: `applications/` (App-of-Apps), `app-projects/`, `rbac/` |
| [`platform/`](platform) | Cluster infra: `observability/`, `alerting/`, `ingress.yaml`, and the reusable `base-chart/` |
| [`services/`](services) | Self-built homelab apps, grouped by domain (`services/<domain>/<name>/`) — see below |
| [`springboot-apps/`](springboot-apps) | Spring Boot POS demo Helm chart (dev/prod values) |
| [`secrets/`](secrets) | SOPS-encrypted secrets (`*.enc.yaml`) — see [`.sops.yaml`](.sops.yaml) |

## Services (self-discovering CI/CD)

Anything under `services/<domain>/<name>/` with a `Dockerfile` **and** a
`service.yaml` is automatically built and pushed to `ghcr.io` by
[`.github/workflows/build-and-push.yml`](.github/workflows/build-and-push.yml)
on every push to `main`. Each service chart depends on the shared
[`platform/base-chart`](platform/base-chart), so a new service is mostly just
`values.yaml` + a Dockerfile.

To deploy a service, add a block to
[`argocd/applications/values.yaml`](argocd/applications/values.yaml) and set
`enabled: true` (do this **after** the first CI build publishes the image).

## Quickstart

Prereqs: a Kubernetes cluster + `kubectl` + `helm`.

```bash
chmod +x bootstrap/bootstrap.sh
./bootstrap/bootstrap.sh \
  --repo-url https://github.com/rprakashdass/gitops.git \
  --revision main

kubectl get applications -n argocd
```

## Conventions

- **One repo, one branch (`main`).** All Applications default to
  `gitops.git @ main`. Per-app `repoURL:`/`targetRevision:` overrides exist for
  when a workload should be pulled from a *different* repo — e.g. splitting
  homelab apps into a separate `homelab-gitops` repo later, without changing
  this control plane.
- **Sync waves** order rollout: `-1` cluster add-ons → `0` foundational →
  `1` platform/apps.
- **Secrets** are committed only as SOPS-encrypted `*.enc.yaml`; plaintext is
  gitignored.

## Learnings

- The App-of-Apps pattern keeps Argo CD self-managing and makes the whole
  cluster reproducible from `bootstrap.sh`.
- A per-app `enabled` toggle turns the repo into an experiment board — add a
  block, flip it on, commit.
- Splitting alerting config into global vs environment-specific directories
  keeps changes reviewable and reduces chart churn.
