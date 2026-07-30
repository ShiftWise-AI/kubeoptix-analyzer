#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Uso: $0 <arquivo_md_ou_diretório_de_entrada>"
}

if [ "$#" -ne 1 ]; then
    usage
    exit 1
fi

INPUT_PATH="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$INPUT_PATH" ]; then
    INPUT_DIR="$(dirname "$INPUT_PATH")"
    SINGLE_MD_FILE="$INPUT_PATH"
elif [ -d "$INPUT_PATH" ]; then
    INPUT_DIR="$INPUT_PATH"
    SINGLE_MD_FILE=""
else
    echo "Erro: arquivo ou diretório de entrada não encontrado: $INPUT_PATH"
    exit 1
fi

FILES_DIR="$INPUT_DIR/files"
EVENTS_FILE="$FILES_DIR/.inventory_events.tsv"
INVENTORY_FILE="$FILES_DIR/inventario.md"

mkdir -p "$FILES_DIR"
: > "$EVENTS_FILE"

if [ -n "$SINGLE_MD_FILE" ]; then
    md_files=("$SINGLE_MD_FILE")
else
    mapfile -t md_files < <(find "$INPUT_DIR" -type f -name '*.md' ! -path "$FILES_DIR/*" | sort)
fi

if [ ${#md_files[@]} -eq 0 ]; then
    echo "Nenhum arquivo .md encontrado em $INPUT_DIR"
    exit 0
fi

echo "Processando ${#md_files[@]} arquivo(s) Markdown..."

echo "Diretório de entrada: $INPUT_DIR"
echo "Diretório de saída único: $FILES_DIR"

echo

for md_file in "${md_files[@]}"; do
    base_name="$(basename "$md_file")"

    echo "[2/5] Convertendo DOCX: $base_name"
    python3 "$SCRIPT_DIR/md2docx.py" "$md_file"

    echo "[3/5] Convertendo PDF: $base_name"
    python3 "$SCRIPT_DIR/md2pdf.py" "$md_file"

    echo "[4/5] Convertendo Excel: $base_name"
    python3 "$SCRIPT_DIR/md2excel.py" \
        --md-file "$md_file" \
        --files-dir "$FILES_DIR" \
        --inventory-events "$EVENTS_FILE"

done

echo "[5/5] Convertendo imagens e diagramas Mermaid"
python3 "$SCRIPT_DIR/md2images.py" \
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
