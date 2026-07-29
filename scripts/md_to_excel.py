#!/usr/bin/env python3

import argparse
import pandas as pd
from pathlib import Path


def extract_markdown_tables(md_content):
    """
    Extrai tabelas Markdown do arquivo.
    """
    lines = md_content.splitlines()

    tables = []
    current_table = []

    for line in lines:
        if "|" in line:
            current_table.append(line)
        else:
            if current_table:
                tables.append(current_table)
                current_table = []

    if current_table:
        tables.append(current_table)

    return tables


def markdown_table_to_dataframe(table_lines):
    """
    Converte uma tabela Markdown em DataFrame.
    """

    table_lines = [line.strip() for line in table_lines]

    if len(table_lines) < 2:
        return None

    header = [col.strip() for col in table_lines[0].strip("|").split("|")]

    data = []

    for line in table_lines[2:]:
        row = [col.strip() for col in line.strip("|").split("|")]

        while len(row) < len(header):
            row.append("")

        data.append(row[:len(header)])

    return pd.DataFrame(data, columns=header)


def md_to_xlsx_tables(md_file):
    md_content = Path(md_file).read_text(encoding="utf-8")

    tables = extract_markdown_tables(md_content)

    if not tables:
        print(f"Nenhuma tabela Markdown encontrada em: {md_file}")
        return 0

    md_path = Path(md_file)
    output_dir = md_path.parent / md_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_count = 0

    for idx, table in enumerate(tables, start=1):
        df = markdown_table_to_dataframe(table)

        if df is not None:
            xlsx_file = output_dir / f"tabela{idx}.xlsx"

            with pd.ExcelWriter(xlsx_file, engine="openpyxl") as writer:
                df.to_excel(
                    writer,
                    sheet_name="Tabela",
                    index=False
                )

            generated_count += 1
            print(f"Arquivo gerado: {xlsx_file}")

    if generated_count == 0:
        print(f"Nenhuma tabela valida encontrada em: {md_file}")

    return generated_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Converte tabelas de um arquivo Markdown em planilhas Excel separadas."
    )
    parser.add_argument(
        "--md-file",
        required=True,
        help="Caminho do arquivo Markdown de entrada (.md)."
    )

    args = parser.parse_args()
    md_file = Path(args.md_file)

    if not md_file.exists() or not md_file.is_file():
        print(f"Arquivo nao encontrado: {md_file}")
        raise SystemExit(1)

    if md_file.suffix.lower() != ".md":
        print(f"Arquivo invalido (esperado .md): {md_file}")
        raise SystemExit(1)

    total_generated = md_to_xlsx_tables(md_file)
    print(f"Total de planilhas geradas: {total_generated}")