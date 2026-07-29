#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Uso: $0 <diretório_de_entrada>"
}

if [ "$#" -ne 1 ]; then
    usage
    exit 1
fi

INPUT_DIR="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FILES_DIR="$INPUT_DIR/files"
EVENTS_FILE="$FILES_DIR/.inventory_events.tsv"
INVENTORY_FILE="$FILES_DIR/inventario.md"

if [ ! -d "$INPUT_DIR" ]; then
    echo "Erro: diretório de entrada não encontrado: $INPUT_DIR"
    exit 1
fi

mkdir -p "$FILES_DIR"
: > "$EVENTS_FILE"

mapfile -t md_files < <(find "$INPUT_DIR" -type f -name '*.md' ! -path "$FILES_DIR/*" | sort)

if [ ${#md_files[@]} -eq 0 ]; then
    echo "Nenhum arquivo .md encontrado em $INPUT_DIR"
    exit 0
fi

echo "Processando ${#md_files[@]} arquivo(s) Markdown..."

echo "Diretório de entrada: $INPUT_DIR"
echo "Diretório de saída único: $FILES_DIR"

echo

for md_file in "${md_files[@]}"; do
    echo "[2/3] Convertendo Excel: $(basename "$md_file")"
    python3 "$SCRIPT_DIR/md_to_excel.py" \
        --md-file "$md_file" \
        --files-dir "$FILES_DIR" \
        --inventory-events "$EVENTS_FILE"

done

echo "[3/3] Convertendo imagens e diagramas Mermaid"
python3 "$SCRIPT_DIR/md_to_images.py" \
    "$INPUT_DIR" \
    "$FILES_DIR" \
    --inventory-events "$EVENTS_FILE"

{
    echo "| nome_arquivo_gerado | origem | hash_m5 |"
    echo "|---|---|---|"
    if [ -s "$EVENTS_FILE" ]; then
        awk -F '\t' '!seen[$1]++ { rows[$1]=$0 } END { for (k in rows) print rows[k] }' "$EVENTS_FILE" \
            | sort \
            | awk -F '\t' '{ printf "| %s | %s | %s |\n", $1, $2, $3 }'
    fi
} > "$INVENTORY_FILE"

echo

echo "Conversão concluída."
echo "Inventário gerado: $INVENTORY_FILE"
