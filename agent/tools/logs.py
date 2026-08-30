"""Tools for scanning pod logs."""

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
            return f"Path not found: {path}"

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
            return f"No log files found in {path}"

        hits: list[str] = []
        files_scanned = 0
        for log_file in log_files:
            files_scanned += 1
            try:
                text = log_file.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                hits.append(f"{log_file.relative_to(artifacts_dir)}: read failure ({exc})")
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

        header = f"Files scanned: {files_scanned}; hits: {len(hits)}"
        if not hits:
            return header + "\nNo error patterns found."
        return header + "\n" + "\n".join(hits)

    return [
        FunctionTool(
            name="scan_logs",
            description=(
                "Scans pod logs for error patterns (ERROR, Exception, OOM, "
                "CrashLoop, timeout, etc.). Accepts a relative path and optional patterns."
            ),
            parameters=object_schema(
                {
                    "path": {
                        "type": "string",
                        "description": "Log subdirectory or file (default: .)",
                    },
                    "patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of regex patterns; if omitted, default patterns are used",
                    },
                    "max_hits": {
                        "type": "integer",
                        "description": "Maximum number of matching lines to return (default: 50)",
                    },
                }
            ),
            handler=scan_logs,
        )
    ]
