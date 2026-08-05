from __future__ import annotations

import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

ALLOWED_MODES = {"local", "llm", "embedded"}
DEFAULT_ASSESSMENT_DIR = Path("/app/data/assessment")
DEFAULT_REPORTS_DIR = Path("/app/data/reports")
WORKNODES_DIRNAME = "worknodes"
EMBEDDED_DISABLED_MSG = (
    "Embedded mode is not available in container or OpenShift environments yet."
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


def _resolve_mode() -> str:
    mode = os.getenv("KUBEOPTIX_MODE", "").strip().lower()
    if not mode:
        raise ValueError("KUBEOPTIX_MODE is required")
    if mode not in ALLOWED_MODES:
        raise ValueError(
            f"Invalid KUBEOPTIX_MODE '{mode}'. Allowed values: {', '.join(sorted(ALLOWED_MODES))}"
        )
    return mode


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
    def _discard_request_body(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length > 0:
            self.rfile.read(content_length)

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

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/run":
            self._write_json(404, {"error": "not found"})
            return
        self._discard_request_body()

        try:
            mode = _resolve_mode()
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