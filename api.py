from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

ALLOWED_MODES = {"local", "llm", "embedded"}
DEFAULT_ASSESSMENT_DIR = Path("data/assessment")
DEFAULT_REPORTS_DIR = Path("/app/data/reports")
WORKNODES_DIRNAME = "worknodes"
EMBEDDED_DISABLED_MSG = (
    "Embedded mode is not available in container or OpenShift environments yet."
)
OPENSHIFT_LLM_DISABLED_MSG = (
    "LLM mode is not available when ENV is set to 'openshift'."
)
INVALID_MODE_MSG = (
    "Request body must include a valid 'mode'. Allowed values: embedded, llm, local."
)


@dataclass
class ExecutionStatus:
    progress: int = 0
    running: bool = False
    phase: str = "idle"
    phase_start_progress: int = 0
    phase_end_progress: int = 0
    phase_started_at: float = 0.0
    phase_window_s: float = 1.0
    updated_at: float = field(default_factory=time.monotonic)


_STATUS_LOCK = threading.Lock()
_STATUS = ExecutionStatus()
_STATUS_STOP_EVENT: threading.Event | None = None
_STATUS_WORKER: threading.Thread | None = None


def _build_command(mode: str, namespace_dir: Path, report_file: Path) -> list[str]:
    script_value = os.getenv("KUBEOPTIX_RUN_SCRIPT", "run-ocp.sh").strip()
    script_path = (ROOT_DIR / script_value).resolve() if not Path(script_value).is_absolute() else Path(script_value)

    if not script_path.exists():
        raise ValueError(f"Run script not found: {script_path}")

    command = [
        "bash",
        str(script_path),
        "--artifacts",
        str(namespace_dir),
        "--mode",
        mode,
        "--report",
        str(report_file),
    ]

    locale = os.getenv("KUBEOPTIX_LOCALE", "").strip()
    if locale:
        command.extend(["--locale", locale])

    return command


def _resolve_mode(mode_value: object) -> str:
    mode = str(mode_value or "").strip().lower()
    if not mode:
        raise ValueError(INVALID_MODE_MSG)
    if mode not in ALLOWED_MODES:
        raise ValueError(INVALID_MODE_MSG)
    return mode


def _is_openshift_env() -> bool:
    return os.getenv("ENV", "").strip().lower() == "openshift"


def _is_container_or_ocp() -> bool:
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        return True
    if Path("/.dockerenv").exists() or Path("/run/.containerenv").exists():
        return True
    return False


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


def _update_status(
    *,
    progress: int | None = None,
    running: bool | None = None,
    phase: str | None = None,
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
        if phase_start_progress is not None:
            _STATUS.phase_start_progress = _clamp_progress(phase_start_progress)
        if phase_end_progress is not None:
            _STATUS.phase_end_progress = _clamp_progress(phase_end_progress)
        if phase_started_at is not None:
            _STATUS.phase_started_at = phase_started_at
        if phase_window_s is not None:
            _STATUS.phase_window_s = max(0.1, phase_window_s)
        _STATUS.updated_at = time.monotonic()


def _set_phase(
    phase: str,
    start_progress: int,
    end_progress: int,
    window_s: float,
) -> None:
    now = time.monotonic()
    with _STATUS_LOCK:
        _STATUS.phase = phase
        _STATUS.phase_start_progress = _clamp_progress(start_progress)
        _STATUS.phase_end_progress = _clamp_progress(end_progress)
        _STATUS.phase_started_at = now
        _STATUS.phase_window_s = max(0.1, window_s)
        _STATUS.progress = max(_STATUS.progress, _STATUS.phase_start_progress)
        _STATUS.running = True
        _STATUS.updated_at = now


def _progress_worker(stop_event: threading.Event) -> None:
    while not stop_event.wait(0.5):
        with _STATUS_LOCK:
            if not _STATUS.running:
                continue
            start_progress = _STATUS.phase_start_progress
            end_progress = _STATUS.phase_end_progress
            phase_started_at = _STATUS.phase_started_at
            phase_window_s = _STATUS.phase_window_s
            current_progress = _STATUS.progress

        if end_progress <= start_progress:
            continue

        elapsed = max(0.0, time.monotonic() - phase_started_at)
        fraction = min(0.95, elapsed / phase_window_s)
        target_progress = start_progress + int((end_progress - start_progress) * fraction)
        target_progress = max(start_progress, min(end_progress, target_progress))

        if target_progress > current_progress:
            _update_status(progress=target_progress)


def _start_progress_tracking() -> None:
    global _STATUS_STOP_EVENT, _STATUS_WORKER
    _STATUS_STOP_EVENT = threading.Event()
    _STATUS_WORKER = threading.Thread(
        target=_progress_worker,
        args=(_STATUS_STOP_EVENT,),
        daemon=True,
    )
    _STATUS_WORKER.start()


def _stop_progress_tracking() -> None:
    global _STATUS_STOP_EVENT, _STATUS_WORKER
    if _STATUS_STOP_EVENT is not None:
        _STATUS_STOP_EVENT.set()
    if _STATUS_WORKER is not None and _STATUS_WORKER.is_alive():
        _STATUS_WORKER.join(timeout=1.0)
    _STATUS_STOP_EVENT = None
    _STATUS_WORKER = None


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


def _report_suffix_for_mode(mode: str) -> str:
    if mode == "local":
        return "-local"
    if mode == "llm":
        return "-llm"
    return ""


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
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_text(self, status_code: int, payload: str) -> None:
        body = payload.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
        if parsed.path in {"/status", "/analysis/status"}:
            self._write_text(200, f"{_snapshot_progress()}\n")
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
            mode = _resolve_mode(request_payload.get("mode"))
            if mode == "llm" and _is_openshift_env():
                raise ValueError(OPENSHIFT_LLM_DISABLED_MSG)
            if mode == "embedded" and _is_container_or_ocp():
                raise ValueError(EMBEDDED_DISABLED_MSG)
            assessment_dir = _resolve_assessment_dir()
            reports_dir = _resolve_reports_dir()
            namespace_dirs = _list_namespace_dirs(assessment_dir)
        except ValueError as exc:
            self._write_json(
                500,
                {"error": str(exc)},
            )
            return

        timeout_s = int(os.getenv("KUBEOPTIX_API_TIMEOUT_S", "7200"))
        progress_window_s = float(os.getenv("KUBEOPTIX_PROGRESS_WINDOW_S", "18"))

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

        _update_status(progress=0, running=True, phase="preparing")
        _start_progress_tracking()

        try:
            _set_phase("validating", 0, 8, progress_window_s * 0.6)

            namespace_count = len(namespace_dirs)
            if namespace_count == 0:
                raise ValueError(f"No namespace directories found under {assessment_dir}")

            _set_phase("preparing", 8, 12, progress_window_s * 0.6)

            base_progress = 12
            final_wrapup_start = 95
            remaining_progress = final_wrapup_start - base_progress
            per_namespace = remaining_progress // namespace_count
            remainder = remaining_progress % namespace_count

            current_start = base_progress

            for index, namespace_dir in enumerate(namespace_dirs):
                namespace_span = per_namespace + (1 if index < remainder else 0)
                namespace_end = current_start + namespace_span
                report_suffix = _report_suffix_for_mode(mode)
                report_file = reports_dir / f"{namespace_dir.name}{report_suffix}.md"
                report_file.parent.mkdir(parents=True, exist_ok=True)

                command = _build_command(mode, namespace_dir, report_file)

                _set_phase(
                    f"analyzing {namespace_dir.name}",
                    current_start,
                    namespace_end,
                    progress_window_s,
                )

                try:
                    completed = subprocess.run(
                        command,
                        cwd=str(ROOT_DIR),
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
                    current_start = namespace_end
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
                    current_start = namespace_end
                    continue

                if completed.returncode != 0:
                    has_error = True

                run_results.append(
                    {
                        "namespace": namespace_dir.name,
                        "report": str(report_file),
                        "command": command,
                        "exit_code": completed.returncode,
                        "stdout": completed.stdout,
                        "stderr": completed.stderr,
                    }
                )

                _update_status(progress=namespace_end)
                current_start = namespace_end

            _set_phase("finalizing", final_wrapup_start, 100, progress_window_s * 0.4)
            _update_status(progress=100, phase="done", running=False)

            payload = {
                "mode": mode,
                "assessment_dir": str(assessment_dir),
                "reports_dir": str(reports_dir),
                "worknodes_dir": str((assessment_dir / WORKNODES_DIRNAME).resolve()),
                "reports": run_results,
            }
            self._write_json(500 if has_error else 200, payload)
        except ValueError as exc:
            _update_status(progress=_snapshot_progress(), phase="error", running=False)
            self._write_json(500, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            _update_status(progress=_snapshot_progress(), phase="error", running=False)
            self._write_json(500, {"error": str(exc)})
        finally:
            _stop_progress_tracking()


def main() -> None:
    host = os.getenv("KUBEOPTIX_API_HOST", "0.0.0.0")
    port = int(os.getenv("KUBEOPTIX_API_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"[api] listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()