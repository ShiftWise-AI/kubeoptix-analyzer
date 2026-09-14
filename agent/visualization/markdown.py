"""Renderização de imagens PNG no relatório Markdown."""

from __future__ import annotations

import base64
import re
from pathlib import Path

_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)(?:\{[^}]*\})?")
_HTML_IMG_RE = re.compile(
    r'(<img\s[^>]*src=")([^"]+)("[^>]*>)',
    re.IGNORECASE,
)


def _normalize_image_path(image_relpath: str) -> str:
    path = image_relpath
    if not path.startswith(("./", "../", "http://", "https://", "data:")):
        path = f"./{path}"
    return path


def png_to_data_uri(image_path: Path) -> str:
    """Converte um PNG em data URI base64 para embutir no Markdown."""
    encoded = base64.standard_b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def markdown_image(title: str, image_relpath: str, *, wide: bool = False) -> str:
    alt = title.replace("[", "").replace("]", "").replace('"', "")
    path = _normalize_image_path(image_relpath)
    if wide:
        return f"![{alt}]({path}){{ width=100% }}"
    return f"![{alt}]({path})"


def embedded_markdown_image(title: str, image_path: Path) -> str:
    """Retorna Markdown com PNG embutido como stream base64 no corpo do arquivo."""
    if not image_path.is_file() or image_path.stat().st_size == 0:
        return "_Visualização indisponível: arquivo de imagem não encontrado._"
    alt = title.replace("[", "").replace("]", "").replace('"', "")
    return f"![{alt}]({png_to_data_uri(image_path)})"


def resolve_local_image(ref: str, *, search_dirs: tuple[Path, ...]) -> Path | None:
    """Resolve uma referência local de imagem a partir de diretórios candidatos."""
    if ref.startswith(("http://", "https://", "data:")):
        return None
    normalized = ref.removeprefix("./")
    basename = Path(normalized).name
    candidates: list[Path] = []
    for base in search_dirs:
        base = base.resolve()
        candidates.extend(
            [
                base / normalized,
                base / "report_assets" / basename,
                base / basename,
            ]
        )
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved
    return None


def embed_markdown_images(
    content: str,
    *,
    markdown_dir: Path,
    assets_dir: Path | None = None,
) -> str:
    """Substitui referências PNG locais por data URIs embutidas no Markdown."""
    search_dirs = (markdown_dir.resolve(),)
    if assets_dir is not None:
        resolved_assets = assets_dir.resolve()
        if resolved_assets not in search_dirs:
            search_dirs = (*search_dirs, resolved_assets)

    def _encode(ref: str) -> str | None:
        image_path = resolve_local_image(ref, search_dirs=search_dirs)
        if image_path is None:
            return None
        return png_to_data_uri(image_path)

    def _replace_md(match: re.Match[str]) -> str:
        alt, ref = match.group(1), match.group(2).strip()
        if ref.startswith("data:image"):
            return match.group(0)
        data_uri = _encode(ref)
        if data_uri is None:
            return ""
        return f"![{alt}]({data_uri})"

    def _replace_html(match: re.Match[str]) -> str:
        prefix, ref, suffix = match.group(1), match.group(2).strip(), match.group(3)
        if ref.startswith("data:image"):
            return match.group(0)
        data_uri = _encode(ref)
        if data_uri is None:
            return ""
        return f"{prefix}{data_uri}{suffix}"

    embedded = _MD_IMAGE_RE.sub(_replace_md, content)
    return _HTML_IMG_RE.sub(_replace_html, embedded)


def strip_unresolvable_image_refs(
    content: str,
    *,
    assets_dir: Path,
) -> str:
    """Remove referências de imagem locais que não existem (ex.: paths inventados pelo LLM)."""

    def _replace_md(match: re.Match[str]) -> str:
        ref = match.group(2).strip()
        if ref.startswith(("http://", "https://", "data:")):
            return match.group(0)
        if resolve_local_image(ref, search_dirs=(assets_dir.resolve(),)) is None:
            return ""
        return match.group(0)

    def _replace_html(match: re.Match[str]) -> str:
        ref = match.group(2).strip()
        if ref.startswith(("http://", "https://", "data:")):
            return match.group(0)
        if resolve_local_image(ref, search_dirs=(assets_dir.resolve(),)) is None:
            return ""
        return match.group(0)

    cleaned = _MD_IMAGE_RE.sub(_replace_md, content)
    cleaned = _HTML_IMG_RE.sub(_replace_html, cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned)


def strip_local_image_refs(content: str) -> str:
    """Remove imagens locais não embutidas (paths relativos que o PDF não resolve)."""

    def _replace_md(match: re.Match[str]) -> str:
        ref = match.group(2).strip()
        if ref.startswith("data:image"):
            return match.group(0)
        if ref.startswith(("http://", "https://")):
            return match.group(0)
        return ""

    def _replace_html(match: re.Match[str]) -> str:
        ref = match.group(2).strip()
        if ref.startswith("data:image"):
            return match.group(0)
        if ref.startswith(("http://", "https://")):
            return match.group(0)
        return ""

    cleaned = _MD_IMAGE_RE.sub(_replace_md, content)
    cleaned = _HTML_IMG_RE.sub(_replace_html, cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned)
