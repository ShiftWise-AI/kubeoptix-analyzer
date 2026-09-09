#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

usage() {
    cat <<'EOF'
Usage:
  ./run.sh --artifacts <diretorio> [--report <arquivo-ou-diretorio>]

Examples:
  ./run.sh --artifacts ./artifacts
EOF
}

if [[ $# -eq 0 ]]; then
    usage
    exit 1
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: Python interpreter not found: $PYTHON_BIN" >&2
    exit 1
fi


cd "$ROOT_DIR"

echo "[run.sh] Running agent"
python -m agent "$@"