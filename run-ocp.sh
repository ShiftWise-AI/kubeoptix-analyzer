#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

usage() {
    cat <<'EOF'
Usage:
  ./run-ocp.sh --artifacts <diretorio> [--report <arquivo-ou-diretorio>]

Examples:
  ./run-ocp.sh --artifacts ./artifacts
EOF
}

if [[ $# -eq 0 ]]; then
    usage
    exit 1
fi

if [[ -x "$VENV_DIR/bin/python" ]]; then
    PYTHON_CMD="$VENV_DIR/bin/python"
elif command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_CMD="$PYTHON_BIN"
else
    echo "Error: Python interpreter not found: $PYTHON_BIN" >&2
    exit 1
fi


cd "$ROOT_DIR"

echo "[run-ocp.sh] Running agent via Cursor SDK"
"$PYTHON_CMD" -m agent --llm "$@"