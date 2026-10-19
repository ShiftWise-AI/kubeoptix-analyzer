"""Tests for the branch-flow workflow's Bash policy."""

import os
import subprocess
import unittest
from pathlib import Path

import yaml


class BranchFlowTests(unittest.TestCase):
    def test_branch_policy(self) -> None:
        workflow = yaml.safe_load(
            (Path(__file__).resolve().parents[1] / ".github/workflows/branch-limits.yml")
            .read_text()
        )
        script = workflow["jobs"]["check-flow"]["steps"][0]["run"]
        repository = "ShiftWise-AI/kubeoptix-analyzer"
        cases = [
            ("develop", "copilot/fix-security-actions-job", repository, True),
            ("develop", "feature/fix", repository, True),
            ("develop", "copilot/fix", "contributor/fork", True),
            ("develop", "feature/fix", "contributor/fork", True),
            ("main", "develop", repository, True),
            ("main", "develop", "contributor/fork", False),
            ("main", "copilot/fix", repository, False),
            ("main", "feature/fix", repository, False),
            ("develop", "copilot/", repository, False),
            ("develop", "feature/", repository, False),
            ("develop", "other/copilot/fix", repository, False),
            ("develop", "fix", repository, False),
            ("stage", "copilot/fix", repository, False),
            ("", "", repository, True),
        ]
        for base, head, source, allowed in cases:
            with self.subTest(base=base, head=head, source=source):
                result = subprocess.run(
                    ["bash", "-e", "-c", script],
                    env={
                        **os.environ,
                        "BASE_REF": base,
                        "HEAD_REF": head,
                        "HEAD_REPOSITORY": source,
                        "GITHUB_REPOSITORY": repository,
                    },
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(
                    result.returncode, 0 if allowed else 1, result.stdout + result.stderr
                )


if __name__ == "__main__":
    unittest.main()
