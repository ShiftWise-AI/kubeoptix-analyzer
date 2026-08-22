#!/usr/bin/env bash
set -euo pipefail

# Fresh install script for kubeoptix-analyzer on OpenShift via Helm.
# Git authentication is read only from the values file.
# Then run:
#   ./install.sh -f ./helm/kubeoptix-analyzer/values.example.yaml

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RELEASE="${RELEASE:-kubeoptix-analyzer}"
NS="${NS:-shiftwise-ai}"
CHART_PATH="${CHART_PATH:-./helm/kubeoptix-analyzer}"
VALUES_FILE="${VALUES_FILE:-}"
GIT_URI="${GIT_URI:-https://github.com/ShiftWise-AI/kubeoptix-analyzer.git}"
GIT_REF="${GIT_REF:-feature/ocp}"
RESET="${RESET:-false}"
WAIT_BUILD="${WAIT_BUILD:-true}"
BUILD_FROM_LOCAL="${BUILD_FROM_LOCAL:-true}"
APP_READY_TIMEOUT="${APP_READY_TIMEOUT:-300s}"
POST_INSTALL_CLEANUP="${POST_INSTALL_CLEANUP:-true}"
CLEANUP_DRY_RUN="${CLEANUP_DRY_RUN:-false}"
CLEANUP_TARGET_KINDS="${CLEANUP_TARGET_KINDS:-configmap,secret,certificate,certificaterequest,order,challenge}"

usage() {
  echo "Usage: $0 -f <values-file>"
  echo "   or: $0 <values-file>"
  echo
  echo "Example:"
  echo "  $0 -f ./helm/kubeoptix-analyzer/values.example.yaml"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--values)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] Missing value for $1"
        usage
        exit 1
      fi
      VALUES_FILE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -z "$VALUES_FILE" ]]; then
        VALUES_FILE="$1"
        shift
      else
        echo "[ERROR] Unknown argument: $1"
        usage
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$VALUES_FILE" ]]; then
  echo "[ERROR] Values file parameter is required."
  usage
  exit 1
fi

if [[ ! -f "$VALUES_FILE" ]]; then
  echo "[ERROR] Values file not found: $VALUES_FILE"
  exit 1
fi

command -v helm >/dev/null 2>&1 || { echo "[ERROR] helm not found"; exit 1; }
command -v oc >/dev/null 2>&1 || { echo "[ERROR] oc not found"; exit 1; }

oc whoami >/dev/null

echo "[INFO] Release: $RELEASE"
echo "[INFO] Namespace: $NS"
echo "[INFO] Chart: $CHART_PATH"
echo "[INFO] Values: $VALUES_FILE"

if [[ "$RESET" == "true" ]]; then
  echo "[INFO] Removing previous release (if any)..."
  helm uninstall "$RELEASE" -n "$NS" || true
fi

if ! oc get namespace "$NS" >/dev/null 2>&1; then
  echo "[ERROR] Namespace '$NS' does not exist. Create it before running install."
  exit 1
fi

echo "[INFO] Namespace '$NS' already exists."

HELM_ARGS=(
  upgrade --install "$RELEASE" "$CHART_PATH"
  -n "$NS"
  -f "$VALUES_FILE"
  --set namespace.create=false
  --set namespace.name="$NS"
  --set build.enabled=true
  --set build.sourceSecret.create=false
  --set build.source.gitUri="$GIT_URI"
  --set build.source.gitRef="$GIT_REF"
)

echo "[INFO] Git source authentication is managed only by values file settings."

echo "[INFO] Phase 1/2: Deploying build resources only..."
helm "${HELM_ARGS[@]}" --set deploy.enabled=false

echo "[INFO] Triggering OpenShift build..."
BC_NAME="$(oc get bc -n "$NS" -l app.kubernetes.io/instance="$RELEASE" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
if [[ -z "$BC_NAME" ]]; then
  echo "[ERROR] BuildConfig not found for release $RELEASE in namespace $NS"
  exit 1
fi

if [[ "$BUILD_FROM_LOCAL" == "true" ]]; then
  echo "[INFO] Build source mode: local workspace (binary build)"
  if [[ "$WAIT_BUILD" == "true" ]]; then
    oc start-build "$BC_NAME" -n "$NS" --from-dir=. --follow --wait
  else
    oc start-build "$BC_NAME" -n "$NS" --from-dir=. --wait
  fi
else
  echo "[INFO] Build source mode: remote Git source"
  if [[ "$WAIT_BUILD" == "true" ]]; then
    oc start-build "$BC_NAME" -n "$NS" --follow --wait
  else
    oc start-build "$BC_NAME" -n "$NS" --wait
  fi
fi

echo "[INFO] Phase 2/2: Deploying StatefulSet and runtime objects after successful build..."
helm "${HELM_ARGS[@]}" --set deploy.enabled=true

STATEFULSET_NAME="$(oc get statefulset -n "$NS" -l app.kubernetes.io/instance="$RELEASE" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
SERVICE_NAME="$(oc get service -n "$NS" -l app.kubernetes.io/instance="$RELEASE" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"

if [[ -z "$STATEFULSET_NAME" || -z "$SERVICE_NAME" ]]; then
  echo "[ERROR] StatefulSet or Service not found for release $RELEASE in namespace $NS"
  exit 1
fi

echo "[INFO] Waiting for StatefulSet '$STATEFULSET_NAME' to become ready..."
oc rollout status "statefulset/$STATEFULSET_NAME" -n "$NS" --timeout="$APP_READY_TIMEOUT"

echo "[INFO] Checking application health through Service '$SERVICE_NAME'..."
SERVICE_PROXY_PATH="/api/v1/namespaces/$NS/services/http:$SERVICE_NAME:http/proxy/health"
if ! oc get --raw "$SERVICE_PROXY_PATH"; then
  echo
  echo "[ERROR] Application health check failed through Service '$SERVICE_NAME'."
  echo "[INFO] Inspect the workload with:"
  echo "  oc get pods -n $NS"
  echo "  oc logs -n $NS statefulset/$STATEFULSET_NAME --tail=200"
  exit 1
fi
echo

echo "[INFO] Helm status:"
helm status "$RELEASE" -n "$NS"

echo "[INFO] Current resources:"
oc get all -n "$NS"

if [[ "$POST_INSTALL_CLEANUP" == "true" ]]; then
  echo "[INFO] Running post-install cleanup for orphan resources..."
  RELEASE="$RELEASE" NS="$NS" DRY_RUN="$CLEANUP_DRY_RUN" TARGET_KINDS="$CLEANUP_TARGET_KINDS" \
    bash "$ROOT_DIR/cleanup-ocp.sh"
else
  echo "[INFO] Post-install cleanup skipped (POST_INSTALL_CLEANUP=false)."
fi

echo "[INFO] Installation and Service health check completed successfully."
