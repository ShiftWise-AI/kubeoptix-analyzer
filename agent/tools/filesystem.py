"""Filesystem tools for exploring artifacts."""

from __future__ import annotations

from pathlib import Path

from agent.tools.base import FunctionTool, object_schema


def _safe_resolve(artifacts_dir: Path, relative_path: str) -> Path:
    """Resolve a relative path and ensure it stays within artifacts_dir."""
    root = artifacts_dir.resolve()
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path outside artifacts directory: {relative_path}") from exc
    return target


def build_filesystem_tools(
    artifacts_dir: Path,
    max_file_chars: int,
) -> list[FunctionTool]:
    def _describe_ns(lines: list[str], ns_dir: Path) -> None:
        """Append namespace content lines (apps, resources, worknodes)."""
        apps_dir = ns_dir / "apps"
        if apps_dir.is_dir():
            for app in sorted(apps_dir.iterdir()):
                if not app.is_dir():
                    continue
                resource_counts: list[str] = []
                for sub in sorted(app.iterdir()):
                    if sub.is_dir():
                        n = sum(1 for _ in sub.rglob("*") if _.is_file())
                        resource_counts.append(f"{sub.name}={n}")
                detail = ", ".join(resource_counts) if resource_counts else "vazio"
                lines.append(f"  app: {app.name} ({detail})")
        resources_dir = ns_dir / "resources"
        if resources_dir.is_dir():
            for sub in sorted(resources_dir.iterdir()):
                if sub.is_dir():
                    n = sum(1 for _ in sub.rglob("*") if _.is_file())
                    lines.append(f"  resources/{sub.name}: {n} arquivos")
        worknodes_dir = ns_dir / "worknodes"
        if worknodes_dir.is_dir():
            n = len(list(worknodes_dir.glob("*.yaml")) + list(worknodes_dir.glob("*.yml")))
            lines.append(f"  worknodes/: {n} arquivos (capacidade dos worker nodes)")

    def list_artifacts(path: str = ".") -> str:
        target = _safe_resolve(artifacts_dir, path)
        if not target.exists():
            return f"Path not found: {path}"
        if target.is_file():
            return f"Arquivo: {path} ({target.stat().st_size} bytes)"

        lines: list[str] = []

        # Single-namespace layout: the target dir itself has resources/ or apps/.
        if (target / "resources").is_dir() or (target / "apps").is_dir():
            lines.append(f"namespace: {target.name}")
            _describe_ns(lines, target)
            return "\n".join(lines)

        # Multi-namespace layout: subdirs are namespaces.
        namespaces = sorted(
            p for p in target.iterdir() if p.is_dir() and not p.name.startswith(".")
        )
        if not namespaces:
            # Fallback: simple listing.
            for child in sorted(target.iterdir()):
                kind = "dir" if child.is_dir() else "file"
                lines.append(f"{kind}\t{child.relative_to(artifacts_dir)}")
            return "\n".join(lines) or "(vazio)"

        # Worknodes at the artifacts root (alongside namespaces).
        worknodes_root = target / "worknodes"
        if worknodes_root.is_dir():
            n = len(list(worknodes_root.glob("*.yaml")) + list(worknodes_root.glob("*.yml")))
            lines.append(f"worknodes/: {n} arquivos (capacidade dos worker nodes)")

        for ns in namespaces:
            if ns.name == "worknodes":
                continue  # already listed above
            lines.append(f"namespace: {ns.name}")
            _describe_ns(lines, ns)
        return "\n".join(lines)

    def read_file(path: str, max_chars: int | None = None) -> str:
        limit = max_chars if max_chars is not None else max_file_chars
        target = _safe_resolve(artifacts_dir, path)
        if not target.is_file():
            return f"File not found: {path}"
        text = target.read_text(encoding="utf-8", errors="replace")
        if len(text) > limit:
            return (
                text[:limit]
                + f"\n\n...[truncado: {len(text)} chars totais, mostrando {limit}]"
            )
        return text

    def find_files(pattern: str = "**/*", path: str = ".") -> str:
        base = _safe_resolve(artifacts_dir, path)
        if not base.exists():
            return f"Path not found: {path}"
        matches = sorted(
            p.relative_to(artifacts_dir).as_posix()
            for p in base.glob(pattern)
            if p.is_file()
        )
        if not matches:
            return f"No files found for pattern: {pattern}"
        # Limit listing size to avoid overflowing the context.
        max_items = 200
        shown = matches[:max_items]
        extra = len(matches) - len(shown)
        out = "\n".join(shown)
        if extra > 0:
            out += f"\n... and {extra} more files"
        return out

    return [
        FunctionTool(
            name="list_artifacts",
            description=(
                "Lists the namespace/application inventory (or the contents of a "
                "subdirectory) under the artifact folder."
            ),
            parameters=object_schema(
                {
                    "path": {
                        "type": "string",
                        "description": "Relative path under the artifacts directory (default: .)",
                    }
                }
            ),
            handler=list_artifacts,
        ),
        FunctionTool(
            name="read_file",
            description="Reads the content of a file (YAML or log) with a size limit.",
            parameters=object_schema(
                {
                    "path": {
                        "type": "string",
                        "description": "Relative path under the artifacts directory",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Optional character limit to return",
                    },
                },
                required=["path"],
            ),
            handler=read_file,
        ),
        FunctionTool(
            name="find_files",
            description="Finds files using a glob pattern (for example: '**/pod-logs/*.log', '**/deployments/*.yaml').",
            parameters=object_schema(
                {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (default: **/*)",
                    },
                    "path": {
                        "type": "string",
                        "description": "Relative subdirectory to start the search from",
                    },
                }
            ),
            handler=find_files,
        ),
    ]
