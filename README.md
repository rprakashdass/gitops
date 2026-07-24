# GitOps — Cluster Control Plane (Argo CD)

The **standard control-plane repo** for a personal Kubernetes platform. It
bootstraps a single Argo CD, runs one shared observability stack, and declares
every workload as an Argo CD Application. Cluster state is driven from Git —
nothing is applied by hand.

Homelab application *source* lives in a separate repo,
[`homelab-gitops`](https://github.com/rprakashdass/homelab-gitops); this repo
**deploys** it. See [docs/repos.md](docs/repos.md) for the two-repo model.

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
                                        └─ homelab:       telegram-bot, hello-world, …
                                                          (source in homelab-gitops, via repoURL)
```

## Repository layout

| Path | Purpose |
|------|---------|
| [`bootstrap/`](bootstrap) | One-command cluster init + the root App-of-Apps |
| [`argocd/`](argocd) | Argo CD self-management: `applications/` (App-of-Apps), `app-projects/`, `rbac/` |
| [`platform/`](platform) | Shared cluster infra: `observability/`, `alerting/`, `ingress.yaml` |
| [`springboot-apps/`](springboot-apps) | Spring Boot POS demo Helm chart (dev/prod values) |
| [`secrets/`](secrets) | SOPS-encrypted secrets (`*.enc.yaml`) — see [`.sops.yaml`](.sops.yaml) |
| [`docs/`](docs) | Architecture notes ([repos.md](docs/repos.md)) |

## Quickstart

Prereqs: a Kubernetes cluster + `kubectl` + `helm`.

```bash
chmod +x bootstrap/bootstrap.sh
./bootstrap/bootstrap.sh \
  --repo-url https://github.com/rprakashdass/gitops.git \
  --revision main

kubectl get applications -n argocd
```

## Deploying a homelab app

The app's source + chart live in `homelab-gitops`. To deploy it, add/enable an
entry in [`argocd/applications/values.yaml`](argocd/applications/values.yaml)
with a `repoURL` pointing at that repo — full steps in
[docs/repos.md](docs/repos.md).

## Conventions

- **One control plane.** This repo bootstraps the single Argo CD and the single
  observability stack; other repos supply app source, deployed via per-app
  `repoURL:`/`targetRevision:` overrides.
- **`main` is the branch.** Applications default to `gitops.git @ main`.
- **Sync waves** order rollout: `-1` cluster add-ons → `0` foundational →
  `1` platform/apps.
- **Secrets** are committed only as SOPS-encrypted `*.enc.yaml`; plaintext is
  gitignored.

## Learnings

- The App-of-Apps pattern keeps Argo CD self-managing and makes the whole
  cluster reproducible from `bootstrap.sh`.
- A per-app `enabled` toggle turns the repo into an experiment board — add a
  block, flip it on, commit.
- Keeping app *source* out of the control-plane repo (in `homelab-gitops`) keeps
  this repo purely declarative: it describes desired state, it doesn't build it.
