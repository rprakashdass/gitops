# Two-repo model: `gitops` + `homelab-gitops`

The platform is split across two repositories with one shared control plane.

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│  gitops  (this repo)         │        │  homelab-gitops               │
│  the STANDARD control plane  │        │  homelab app SOURCE           │
│                              │        │                               │
│  • bootstrap/ → 1 Argo CD    │        │  • services/<domain>/<name>/  │
│  • 1 observability stack     │ deploys│      Dockerfile + Helm chart  │
│    (Grafana/Loki/Mimir/…)    │───────▶│  • base-chart (shared lib)    │
│  • argocd/ app-of-apps       │        │  • build-and-push CI → ghcr   │
│  • springboot POS demo       │        │  • services/ai, services/…    │
└─────────────────────────────┘        └──────────────────────────────┘
```

## Responsibilities

**`gitops` (standard / canonical):**
- Bootstraps the **single** Argo CD instance (`bootstrap/`).
- Hosts the **single** observability stack and platform infra (`platform/`).
- Owns the app-of-apps (`argocd/applications`) — the one place every
  Application is declared, including homelab apps.
- Holds the Spring Boot POS demo.

**`homelab-gitops`:**
- Holds homelab application **source**: `services/<domain>/<name>/` (Dockerfile
  + Helm chart), the shared `base-chart`, and the CI that builds images to
  `ghcr.io`.
- Does **not** run its own Argo CD or observability — those are shared, in
  `gitops`. (Any legacy app-of-apps / argocd-project / observability inside
  homelab-gitops is redundant under this model and can be removed.)

## How a homelab app gets deployed

1. Add/build the app in `homelab-gitops` under `services/<domain>/<name>/`.
   Push to `main` → CI builds and pushes `ghcr.io/rprakashdass/<name>`.
2. In **this** repo, add (or enable) an entry in
   [`argocd/applications/values.yaml`](../argocd/applications/values.yaml) with
   a `repoURL` pointing at `homelab-gitops`:
   ```yaml
   my-service:
     enabled: true
     project: home
     namespace: home
     repoURL: https://github.com/rprakashdass/homelab-gitops.git
     targetRevision: main
     path: services/<domain>/<my-service>
   ```
3. The single Argo CD (bootstrapped from `gitops`) syncs it.

The `home` AppProject already allowlists both repos
([`argocd/app-projects/homelab-project.yaml`](../argocd/app-projects/homelab-project.yaml)).
If `homelab-gitops` is private, register it in Argo CD:
`argocd repo add https://github.com/rprakashdass/homelab-gitops.git ...`.

## Reconciling homelab-gitops (recommended follow-ups)

To honor "one Argo CD, one observability tool", trim the redundant control-plane
pieces from `homelab-gitops`:
- Remove its `platform/applications-chart` (app list now lives in `gitops`), OR
  keep it and reference it from `gitops` as a single nested app-of-apps entry —
  pick one, don't run both.
- Remove its `infrastructure/argocd/project.yaml` (the `home` project is defined
  in `gitops`).
- Remove any observability it ships (e.g. its own MinIO/Prometheus) — use the
  shared stack in `gitops`.
