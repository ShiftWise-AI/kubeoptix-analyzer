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


if __name__ == "__main__":
    unittest.main()
