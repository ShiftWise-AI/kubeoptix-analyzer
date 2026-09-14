"""Renderização de diagramas de arquitetura via KubeDiagrams + Graphviz."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from agent.visualization.png.export_config import layout_profile_for_output
from agent.visualization.png.postprocess import finalize_report_png

logger = logging.getLogger(__name__)

KUBEDIAGRAMS_IMAGE = "docker.io/philippemerle/kubediagrams:latest"
_DEFAULT_TIMEOUT_SECONDS = 180


def bundled_config_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "kube-diagrams.yml"


def find_container_runtime() -> str | None:
    for runtime in ("podman", "docker"):
        if shutil.which(runtime) is not None:
            return runtime
    return None


def is_kubediagrams_available() -> bool:
    if shutil.which("kube-diagrams") is not None and shutil.which("dot") is not None:
        return True
    return find_container_runtime() is not None


def _png_output_ok(output_path: Path) -> bool:
    return output_path.is_file() and output_path.stat().st_size > 0


def _finalize_png(output_path: Path) -> None:
    finalize_report_png(output_path, profile=layout_profile_for_output(output_path))


def _read_generated_dot(requested: Path) -> str | None:
    candidates = (requested, requested.with_suffix(""), requested.with_suffix(".dot"))
    seen: set[Path] = set()
    for path in candidates:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "digraph" in text:
            return text
    return None


def _render_dot_to_png(dot_source: str, output_path: Path) -> bool:
    dot_bin = shutil.which("dot")
    if dot_bin is not None:
        with tempfile.NamedTemporaryFile(
            prefix="kd_layout_",
            suffix=".dot",
            delete=False,
        ) as tmp:
            dot_path = Path(tmp.name)
        try:
            dot_path.write_text(dot_source, encoding="utf-8")
            result = subprocess.run(
                [dot_bin, "-Tpng", "-o", str(output_path), str(dot_path)],
                capture_output=True,
                text=True,
                timeout=_DEFAULT_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("Falha ao renderizar DOT: %s", exc)
            result = None
        finally:
            dot_path.unlink(missing_ok=True)
        if _png_output_ok(output_path):
            if result is not None and result.returncode != 0:
                logger.warning(
                    "dot retornou código %s, mas PNG foi gerado: %s",
                    result.returncode,
                    output_path,
                )
            _finalize_png(output_path)
            return True

    runtime = find_container_runtime()
    if runtime is None:
        return False

    assets_dir = output_path.parent
    dot_name = f".kd_layout_{output_path.stem}.dot"
    host_dot = assets_dir / dot_name
    result = None
    try:
        host_dot.write_text(dot_source, encoding="utf-8")
        command = [
            runtime,
            "run",
            "--rm",
            "-v",
            f"{assets_dir.resolve()}:/out:Z",
            KUBEDIAGRAMS_IMAGE,
            "dot",
            "-Tpng",
            "-o",
            f"/out/{output_path.name}",
            f"/out/{dot_name}",
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=_DEFAULT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Falha ao renderizar DOT via container: %s", exc)
        return False
    finally:
        host_dot.unlink(missing_ok=True)

    if _png_output_ok(output_path):
        if result is not None and result.returncode != 0:
            logger.warning(
                "dot em container retornou código %s, mas PNG foi gerado: %s",
                result.returncode,
                output_path,
            )
        _finalize_png(output_path)
        return True
    return False


def _invoke_local_kube_diagrams(
    manifests: tuple[Path, ...],
    output_path: Path,
    *,
    use_config: bool,
) -> bool:
    executable = shutil.which("kube-diagrams")
    if executable is None:
        return False

    config = bundled_config_path()
    with tempfile.NamedTemporaryFile(
        prefix="kd_dot_",
        suffix=".dot",
        dir=output_path.parent,
        delete=False,
    ) as tmp:
        dot_output = Path(tmp.name)

    try:
        command: list[str] = [
            executable,
            "-f",
            "dot",
            "-o",
            str(dot_output),
        ]
        if use_config and config.is_file():
            command.extend(["-c", str(config)])
        command.extend(str(path) for path in manifests)
        subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=_DEFAULT_TIMEOUT_SECONDS,
            check=False,
        )
        source = _read_generated_dot(dot_output)
        if not source:
            return False
        return _render_dot_to_png(source, output_path)
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError) as exc:
        logger.warning("KubeDiagrams local falhou: %s", exc)
        return False
    finally:
        for path in (dot_output, dot_output.with_suffix("")):
            path.unlink(missing_ok=True)


def _invoke_container_kube_diagrams(
    runtime: str,
    manifests: tuple[Path, ...],
    output_path: Path,
    *,
    use_config: bool,
) -> bool:
    if not manifests:
        return False

    resolved = [path.resolve() for path in manifests]
    work_root = Path(os.path.commonpath([str(path) for path in resolved]))
    if work_root.is_file():
        work_root = work_root.parent

    assets_dir = output_path.parent.resolve()
    container_manifests = [
        f"/work/{path.relative_to(work_root).as_posix()}" for path in resolved
    ]
    container_output = f"/out/{output_path.name}"

    volumes = [
        "-v",
        f"{work_root}:/work:ro,Z",
        "-v",
        f"{assets_dir}:/out:Z",
    ]
    config = bundled_config_path()
    if use_config and config.is_file():
        volumes.extend(["-v", f"{config.parent.resolve()}:/kdconfig:ro,Z"])

    command: list[str] = [
        runtime,
        "run",
        "--rm",
        *volumes,
        KUBEDIAGRAMS_IMAGE,
        "kube-diagrams",
        "-f",
        "png",
        "-o",
        container_output,
    ]
    if use_config and config.is_file():
        command.extend(["-c", "/kdconfig/kube-diagrams.yml"])
    command.extend(container_manifests)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=_DEFAULT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("KubeDiagrams em container falhou: %s", exc)
        return False

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        logger.warning(
            "KubeDiagrams em container retornou código %s: %s",
            result.returncode,
            stderr[:1000] if stderr else "(sem stderr)",
        )

    if _png_output_ok(output_path):
        _finalize_png(output_path)
        return True
    return False


def render_manifests(manifests: tuple[Path, ...], output_path: Path) -> bool:
    """Gera PNG a partir de manifests YAML. Retorna True se bem-sucedido."""
    if not manifests:
        return False
    valid = tuple(path for path in manifests if path.is_file())
    if not valid:
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.unlink(missing_ok=True)

    runtime = find_container_runtime()
    dot_available = shutil.which("dot") is not None

    # Sem Graphviz local: preferir pipeline completo no container (ícones inclusos).
    if not dot_available and runtime is not None:
        if _invoke_container_kube_diagrams(runtime, valid, output_path, use_config=True):
            return True
        if _invoke_container_kube_diagrams(runtime, valid, output_path, use_config=False):
            return True

    if _invoke_local_kube_diagrams(valid, output_path, use_config=True):
        return True
    if _invoke_local_kube_diagrams(valid, output_path, use_config=False):
        return True

    if runtime is not None:
        if _invoke_container_kube_diagrams(runtime, valid, output_path, use_config=True):
            return True
        if _invoke_container_kube_diagrams(runtime, valid, output_path, use_config=False):
            return True
    return False
