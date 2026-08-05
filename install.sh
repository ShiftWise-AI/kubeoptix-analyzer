#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHART_DIR="${CHART_DIR:-$ROOT_DIR/helm/kubeoptix-analyzer}"
RELEASE_NAME="${RELEASE_NAME:-kubeoptix-analyzer}"
NAMESPACE="${NAMESPACE:-shiftwise-ai}"

usage() {
  cat <<'EOF'
Usage:
  ./install.sh -f <values-file> [--dry-run]

Examples:
  ./install.sh -f ./.values.yaml
  ./install.sh -f ./values-shiftwise-ai.yaml --dry-run

Environment overrides (optional):
  RELEASE_NAME=<helm-release>
  NAMESPACE=<k8s-namespace>
  CHART_DIR=<path-to-chart>
EOF
}

VALUES_FILE=""
DRY_RUN="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--values)
      if [[ $# -lt 2 ]]; then
        echo "Error: missing values file after $1" >&2
        usage
        exit 1
      fi
      VALUES_FILE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown argument '$1'" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$VALUES_FILE" ]]; then
  echo "Error: values file is required via -f" >&2
  usage
  exit 1
fi

if ! command -v helm >/dev/null 2>&1; then
  echo "Error: helm is not installed or not in PATH" >&2
  exit 1
fi

if [[ ! -f "$VALUES_FILE" ]]; then
  echo "Error: values file not found: $VALUES_FILE" >&2
  exit 1
fi

if [[ ! -d "$CHART_DIR" ]]; then
  echo "Error: chart directory not found: $CHART_DIR" >&2
  exit 1
fi

VALUES_FILE_ABS="$(cd "$(dirname "$VALUES_FILE")" && pwd)/$(basename "$VALUES_FILE")"

echo "[install.sh] Release: $RELEASE_NAME"
echo "[install.sh] Namespace: $NAMESPACE"
echo "[install.sh] Chart: $CHART_DIR"
echo "[install.sh] Values: $VALUES_FILE_ABS"

HELM_CMD=(
  helm upgrade --install "$RELEASE_NAME" "$CHART_DIR"
  --namespace "$NAMESPACE"
  --create-namespace
  -f "$VALUES_FILE_ABS"
)

if [[ "$DRY_RUN" == "true" ]]; then
  HELM_CMD+=(--dry-run --debug)
fi

"${HELM_CMD[@]}"

echo "[install.sh] Helm deployment finished successfully."
