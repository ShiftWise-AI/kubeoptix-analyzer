#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  oc_collect_worknodes.sh [-o <output_dir>]

Description:
  Extrai um manifesto YAML para cada node com o label
  node-role.kubernetes.io/worker e grava os arquivos em:
    <output_dir>/worknodes/<node>.yaml

Requirements:
  - oc instalado
  - sessao autenticada no cluster (oc whoami)
  - permissao para listar e consultar nodes
EOF
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

OUTPUT_DIR="."

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output-dir)
      OUTPUT_DIR="${2:-}"
      [[ -n "$OUTPUT_DIR" ]] || fail "$1 requer um diretorio"
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

command -v oc >/dev/null 2>&1 || fail "Comando 'oc' nao encontrado no PATH"
oc whoami >/dev/null 2>&1 || fail "Sem sessao autenticada no OpenShift. Execute: oc login"

WORKNODES_DIR="$OUTPUT_DIR/worknodes"
mkdir -p "$WORKNODES_DIR"

mapfile -t WORKER_NODES < <(
  oc get nodes \
    -l node-role.kubernetes.io/worker \
    -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'
)

if [[ "${#WORKER_NODES[@]}" -eq 0 ]]; then
  echo "[WARN] Nenhum worker node encontrado."
  exit 0
fi

for node in "${WORKER_NODES[@]}"; do
  [[ -n "$node" ]] || continue
  echo "[INFO] Coletando worker node: $node"
  oc get node "$node" -o yaml > "$WORKNODES_DIR/$node.yaml"
done

echo "[INFO] Coleta de worker nodes concluida em: $WORKNODES_DIR"