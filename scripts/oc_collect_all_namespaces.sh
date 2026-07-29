#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  oc_collect_all_namespaces.sh [-o <output_dir>] [--tail-lines <N>] [--namespaces "ns1 ns2"]

Description:
  Executa a coleta simplificada para multiplos namespaces e organiza a saida
  por namespace/aplicacao.
  Coleta apenas: logs de pods, deployments, deploymentconfigs, statefulsets,
  configmaps, routes, services, jobs, replicasets e hpa.
EOF
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COLLECT_SCRIPT="$SCRIPT_DIR/oc_collect_namespace.sh"

[[ -f "$COLLECT_SCRIPT" ]] || fail "Script base nao encontrado: $COLLECT_SCRIPT"

OUTPUT_DIR="./oc-health-artifacts-$(date '+%Y%m%d_%H%M%S')"
TAIL_LINES="300"
NAMESPACES="san1-prd san2-prd"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output-dir)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    --tail-lines)
      TAIL_LINES="${2:-}"
      shift 2
      ;;
    --namespaces)
      NAMESPACES="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Parametro invalido: $1"
      ;;
  esac
done

[[ "$TAIL_LINES" =~ ^[0-9]+$ ]] || fail "--tail-lines deve ser numerico"
command -v oc >/dev/null 2>&1 || fail "Comando 'oc' nao encontrado no PATH"
oc whoami >/dev/null 2>&1 || fail "Sem sessao autenticada no OpenShift. Execute: oc login"
mkdir -p "$OUTPUT_DIR"

for ns in $NAMESPACES; do
  echo "[INFO] Coletando namespace: $ns"
  bash "$COLLECT_SCRIPT" -n "$ns" -o "$OUTPUT_DIR" --tail-lines "$TAIL_LINES"
done

echo "[INFO] Coleta concluida em: $OUTPUT_DIR"
