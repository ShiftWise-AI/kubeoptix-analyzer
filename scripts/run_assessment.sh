#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  # Análise direta em artefatos já coletados (coleta NÃO roda):
  run_assessment.sh --artifacts <dir> [--report <arquivo.md>] [--skip-sanitize]

  # Aliases de --artifacts:
  run_assessment.sh --repo <dir> ...
  run_assessment.sh -a <dir> ...

  # Pipeline com coleta (opcional):
  run_assessment.sh [--namespaces "ns1 ns2"] [-o <output_dir>] [--tail-lines N]
                    [--report <arquivo.md>] [--use-llm] [--skip-sanitize]

Description:
  1. Coleta artefatos OpenShift (somente se --artifacts/--repo NÃO for passado)
  2. Sanitize secrets/logs (pulável com --skip-sanitize)
  3. Gera relatório Markdown com achados e recomendações
     - padrão: análise local (sem LLM)
     - --use-llm: agente Python com API OpenAI-compatible

Examples:
  ./scripts/run_assessment.sh --artifacts ./pasta-saida
  ./scripts/run_assessment.sh --repo ./pasta-saida --report ./relatorio.md
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
REMOVE_SECRETS_SCRIPT="$SCRIPT_DIR/oc_remove_secret_manifests.sh"
VALIDATE_LOGS="$ROOT_DIR/python_valida_logs.py"

ARTIFACTS_DIR=""
OUTPUT_DIR=""
REPORT_PATH=""
NAMESPACES=""
TAIL_LINES="300"
SKIP_SANITIZE=0
USE_LLM=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -a|--artifacts|--repo)
      ARTIFACTS_DIR="${2:-}"
      [[ -n "$ARTIFACTS_DIR" ]] || fail "$1 requer um diretório"
      shift 2
      ;;
    -o|--output-dir)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    -r|--report)
      REPORT_PATH="${2:-}"
      [[ -n "$REPORT_PATH" ]] || fail "--report requer um arquivo .md"
      shift 2
      ;;
    --namespaces)
      NAMESPACES="${2:-}"
      shift 2
      ;;
    --tail-lines)
      TAIL_LINES="${2:-}"
      shift 2
      ;;
    --skip-collect)
      # Compat: equivalente a exigir --artifacts; mantido por compatibilidade.
      if [[ -z "$ARTIFACTS_DIR" && -n "${OUTPUT_DIR:-}" ]]; then
        ARTIFACTS_DIR="$OUTPUT_DIR"
      fi
      shift
      ;;
    --skip-sanitize)
      SKIP_SANITIZE=1
      shift
      ;;
    --use-llm)
      USE_LLM=1
      shift
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

# --artifacts/--repo: análise direta, sem coleta
if [[ -n "$ARTIFACTS_DIR" ]]; then
  [[ -d "$ARTIFACTS_DIR" ]] || fail "Diretório de artefatos nao encontrado: $ARTIFACTS_DIR"
  ARTIFACTS_DIR="$(cd -- "$ARTIFACTS_DIR" && pwd)"
  DO_COLLECT=0
else
  DO_COLLECT=1
  if [[ -z "$OUTPUT_DIR" ]]; then
    OUTPUT_DIR="$ROOT_DIR/oc-health-artifacts-$(date '+%Y%m%d_%H%M%S')"
  fi
  mkdir -p "$OUTPUT_DIR"
  ARTIFACTS_DIR="$(cd -- "$OUTPUT_DIR" && pwd)"
fi

if [[ "$DO_COLLECT" -eq 1 ]]; then
  [[ -f "$COLLECT_SCRIPT" ]] || fail "Script de coleta nao encontrado: $COLLECT_SCRIPT"
  collect_args=(-o "$ARTIFACTS_DIR" --tail-lines "$TAIL_LINES")
  if [[ -n "$NAMESPACES" ]]; then
    collect_args+=(--namespaces "$NAMESPACES")
  fi
  echo "[INFO] Coletando artefatos..."
  bash "$COLLECT_SCRIPT" "${collect_args[@]}"
else
  echo "[INFO] Coleta omitida. Analisando: $ARTIFACTS_DIR"
fi

if [[ "$SKIP_SANITIZE" -eq 0 ]]; then
  [[ -f "$REMOVE_SECRETS_SCRIPT" ]] || fail "Script de remocao de secrets nao encontrado: $REMOVE_SECRETS_SCRIPT"
  [[ -f "$VALIDATE_LOGS" ]] || fail "Script de validacao de logs nao encontrado: $VALIDATE_LOGS"
  echo "[INFO] Removendo manifests de Secret..."
  bash "$REMOVE_SECRETS_SCRIPT" -d "$ARTIFACTS_DIR"
  echo "[INFO] Sanitizando logs..."
  python3 "$VALIDATE_LOGS" "$ARTIFACTS_DIR"
else
  echo "[INFO] Sanitize omitido (--skip-sanitize)."
fi

if [[ -z "$REPORT_PATH" ]]; then
  REPORT_PATH="$ARTIFACTS_DIR/assessment-report.md"
fi

cd "$ROOT_DIR"
if [[ "$USE_LLM" -eq 1 ]]; then
  echo "[INFO] Executando agente LLM..."
  python3 -m agent --artifacts "$ARTIFACTS_DIR" --report "$REPORT_PATH" --mode llm
else
  echo "[INFO] Executando análise local (sem LLM)..."
  python3 -m agent --artifacts "$ARTIFACTS_DIR" --report "$REPORT_PATH" --mode local
fi

echo "[INFO] Assessment concluido."
echo "[INFO] Artefatos: $ARTIFACTS_DIR"
echo "[INFO] Relatorio Markdown pt-BR: $REPORT_PATH"
