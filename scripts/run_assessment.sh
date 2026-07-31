#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_assessment.sh [--namespaces "ns1 ns2"] [-o <output_dir>] [--tail-lines N]

Description:
  1. Coleta artefatos dos namespaces OpenShift
  2. Coleta os YAMLs dos worker nodes em <output_dir>/worknodes

Examples:
  ./scripts/run_assessment.sh --namespaces "app-a app-b" -o ./pasta-saida
EOF
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
COLLECT_SCRIPT="$SCRIPT_DIR/oc_collect_all_namespaces.sh"
COLLECT_WORKNODES_SCRIPT="$SCRIPT_DIR/oc_collect_worknodes.sh"

OUTPUT_DIR=""
NAMESPACES=""
TAIL_LINES="300"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output-dir)
      OUTPUT_DIR="${2:-}"
      [[ -n "$OUTPUT_DIR" ]] || fail "$1 requer um diretorio"
      shift 2
      ;;
    --namespaces)
      NAMESPACES="${2:-}"
      [[ -n "$NAMESPACES" ]] || fail "--namespaces requer ao menos um namespace"
      shift 2
      ;;
    --tail-lines)
      TAIL_LINES="${2:-}"
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

if [[ -z "$OUTPUT_DIR" ]]; then
  OUTPUT_DIR="$ROOT_DIR/oc-health-artifacts-$(date '+%Y%m%d_%H%M%S')"
fi
mkdir -p "$OUTPUT_DIR"
ARTIFACTS_DIR="$(cd -- "$OUTPUT_DIR" && pwd)"

[[ -f "$COLLECT_SCRIPT" ]] || fail "Script de coleta nao encontrado: $COLLECT_SCRIPT"
collect_args=(-o "$ARTIFACTS_DIR" --tail-lines "$TAIL_LINES")
if [[ -n "$NAMESPACES" ]]; then
  collect_args+=(--namespaces "$NAMESPACES")
fi
echo "[INFO] Coletando artefatos..."
bash "$COLLECT_SCRIPT" "${collect_args[@]}"

# Geracao do relatorio desativada: este script executa somente a extracao.
# cd "$ROOT_DIR"
# python3 -m agent --artifacts "$ARTIFACTS_DIR" \
#   --report "$ARTIFACTS_DIR/assessment-report.md" --mode local

[[ -f "$COLLECT_WORKNODES_SCRIPT" ]] || fail "Script de coleta de worker nodes nao encontrado: $COLLECT_WORKNODES_SCRIPT"
echo "[INFO] Coletando YAMLs dos worker nodes..."
bash "$COLLECT_WORKNODES_SCRIPT" -o "$ARTIFACTS_DIR"

echo "[INFO] Extracao concluida."
echo "[INFO] Artefatos: $ARTIFACTS_DIR"
