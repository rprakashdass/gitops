#!/usr/bin/env bash
set -euo pipefail

# Bootstrap Argo CD + the GitOps root app on a fresh cluster.
#
# Assumes k3s (traefik ingress + local-path storage + metrics-server are
# bundled, so this script does NOT install an ingress controller). On a
# non-k3s cluster, install an ingress controller + a default StorageClass
# first, and set ingressClassName accordingly in argocd-values.yaml.

usage() {
  cat <<'EOF'
Bootstrap Argo CD + GitOps root app.

Usage:
  bootstrap/bootstrap.sh [--repo-url <url>] [--revision <rev>] [--namespace <ns>] [--release <name>]

Env vars (optional):
  REPO_URL, TARGET_REVISION, ARGOCD_NAMESPACE, ARGOCD_RELEASE,
  ARGOCD_CHART_VERSION, KEDA_CHART_VERSION   # pin for reproducible bootstraps

Examples:
  ./bootstrap/bootstrap.sh
  ./bootstrap/bootstrap.sh --repo-url https://github.com/you/gitops.git --revision main
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ALLOWED_CONTEXT="k3s-remote"
current_ctx="$(kubectl config current-context 2>/dev/null || true)"
if [[ "$current_ctx" != "$ALLOWED_CONTEXT" ]]; then
  echo "Refusing to bootstrap: current kubectl context '${current_ctx}' is not '${ALLOWED_CONTEXT}'." >&2
  exit 1
fi

ARGOCD_NAMESPACE="${ARGOCD_NAMESPACE:-argocd}"
ARGOCD_RELEASE="${ARGOCD_RELEASE:-argocd}"
TARGET_REVISION="${TARGET_REVISION:-main}"
REPO_URL="${REPO_URL:-}"

# Chart versions — pin these for reproducible re-bootstraps. Leave empty to
# take "latest" (NOT reproducible). Discover available versions with:
#   helm search repo argo/argo-cd --versions | head
#   helm search repo kedacore/keda --versions | head
ARGOCD_CHART_VERSION="${ARGOCD_CHART_VERSION:-}"
KEDA_CHART_VERSION="${KEDA_CHART_VERSION:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-url)   REPO_URL="$2"; shift 2 ;;
    --revision)   TARGET_REVISION="$2"; shift 2 ;;
    --namespace)  ARGOCD_NAMESPACE="$2"; shift 2 ;;
    --release)    ARGOCD_RELEASE="$2"; shift 2 ;;
    -h|--help)    usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing dependency: $1" >&2; exit 1; }
}

normalize_repo_url() {
  local url="$1"
  # git@github.com:owner/repo.git -> https://github.com/owner/repo.git
  if [[ "$url" =~ ^git@github\.com:([^/]+)/([^/]+?)(\.git)?$ ]]; then
    echo "https://github.com/${BASH_REMATCH[1]}/${BASH_REMATCH[2]}.git"; return 0
  fi
  # ssh://git@github.com/owner/repo.git -> https://github.com/owner/repo.git
  if [[ "$url" =~ ^ssh://git@github\.com/([^/]+)/([^/]+?)(\.git)?$ ]]; then
    echo "https://github.com/${BASH_REMATCH[1]}/${BASH_REMATCH[2]}.git"; return 0
  fi
  echo "$url"
}

need_cmd kubectl
need_cmd helm

# Resolve repo URL (flag/env, else the local git remote).
if [[ -z "$REPO_URL" ]]; then
  if command -v git >/dev/null 2>&1 && git rev-parse --show-toplevel >/dev/null 2>&1; then
    REPO_URL="$(git config --get remote.origin.url || true)"
  fi
fi
if [[ -z "$REPO_URL" ]]; then
  echo "Could not auto-detect repo URL. Provide --repo-url (or REPO_URL env var)." >&2
  exit 1
fi
REPO_URL="$(normalize_repo_url "$REPO_URL")"

VALUES_FILE="$SCRIPT_DIR/argocd-values.yaml"

echo "[preflight] Checking cluster reachability + default StorageClass"
kubectl version -o yaml >/dev/null 2>&1 || { echo "Cannot reach a cluster (check kubeconfig)." >&2; exit 1; }
if ! kubectl get storageclass 2>/dev/null | grep -q '(default)'; then
  echo "  WARNING: no default StorageClass found — PVCs (Vault, Loki, Mimir, MinIO, Tempo)" >&2
  echo "           will stay Pending. On k3s this is 'local-path' and is normally present." >&2
fi

echo "[1/2] Installing/Upgrading Argo CD via Helm"
helm repo add argo https://argoproj.github.io/argo-helm >/dev/null 2>&1 || true
helm repo update >/dev/null
helm upgrade --install "$ARGOCD_RELEASE" argo/argo-cd \
  --namespace "$ARGOCD_NAMESPACE" \
  --create-namespace \
  ${ARGOCD_CHART_VERSION:+--version "$ARGOCD_CHART_VERSION"} \
  --values "$VALUES_FILE"

echo "[1b] Waiting for Argo CD server + the Application CRD"
kubectl rollout status "deployment/${ARGOCD_RELEASE}-server" -n "$ARGOCD_NAMESPACE" --timeout=300s
kubectl wait --for=condition=established --timeout=60s crd/applications.argoproj.io


echo "[2/2] Applying root app (App-of-Apps)"
ROOT_APP_FILE="$SCRIPT_DIR/../argocd/root.yaml"
sed \
  -e "s#repoURL: .*#repoURL: ${REPO_URL}#" \
  -e "s#targetRevision: .*#targetRevision: ${TARGET_REVISION}#" \
  -e "s#namespace: .*#namespace: ${ARGOCD_NAMESPACE}#" \
  "$ROOT_APP_FILE" | kubectl apply -f -

echo
echo "Done. Argo CD will now create/sync AppProjects and Applications from git."
kubectl get applications -n "$ARGOCD_NAMESPACE" || true
