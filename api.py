from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from agent.system_settings import SettingsLoadError, load_runtime_settings
from agent.visualization.report_postprocess import postprocess_report_file


ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

DEFAULT_ASSESSMENT_DIR = Path("data/assessment")
DEFAULT_REPORTS_DIR = Path("/app/data/reports")
WORKNODES_DIRNAME = "worknodes"
INVALID_NAMESPACES_MSG = (
    "Request body must include 'namespaces' with one or more namespace names."
)


@dataclass
class ExecutionStatus:
    progress: int = 0
    running: bool = False
    phase: str = "idle"
    current_file: str | None = None
    files_total: int = 0
    files_processed: int = 0


_STATUS_LOCK = threading.Lock()
_STATUS = ExecutionStatus()
_STATUS_NO_VALUE = object()

_PROCESSABLE_SUFFIXES = {".json", ".log", ".txt", ".yaml", ".yml"}
_IGNORED_FILE_NAMES = {".gitkeep"}
_IGNORED_DIR_NAMES = {".git", "report_assets", "tmp", "temp"}


def _build_command(namespace_dir: Path, report_file: Path) -> list[str]:
    script_value = os.getenv("KUBEOPTIX_RUN_SCRIPT", "run-ocp.sh").strip()
    script_path = (ROOT_DIR / script_value).resolve() if not Path(script_value).is_absolute() else Path(script_value)

    if not script_path.exists():
        raise ValueError(f"Run script not found: {script_path}")

    command = [
        "bash",
        str(script_path),
        "--artifacts",
        str(namespace_dir),
        "--report",
        str(report_file),
    ]

    return command


def _resolve_namespaces(namespaces_value: object) -> list[str]:
    if isinstance(namespaces_value, str):
        items = [item.strip() for item in namespaces_value.split(",")]
    elif isinstance(namespaces_value, list):
        items = [str(item).strip() for item in namespaces_value]
    else:
        raise ValueError(INVALID_NAMESPACES_MSG)

    names = [item for item in items if item]
    if not names:
        raise ValueError(INVALID_NAMESPACES_MSG)

    # Preserve order and remove duplicates.
    return list(dict.fromkeys(names))


def _select_namespace_dirs(namespace_dirs: list[Path], namespace_names: list[str]) -> list[Path]:
    by_name = {ns_dir.name: ns_dir for ns_dir in namespace_dirs}
    missing = [name for name in namespace_names if name not in by_name]
    if missing:
        available = ", ".join(sorted(by_name))
        missing_list = ", ".join(missing)
        raise ValueError(
            f"Namespaces not found: {missing_list}. Available namespaces: {available}"
        )
    return [by_name[name] for name in namespace_names]


def _resolve_assessment_dir() -> Path:
    return DEFAULT_ASSESSMENT_DIR.resolve()


def _resolve_reports_dir() -> Path:
    return DEFAULT_REPORTS_DIR.resolve()


def _clear_reports_dir(reports_dir: Path) -> list[str]:
    reports_dir.mkdir(parents=True, exist_ok=True)

    deleted_entries: list[str] = []
    for child in sorted(reports_dir.iterdir()):
        deleted_entries.append(child.name)
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
            continue
        child.unlink()

    return deleted_entries


def _clamp_progress(value: int) -> int:
    return max(0, min(100, value))


def _snapshot_progress() -> int:
    with _STATUS_LOCK:
        return _STATUS.progress


def _status_value() -> str:
    if _STATUS.phase == "error":
        return "error"
    if _STATUS.running:
        return "running"
    if _STATUS.phase == "done":
        return "done"
    return "idle"


def _snapshot_status() -> dict[str, object]:
    with _STATUS_LOCK:
        phase = _STATUS.phase
        progress = _clamp_progress(_STATUS.progress)
        status = _status_value()
        current_file = _STATUS.current_file
        return {
            "progress": progress,
            "status": status,
            "phase": phase,
            "current_file": current_file,
            "running": _STATUS.running,
            "files_total": _STATUS.files_total,
            "files_processed": _STATUS.files_processed,
        }


def _update_status(
    *,
    progress: int | None = None,
    running: bool | None = None,
    phase: str | None = None,
    current_file: str | None | object = _STATUS_NO_VALUE,
    phase_start_progress: int | None = None,
    phase_end_progress: int | None = None,
    phase_started_at: float | None = None,
    phase_window_s: float | None = None,
) -> None:
    with _STATUS_LOCK:
        if progress is not None:
            _STATUS.progress = _clamp_progress(progress)
        if running is not None:
            _STATUS.running = running
        if phase is not None:
            _STATUS.phase = phase
        if current_file is not _STATUS_NO_VALUE:
            _STATUS.current_file = current_file or None


def _list_namespace_dirs(assessment_dir: Path) -> list[Path]:
    if not assessment_dir.is_dir():
        raise ValueError(f"Assessment directory not found: {assessment_dir}")

    namespaces: list[Path] = []
    for child in sorted(assessment_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name == WORKNODES_DIRNAME:
            continue
        namespaces.append(child)

    if not namespaces:
        raise ValueError(
            f"No namespace directories found under {assessment_dir}"
        )

    return namespaces


def _is_processable_file(path: Path) -> bool:
    return (
        path.is_file()
        and path.name not in _IGNORED_FILE_NAMES
        and not path.name.startswith((".", "~"))
        and not path.name.endswith((".tmp", ".partial", ".lock"))
        and path.suffix.lower() in _PROCESSABLE_SUFFIXES
    )


def _list_processable_files(namespace_dirs: list[Path]) -> list[Path]:
    files: list[Path] = []
    for namespace_dir in namespace_dirs:
        if not namespace_dir.is_dir():
            continue
        for path in sorted(namespace_dir.rglob("*")):
            relative_parts = path.relative_to(namespace_dir).parts
            if any(part in _IGNORED_DIR_NAMES for part in relative_parts[:-1]):
                continue
            if _is_processable_file(path):
                files.append(path.resolve())
    return files


def _file_progress(processed: int, total: int) -> int:
    if total <= 0:
        return 0
    return min(99, max(0, int(processed * 99 / total)))


def _update_file_progress(
    *,
    files_processed: int,
    files_total: int,
    current_file: str | None | object = _STATUS_NO_VALUE,
) -> None:
    with _STATUS_LOCK:
        _STATUS.files_processed = max(0, files_processed)
        _STATUS.files_total = max(0, files_total)
        _STATUS.progress = max(
            _STATUS.progress,
            _file_progress(files_processed, files_total),
        )
    _update_status(current_file=current_file)


def _list_assessment_folder_names(assessment_dir: Path) -> list[str]:
    if not assessment_dir.is_dir():
        raise ValueError(f"Assessment directory not found: {assessment_dir}")

    folder_names: list[str] = []
    for child in sorted(assessment_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name == WORKNODES_DIRNAME:
            continue
        folder_names.append(child.name)

    return folder_names


def _resolve_file_created_at(path: Path) -> datetime:
    stat_result = path.stat()
    created_ts = getattr(stat_result, "st_birthtime", None)
    if created_ts is None:
        # Linux usually does not expose birth time; ctime is the best available fallback.
        created_ts = stat_result.st_ctime
    return datetime.fromtimestamp(created_ts).astimezone()


def missing_markdown_reports(reports_dir: Path, namespace_names: list[str]) -> list[str]:
    """Namespaces whose non-empty ``<name>.md`` report is not on disk yet."""
    missing: list[str] = []
    for name in namespace_names:
        report_path = reports_dir / f"{name}.md"
        if not report_path.is_file() or report_path.stat().st_size == 0:
            missing.append(name)
    return missing


def finalize_status_if_reports_ready(
    reports_dir: Path,
    namespace_names: list[str],
    *,
    final_wrapup_start: int,
    progress_window_s: float,
) -> bool:
    """Reach 100 / done only after every namespace markdown file exists.

    A finished subprocess is not enough: the status stays below 100 when the
    report was not written, so clients do not treat a missing file as ready.
    """
    missing = missing_markdown_reports(reports_dir, namespace_names)
    if missing:
        print(f"[api] Markdown report not written for: {', '.join(missing)}")
        _update_status(phase="error", running=False, current_file=None)
        return False

    _update_status(progress=100, phase="done", running=False, current_file=None)
    return True


def _list_report_files_with_dates(reports_dir: Path) -> list[dict[str, str]]:
    reports_dir.mkdir(parents=True, exist_ok=True)

    files: list[dict[str, str]] = []
    for child in sorted(reports_dir.iterdir()):
        if not child.is_file() or child.name.startswith("."):
            continue
        created_at = _resolve_file_created_at(child)
        files.append(
            {
                "name": child.name,
                "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S %z"),
                "created_at_iso": created_at.isoformat(),
            }
        )

    return files


class ApiHandler(BaseHTTPRequestHandler):
    def _read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length <= 0:
            return {}

        raw_body = self.rfile.read(content_length)
        if not raw_body:
            return {}

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Request body must be valid JSON.") from exc

        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        return payload

    def _write_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        try:
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            print("[api] client disconnected before JSON response was sent")

    def _write_text(self, status_code: int, payload: str) -> None:
        body = payload.encode("utf-8")
        try:
            self.send_response(status_code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            print("[api] client disconnected before text response was sent")

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        # Silence noisy health probes while keeping logs for other endpoints.
        path = urlparse(self.path).path
        if path == "/health":
            return
        super().log_request(code, size)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._write_json(200, {"status": "ok"})
            return
        if parsed.path == "/status":
            self._write_text(200, f"{_snapshot_progress()}\n")
            return
        if parsed.path == "/analysis/status":
            self._write_json(200, _snapshot_status())
            return
        if parsed.path in {"/reports", "/reports/files"}:
            reports_dir = _resolve_reports_dir()
            files = _list_report_files_with_dates(reports_dir)
            self._write_json(
                200,
                {
                    "reports_dir": str(reports_dir),
                    "count": len(files),
                    "files": files,
                },
            )
            return
        if parsed.path in {"/assessment/folders", "/assessment/namespaces"}:
            try:
                assessment_dir = _resolve_assessment_dir()
                folder_names = _list_assessment_folder_names(assessment_dir)
            except ValueError as exc:
                self._write_json(500, {"error": str(exc)})
                return

            self._write_json(
                200,
                {
                    "assessment_dir": str(assessment_dir),
                    "count": len(folder_names),
                    "folders": folder_names,
                },
            )
            return
        self._write_json(404, {"error": "not found"})

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/reports":
            self._write_json(404, {"error": "not found"})
            return

        reports_dir = _resolve_reports_dir()
        deleted_entries = _clear_reports_dir(reports_dir)
        self._write_json(
            200,
            {
                "status": "ok",
                "reports_dir": str(reports_dir),
                "deleted_count": len(deleted_entries),
                "deleted_entries": deleted_entries,
            },
        )

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/run":
            self._write_json(404, {"error": "not found"})
            return

        try:
            request_payload = self._read_json_body()
            namespaces_value = request_payload.get(
                "namespaces",
                request_payload.get("--namespaces"),
            )

            namespace_names = _resolve_namespaces(namespaces_value)

            assessment_dir = _resolve_assessment_dir()
            reports_dir = _resolve_reports_dir()
            all_namespace_dirs = _list_namespace_dirs(assessment_dir)
            namespace_dirs = _select_namespace_dirs(all_namespace_dirs, namespace_names)
        except ValueError as exc:
            self._write_json(
                500,
                {"error": str(exc)},
            )
            return

        timeout_s = int(os.getenv("KUBEOPTIX_API_TIMEOUT_S", "7200"))
        with _STATUS_LOCK:
            if _STATUS.running:
                self._write_json(
                    409,
                    {
                        "error": "analysis already running",
                        "progress": _STATUS.progress,
                    },
                )
                return

        run_results: list[dict] = []
        has_error = False
        reports_dir.mkdir(parents=True, exist_ok=True)

        try:
            load_runtime_settings()
        except SettingsLoadError as exc:
            self._write_json(500, {"error": str(exc)})
            return

        _update_status(
            progress=0,
            running=True,
            phase="preparing",
            current_file=None,
        )

        try:
            namespace_count = len(namespace_dirs)
            if namespace_count == 0:
                raise ValueError(f"No namespace directories found under {assessment_dir}")

            tracked_files = set(_list_processable_files(namespace_dirs))
            processed_files: set[Path] = set()
            _update_file_progress(
                files_processed=0,
                files_total=len(tracked_files),
                current_file=None,
            )

            for namespace_dir in namespace_dirs:
                report_file = reports_dir / f"{namespace_dir.name}.md"
                report_file.parent.mkdir(parents=True, exist_ok=True)

                namespace_files = [
                    path for path in sorted(tracked_files)
                    if namespace_dir in path.parents
                ]
                current_file = namespace_files[0].name if namespace_files else None
                _update_status(
                    phase=f"analyzing {namespace_dir.name}",
                    current_file=current_file,
                )

                command = _build_command(namespace_dir, report_file)

                try:
                    completed = subprocess.run(
                        command,
                        cwd=str(ROOT_DIR),
                        env=os.environ.copy(),
                        capture_output=True,
                        text=True,
                        timeout=timeout_s,
                        check=False,
                    )
                except subprocess.TimeoutExpired as exc:
                    has_error = True
                    run_results.append(
                        {
                            "namespace": namespace_dir.name,
                            "report": str(report_file),
                            "command": command,
                            "exit_code": None,
                            "error": "execution timeout",
                            "timeout_s": timeout_s,
                            "stdout": exc.stdout or "",
                            "stderr": exc.stderr or "",
                        }
                    )
                    _update_status(
                        phase=f"analyzing {namespace_dir.name}",
                        current_file=current_file,
                    )
                    continue
                except OSError as exc:
                    has_error = True
                    run_results.append(
                        {
                            "namespace": namespace_dir.name,
                            "report": str(report_file),
                            "command": command,
                            "exit_code": None,
                            "error": f"failed to execute script: {exc}",
                            "stdout": "",
                            "stderr": "",
                        }
                    )
                    _update_status(
                        phase=f"analyzing {namespace_dir.name}",
                        current_file=current_file,
                    )
                    continue

                if completed.returncode != 0:
                    has_error = True

                result = {
                    "namespace": namespace_dir.name,
                    "report": str(report_file),
                    "command": command,
                    "exit_code": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                }
                if report_file.is_file() and report_file.stat().st_size > 0:
                    postprocess = postprocess_report_file(report_file, namespace_dir)
                    print(
                        f"[api] Post-processed {report_file.name}: "
                        f"{postprocess['embedded']} PNG(s) embedded, "
                        f"removed scripts={postprocess['removed_scripts']}"
                    )
                    tracked_files.update(
                        path
                        for path in _list_processable_files(namespace_dirs)
                        if path not in tracked_files
                    )
                    processed_files.update(
                        path for path in tracked_files if namespace_dir in path.parents
                    )
                    _update_file_progress(
                        files_processed=len(processed_files),
                        files_total=len(tracked_files),
                        current_file=None,
                    )
                else:
                    has_error = True
                    result["error"] = "markdown report was not written"
                    print(f"[api] Markdown report was not written: {report_file}")

                run_results.append(result)

            if not finalize_status_if_reports_ready(
                reports_dir,
                [namespace_dir.name for namespace_dir in namespace_dirs],
                final_wrapup_start=99,
                progress_window_s=0,
            ):
                has_error = True

            payload = {
                "namespaces": [ns.name for ns in namespace_dirs],
                "assessment_dir": str(assessment_dir),
                "reports_dir": str(reports_dir),
                "worknodes_dir": str((assessment_dir / WORKNODES_DIRNAME).resolve()),
                "reports": run_results,
                "status": _snapshot_status(),
            }
            self._write_json(500 if has_error else 200, payload)
        except ValueError as exc:
            _update_status(
                progress=_snapshot_progress(),
                phase="error",
                running=False,
                current_file=None,
            )
            self._write_json(500, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            _update_status(
                progress=_snapshot_progress(),
                phase="error",
                running=False,
                current_file=None,
            )
            self._write_json(500, {"error": str(exc)})
        finally:
            with _STATUS_LOCK:
                if _STATUS.running:
                    _STATUS.running = False


def main() -> None:
    host = os.getenv("KUBEOPTIX_API_HOST", "0.0.0.0")
    port = int(os.getenv("KUBEOPTIX_API_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"[api] listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()