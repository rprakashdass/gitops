#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Bootstrap Argo CD + GitOps root app.

Usage:
  boostrap/bootstrap.sh [--repo-url <url>] [--revision <rev>] [--namespace <ns>] [--release <name>]

Env vars (optional):
  REPO_URL, TARGET_REVISION, ARGOCD_NAMESPACE, ARGOCD_RELEASE

Examples:
  ./boostrap/bootstrap.sh
  ./boostrap/bootstrap.sh --repo-url https://github.com/you/gitops.git --revision main
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ARGOCD_NAMESPACE="${ARGOCD_NAMESPACE:-argocd}"
ARGOCD_RELEASE="${ARGOCD_RELEASE:-argocd}"
TARGET_REVISION="${TARGET_REVISION:-local-server}"
REPO_URL="${REPO_URL:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-url)
      REPO_URL="$2"; shift 2 ;;
    --revision)
      TARGET_REVISION="$2"; shift 2 ;;
    --namespace)
      ARGOCD_NAMESPACE="$2"; shift 2 ;;
    --release)
      ARGOCD_RELEASE="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2
      ;;
  esac
done

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing dependency: $1" >&2; exit 1; }
}

normalize_repo_url() {
  local url="$1"
  # git@github.com:owner/repo.git -> https://github.com/owner/repo.git
  if [[ "$url" =~ ^git@github\.com:([^/]+)/([^/]+?)(\.git)?$ ]]; then
    echo "https://github.com/${BASH_REMATCH[1]}/${BASH_REMATCH[2]}.git"
    return 0
  fi
  # ssh://git@github.com/owner/repo.git -> https://github.com/owner/repo.git
  if [[ "$url" =~ ^ssh://git@github\.com/([^/]+)/([^/]+?)(\.git)?$ ]]; then
    echo "https://github.com/${BASH_REMATCH[1]}/${BASH_REMATCH[2]}.git"
    return 0
  fi
  echo "$url"
}

need_cmd kubectl
need_cmd helm

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

echo "[1/4] Installing/Upgrading Argo CD via Helm"
helm repo add argo https://argoproj.github.io/argo-helm >/dev/null 2>&1 || true
helm repo update >/dev/null
helm upgrade --install "$ARGOCD_RELEASE" argo/argo-cd \
  --namespace "$ARGOCD_NAMESPACE" \
  --create-namespace \
  --values "$VALUES_FILE"

echo "[2/4] Waiting for Argo CD API server to be ready"
kubectl rollout status "deployment/${ARGOCD_RELEASE}-server" -n "$ARGOCD_NAMESPACE" --timeout=300s

echo "[3/4] Applying root app (App-of-Apps)"
kubectl apply -f "$SCRIPT_DIR/root.yaml"

echo "[4/4] Done"
echo "Argo CD should now create/sync AppProjects and Applications automatically."
echo
kubectl get applications -n "$ARGOCD_NAMESPACE" || true
