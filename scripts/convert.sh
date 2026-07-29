#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Uso: $0 <diretório_de_entrada> <diretório_de_saida>"
}

if [ "$#" -ne 2 ]; then
    usage
    exit 1
fi

INPUT_DIR="$1"
OUTPUT_DIR="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$INPUT_DIR" ]; then
    echo "Erro: diretório de entrada não encontrado: $INPUT_DIR"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

mapfile -t md_files < <(find "$INPUT_DIR" -type f -name '*.md' | sort)

if [ ${#md_files[@]} -eq 0 ]; then
    echo "Nenhum arquivo .md encontrado em $INPUT_DIR"
    exit 0
fi

echo "Processando $(printf '%s
' "${md_files[@]}" | wc -l) arquivo(s) Markdown..."

echo "Diretório de entrada: $INPUT_DIR"
echo "Diretório de saída: $OUTPUT_DIR"

echo

for md_file in "${md_files[@]}"; do
    rel_path="${md_file#"$INPUT_DIR"/}"
    rel_dir="$(dirname "$rel_path")"
    target_dir="$OUTPUT_DIR/$rel_dir"
    mkdir -p "$target_dir"

    work_file="$target_dir/$(basename "$md_file")"
    cp "$md_file" "$work_file"

    echo "[1/3] Convertendo DOCX: $(basename "$md_file")"
    python3 "$SCRIPT_DIR/md_to_docx.py" "$work_file"

    echo "[2/3] Convertendo Excel: $(basename "$md_file")"
    python3 "$SCRIPT_DIR/md_to_excel.py" --md-file "$work_file"

done

echo "[3/3] Convertendo imagens e diagramas Mermaid"
python3 "$SCRIPT_DIR/md_to_images.py" "$INPUT_DIR" "$OUTPUT_DIR"

echo

echo "Conversão concluída."
