"""Tools para escanear logs de pods."""

from __future__ import annotations

import re
from pathlib import Path

from agent.tools.base import FunctionTool, object_schema
from agent.tools.filesystem import _safe_resolve

DEFAULT_PATTERNS = [
    r"ERROR",
    r"Error",
    r"Exception",
    r"FATAL",
    r"OOM",
    r"OutOfMemory",
    r"CrashLoop",
    r"Back-off",
    r"timeout",
    r"Timeout",
    r"denied",
    r"Traceback",
]


def build_log_tools(artifacts_dir: Path) -> list[FunctionTool]:
    def scan_logs(
        path: str = ".",
        patterns: list[str] | None = None,
        max_hits: int = 50,
    ) -> str:
        base = _safe_resolve(artifacts_dir, path)
        if not base.exists():
            return f"Path não encontrado: {path}"

        regexes = [re.compile(p) for p in (patterns or DEFAULT_PATTERNS)]
        log_files: list[Path]
        if base.is_file():
            log_files = [base]
        else:
            log_files = sorted(
                p
                for p in base.rglob("*")
                if p.is_file()
                and (
                    "pod-logs" in p.parts
                    or p.suffix in {".log", ".txt"}
                    or p.name.endswith(".log")
                )
            )

        if not log_files:
            return f"Nenhum arquivo de log encontrado em {path}"

        hits: list[str] = []
        files_scanned = 0
        for log_file in log_files:
            files_scanned += 1
            try:
                text = log_file.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                hits.append(f"{log_file.relative_to(artifacts_dir)}: falha ao ler ({exc})")
                continue

            rel = log_file.relative_to(artifacts_dir).as_posix()
            for lineno, line in enumerate(text.splitlines(), start=1):
                if any(r.search(line) for r in regexes):
                    snippet = line.strip()
                    if len(snippet) > 300:
                        snippet = snippet[:300] + "..."
                    hits.append(f"{rel}:{lineno}: {snippet}")
                    if len(hits) >= max_hits:
                        break
            if len(hits) >= max_hits:
                break

        header = f"Arquivos escaneados: {files_scanned}; hits: {len(hits)}"
        if not hits:
            return header + "\nNenhum padrão de erro encontrado."
        return header + "\n" + "\n".join(hits)

    return [
        FunctionTool(
            name="scan_logs",
            description=(
                "Escaneia logs de pods por padrões de erro (ERROR, Exception, OOM, "
                "CrashLoop, timeout, etc.). Aceita path relativo e patterns opcionais."
            ),
            parameters=object_schema(
                {
                    "path": {
                        "type": "string",
                        "description": "Subdiretório ou arquivo de log (default: .)",
                    },
                    "patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista opcional de regex; se omitida usa padrões padrão",
                    },
                    "max_hits": {
                        "type": "integer",
                        "description": "Máximo de linhas de hit a retornar (default: 50)",
                    },
                }
            ),
            handler=scan_logs,
        )
    ]
