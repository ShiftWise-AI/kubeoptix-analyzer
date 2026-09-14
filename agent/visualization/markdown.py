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


def markdown_image(title: str, image_relpath: str, *, wide: bool = False) -> str:
    alt = title.replace("[", "").replace("]", "").replace('"', "")
    path = _normalize_image_path(image_relpath)
    if wide:
        return f"![{alt}]({path}){{ width=100% }}"
    return f"![{alt}]({path})"


def embed_markdown_images(content: str, *, markdown_dir: Path) -> str:
    """Substitui referências PNG locais por data URIs embutidas no Markdown."""

    def _encode(ref: str) -> str | None:
        if ref.startswith(("http://", "https://", "data:")):
            return None
        normalized = ref.removeprefix("./")
        image_path = (markdown_dir / normalized).resolve()
        if not image_path.is_file():
            return None
        encoded = base64.standard_b64encode(image_path.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def _replace_md(match: re.Match[str]) -> str:
        alt, ref = match.group(1), match.group(2).strip()
        data_uri = _encode(ref)
        if data_uri is None:
            return match.group(0)
        return f"![{alt}]({data_uri})"

    def _replace_html(match: re.Match[str]) -> str:
        prefix, ref, suffix = match.group(1), match.group(2).strip(), match.group(3)
        data_uri = _encode(ref)
        if data_uri is None:
            return match.group(0)
        return f"{prefix}{data_uri}{suffix}"

    embedded = _MD_IMAGE_RE.sub(_replace_md, content)
    return _HTML_IMG_RE.sub(_replace_html, embedded)
