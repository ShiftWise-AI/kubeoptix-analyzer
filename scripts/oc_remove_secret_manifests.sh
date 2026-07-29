#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  oc_remove_secret_manifests.sh -d <diretorio> [--dry-run]

Description:
  Varre recursivamente um diretorio, procura manifests YAML com kind: Secret
  e apaga os arquivos encontrados.

Options:
  -d, --dir       Diretorio raiz para varredura
  --dry-run       Apenas lista os arquivos encontrados, sem apagar
EOF
}

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

main() {
  local target_dir=""
  local dry_run="false"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -d|--dir)
        target_dir="${2:-}"
        shift 2
        ;;
      --dry-run)
        dry_run="true"
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

  [[ -n "$target_dir" ]] || fail "Informe o diretorio com -d|--dir"
  [[ -d "$target_dir" ]] || fail "Diretorio nao encontrado: $target_dir"

  local found_count=0
  local removed_count=0
  local file

  while IFS= read -r -d '' file; do
    if grep -Eq '^[[:space:]]*kind:[[:space:]]*Secret([[:space:]]*$)' "$file"; then
      found_count=$((found_count + 1))
      if [[ "$dry_run" == "true" ]]; then
        log "Encontrado Secret: $file"
        continue
      fi

      rm -f -- "$file"
      removed_count=$((removed_count + 1))
      log "Apagado Secret: $file"
    fi
  done < <(find "$target_dir" -type f \( -name '*.yaml' -o -name '*.yml' \) -print0)

  if [[ "$dry_run" == "true" ]]; then
    log "Dry-run concluido. Secrets encontrados: $found_count"
  else
    log "Varredura concluida. Secrets encontrados: $found_count, apagados: $removed_count"
  fi
}

main "$@"