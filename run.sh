#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

usage() {
    cat <<'EOF'
Usage:
  ./run.sh --artifacts <diretorio> [--report <arquivo-ou-diretorio>] [--mode local|llm|embedded]

Examples:
  ./run.sh --artifacts ./artifacts
  ./run.sh --artifacts ./artifacts --mode llm
  ./run.sh --artifacts ./artifacts --mode embedded
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

if [[ ! -d "$VENV_DIR" ]]; then
  echo "[run.sh] Creating virtual environment at $VENV_DIR"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "[run.sh] Installing dependencies"
python -m pip install --upgrade pip
python -m pip install -r "$ROOT_DIR/requirements.txt"

cd "$ROOT_DIR"

echo "[run.sh] Running agent"
python -m agent "$@"