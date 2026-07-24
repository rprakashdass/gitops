# Migration Plan — Split homelab apps into `homelab-gitops`

Goal: make **`gitops`** a pure GitOps *control plane* and move all
build-from-source app code into a separate **`homelab-gitops`** repo. Argo CD
(in `gitops`) keeps deploying everything; it just pulls the homelab charts from
the other repo via per-app `repoURL` overrides.

## End state

```
gitops/                          # CONTROL PLANE — no app source, no Dockerfiles
├── bootstrap/                   # cluster init + root App-of-Apps
├── argocd/                      # app-of-apps values, projects, rbac
├── platform/                    # observability, alerting, ingress  (base-chart REMOVED)
├── springboot-apps/             # demo chart (self-contained; optional to keep)
├── secrets/
└── .sops.yaml                   # secrets/** rule only

homelab-gitops/                  # APP SOURCE + build + chart
├── .github/workflows/build-and-push.yml   # moved from gitops
├── base-chart/                  # shared library (moved from platform/base-chart)
├── services/
│   ├── messaging/telegram-bot/
│   └── automation/hello-world/
└── .sops.yaml                   # services/** rule
```

Why base-chart moves: it is depended on **only** by the homelab service charts
(`springboot-apps` is self-contained). Keeping it in `gitops` would force a
cross-repo `file://` dependency, which Helm can't resolve. So it lives with the
services that use it.

## Steps

### 1. Create the new repo
```bash
gh repo create rprakashdass/homelab-gitops --private
```

### 2. Move source out of `gitops` (run from the gitops repo root)
```bash
git rm -r --cached services platform/base-chart .github/workflows/build-and-push.yml
# then physically move the dirs into a clone of homelab-gitops:
#   services/            -> homelab-gitops/services/
#   platform/base-chart/ -> homelab-gitops/base-chart/
#   .github/workflows/build-and-push.yml -> homelab-gitops/.github/workflows/
git commit -m "chore: move homelab apps to homelab-gitops"
```

### 3. Fix the base-chart dependency path in each service chart
Because `base-chart` is now at the homelab-gitops **root** (not `platform/`),
update every `services/*/Chart.yaml`:
```diff
- repository: "file://../../../platform/base-chart"
+ repository: "file://../../../base-chart"
```
Then verify: `helm dependency build services/automation/hello-world`.

### 4. Point the app-of-apps at the new repo (in `gitops`)
In `argocd/applications/values.yaml`, add a `repoURL`/`targetRevision` override
to each homelab app (leave `enabled: false` until images are built):
```yaml
telegram-bot:
  enabled: false
  project: home
  namespace: home
  syncWave: "0"
  repoURL: https://github.com/rprakashdass/homelab-gitops.git   # <— add
  targetRevision: main                                          # <— add
  path: services/messaging/telegram-bot
```

### 5. Allow the new repo in the `home` AppProject
`argocd/app-projects/homelab-project.yaml` currently allows only `gitops.git`.
Add:
```yaml
sourceRepos:
  - "https://github.com/rprakashdass/gitops.git"
  - "https://github.com/rprakashdass/homelab-gitops.git"   # <— add
```
If `homelab-gitops` is private, register credentials in Argo CD
(`argocd repo add https://github.com/rprakashdass/homelab-gitops.git ...`).

### 6. Move the SOPS `services/**` rule
The `services/**` rule in `.sops.yaml` follows the services to homelab-gitops.
`gitops/.sops.yaml` keeps only the `secrets/**` rule.

### 7. First build, then enable
Push to `homelab-gitops` `main` → CI builds `services/**` → images land in
`ghcr.io/rprakashdass/<name>`. Only then flip each app to `enabled: true` in
`gitops`.

## Decision left open
`springboot-apps/` is a demo Helm chart with no Dockerfile (it references
prebuilt images), so it can stay in `gitops` as a reference workload, or move to
`homelab-gitops` too. Recommend: keep it in `gitops` for now — it's a
self-contained example, not homelab source.
