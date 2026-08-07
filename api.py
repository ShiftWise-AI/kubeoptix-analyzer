from __future__ import annotations

import json
import os
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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

        run_results: list[dict] = []
        has_error = False
        reports_dir.mkdir(parents=True, exist_ok=True)

        for namespace_dir in namespace_dirs:
            report_file = reports_dir / f"{namespace_dir.name}.md"
            report_file.parent.mkdir(parents=True, exist_ok=True)

            try:
                command = _build_command(mode, namespace_dir, report_file)
            except ValueError as exc:
                self._write_json(500, {"error": str(exc)})
                return

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

        payload = {
            "mode": mode,
            "assessment_dir": str(assessment_dir),
            "reports_dir": str(reports_dir),
            "worknodes_dir": str((assessment_dir / WORKNODES_DIRNAME).resolve()),
            "reports": run_results,
        }
        self._write_json(500 if has_error else 200, payload)


def main() -> None:
    host = os.getenv("KUBEOPTIX_API_HOST", "0.0.0.0")
    port = int(os.getenv("KUBEOPTIX_API_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"[api] listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()