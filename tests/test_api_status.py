"""Status reaches 100 only after the markdown report is on disk."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

import api


class FinalizeStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        api._update_status(
            progress=40,
            running=True,
            phase="analyzing shiftwise-ai",
            phase_start_progress=12,
            phase_end_progress=95,
            phase_started_at=time.monotonic(),
            phase_window_s=18,
        )

    def test_missing_report_does_not_finish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports_dir = Path(tmp)
            ready = api.finalize_status_if_reports_ready(
                reports_dir,
                ["shiftwise-ai"],
                final_wrapup_start=95,
                progress_window_s=18,
            )

        self.assertFalse(ready)
        self.assertEqual(api._snapshot_progress(), 40)
        self.assertEqual(api._STATUS.phase, "error")
        self.assertFalse(api._STATUS.running)

    def test_written_report_finishes_at_100(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports_dir = Path(tmp)
            (reports_dir / "shiftwise-ai.md").write_text("# report\n", encoding="utf-8")
            ready = api.finalize_status_if_reports_ready(
                reports_dir,
                ["shiftwise-ai"],
                final_wrapup_start=95,
                progress_window_s=18,
            )

        self.assertTrue(ready)
        self.assertEqual(api._snapshot_progress(), 100)
        self.assertEqual(api._STATUS.phase, "done")
        self.assertFalse(api._STATUS.running)

    def test_report_from_before_run_does_not_finish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports_dir = Path(tmp)
            report_path = reports_dir / "shiftwise-ai.md"
            report_path.write_text("# old report\n", encoding="utf-8")
            old_timestamp = time.time() - 60
            import os

            os.utime(report_path, (old_timestamp, old_timestamp))
            ready = api.finalize_status_if_reports_ready(
                reports_dir,
                ["shiftwise-ai"],
                final_wrapup_start=99,
                progress_window_s=0,
                run_started_at=time.time(),
            )

        self.assertFalse(ready)
        self.assertEqual(api._STATUS.phase, "error")

    def test_partial_reports_do_not_finish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports_dir = Path(tmp)
            (reports_dir / "one.md").write_text("# one\n", encoding="utf-8")
            ready = api.finalize_status_if_reports_ready(
                reports_dir,
                ["one", "two"],
                final_wrapup_start=95,
                progress_window_s=18,
            )
            self.assertEqual(
                api.missing_markdown_reports(reports_dir, ["one", "two"]),
                ["two"],
            )

        self.assertFalse(ready)
        self.assertLess(api._snapshot_progress(), 100)


class ProgressDetailsTests(unittest.TestCase):
    def test_file_progress_is_capped_before_report_completion(self) -> None:
        self.assertEqual(api._file_progress(0, 10), 0)
        self.assertEqual(api._file_progress(5, 10), 49)
        self.assertEqual(api._file_progress(10, 10), 99)

    def test_inventory_ignores_temporary_and_report_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            namespace_dir = Path(tmp) / "namespace"
            (namespace_dir / "resources").mkdir(parents=True)
            (namespace_dir / "resources" / "deployment.yaml").write_text("kind: Deployment")
            (namespace_dir / "resources" / "deployment.yaml.tmp").write_text("")
            (namespace_dir / "assessment-report.md").write_text("# report")
            (namespace_dir / "resources" / "result.lock").write_text("")

            files = api._list_processable_files([namespace_dir])

        self.assertEqual([path.name for path in files], ["deployment.yaml"])

    def test_snapshot_status_includes_current_file_and_phase(self) -> None:
        api._update_status(
            progress=47,
            running=True,
            phase="analyzing deployment",
            current_file="deployment-prod.yaml",
        )

        status = api._snapshot_status()
        self.assertEqual(status["progress"], 47)
        self.assertEqual(status["status"], "running")
        self.assertEqual(status["phase"], "analyzing deployment")
        self.assertEqual(status["current_file"], "deployment-prod.yaml")

    def test_snapshot_status_clamps_to_100_and_uses_null_current_file_when_idle(self) -> None:
        api._update_status(progress=999, running=False, phase="idle", current_file=None)

        status = api._snapshot_status()
        self.assertEqual(status["progress"], 100)
        self.assertEqual(status["status"], "idle")
        self.assertIsNone(status["current_file"])


if __name__ == "__main__":
    unittest.main()
