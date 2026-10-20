import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml


spec = importlib.util.spec_from_file_location(
    "ci_pipeline", Path(__file__).resolve().parents[1] / "scripts/ci_pipeline.py"
)
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)


class PipelineTests(unittest.TestCase):
    def test_operator_token_does_not_gate_quay_release(self):
        root = Path(__file__).resolve().parents[1]
        workflow = yaml.safe_load(
            (root / ".github/workflows/ci-release.yml").read_text()
        )
        release = workflow["jobs"]["release"]
        self.assertEqual(
            release["env"]["OPERATOR_TOKEN_AVAILABLE"],
            "${{ secrets.OPERATOR_TOKEN != '' }}",
        )

        credential_step = next(
            step for step in release["steps"]
            if step.get("name") == "Check credentials before reserving a release"
        )
        self.assertEqual(
            set(credential_step["env"]), {"QUAY_USERNAME", "QUAY_PASSWORD"}
        )
        self.assertIn("for name in QUAY_USERNAME QUAY_PASSWORD; do", credential_step["run"])

        operator_steps = [
            step for step in release["steps"]
            if step.get("with", {}).get("repository") == "ShiftWise-AI/kubeoptix-operator"
            or step.get("name") in (
                "Set up Go for Operator validation",
                "Open or resume validated Operator PR",
            )
        ]
        self.assertEqual(len(operator_steps), 3)
        for step in operator_steps:
            self.assertEqual(step["if"], "env.OPERATOR_TOKEN_AVAILABLE == 'true'")

    def test_next_version_uses_highest_patch_release(self):
        self.assertEqual(pipeline.next_version("1.0.0", ["1.0.2", "1.0.5"]), "1.0.6")
        self.assertEqual(pipeline.next_version("1.2.4", []), "1.2.5")
        with self.assertRaises(ValueError):
            pipeline.next_version("1.0.0", ["2.0.0"])

    def test_chart_version_updates_only_four_version_fields(self):
        root = Path(__file__).resolve().parents[1]
        chart_text = (root / "helm/kubeoptix-analyzer/Chart.yaml").read_text()
        values_text = (root / "helm/kubeoptix-analyzer/values.yaml").read_text()
        updated_chart, updated_values = pipeline.replace_chart_version(
            chart_text, values_text, "1.0.6"
        )
        chart = yaml.safe_load(updated_chart)
        values = yaml.safe_load(updated_values)
        self.assertEqual(chart["version"], "1.0.6")
        self.assertEqual(chart["appVersion"], "1.0.6")
        self.assertEqual(values["image"]["tag"], "1.0.6")
        self.assertEqual(values["build"]["outputTag"], "1.0.6")
        self.assertEqual(values["image"]["repository"], pipeline.IMAGE)
        self.assertIn("pullPolicy: Always", updated_values)

    def test_chart_version_refuses_drift(self):
        root = Path(__file__).resolve().parents[1]
        chart_text = (root / "helm/kubeoptix-analyzer/Chart.yaml").read_text()
        values_text = (root / "helm/kubeoptix-analyzer/values.yaml").read_text()
        drifted_values = values_text.replace("tag: 1.0.0", "tag: 0.9.0", 1)
        with self.assertRaises(ValueError):
            pipeline.replace_chart_version(chart_text, drifted_values, "1.0.6")

    def test_operator_image_update_is_scoped_and_idempotent(self):
        original = (
            "AnalyzerImage: registryImage(constants.AnalyzerName),\n"
            "CoreAIImage: registryImage(constants.CoreAIName),\n"
        )
        reference = pipeline.IMAGE + ":1.0.6@sha256:" + "a" * 64
        updated = pipeline.operator_image(original, reference)
        self.assertIn(f'AnalyzerImage: "{reference}",', updated)
        self.assertIn("CoreAIImage: registryImage(constants.CoreAIName),", updated)
        self.assertEqual(pipeline.operator_image(updated, reference), updated)
        with self.assertRaises(ValueError):
            pipeline.operator_image("unexpected contract", reference)

    def test_release_reservation_survives_fresh_checkout(self):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / "remote.git"
            first = root / "first"
            second = root / "second"
            subprocess.check_call(["git", "init", "--bare", str(remote)], stdout=subprocess.DEVNULL)
            subprocess.check_call(["git", "clone", str(remote), str(first)], stdout=subprocess.DEVNULL)
            try:
                os.chdir(first)
                pipeline.run("git", "config", "user.name", "CI Test")
                pipeline.run("git", "config", "user.email", "ci@example.invalid")
                chart_path = Path(pipeline.CHART_PATH)
                values_path = Path(pipeline.VALUES_PATH)
                chart_path.parent.mkdir(parents=True)
                values_path.write_text(
                    "image:\n  repository: quay.io/parraes/kubeoptix-analyzer\n"
                    "  tag: 1.0.0\nbuild:\n  outputTag: 1.0.0\n"
                )
                chart_path.write_text(
                    "apiVersion: v2\nname: kubeoptix-analyzer\nversion: 1.0.0\n"
                    'appVersion: "1.0.0"\n'
                )
                pipeline.run("git", "add", pipeline.CHART_PATH, pipeline.VALUES_PATH)
                pipeline.run("git", "commit", "-m", "Initial source")
                pipeline.run("git", "branch", "-M", "main")
                pipeline.run("git", "tag", "v1.0.5")
                pipeline.run("git", "push", "origin", "HEAD:refs/heads/main", "--tags")
                source = pipeline.run("git", "rev-parse", "HEAD")
                with patch.object(pipeline, "verify_source"), patch.object(pipeline, "output") as first_output:
                    pipeline.reserve(source)
                self.assertEqual(first_output.call_args.kwargs["version"], "1.0.6")
                subprocess.check_call(
                    ["git", "clone", "--branch", "main", str(remote), str(second)],
                    stdout=subprocess.DEVNULL,
                )
                os.chdir(second)
                with patch.object(pipeline, "verify_source"), patch.object(pipeline, "output") as second_output:
                    pipeline.reserve(source)
                self.assertEqual(first_output.call_args, second_output.call_args)
                self.assertIn("v1.0.6", pipeline.run("git", "tag", "--list"))
                self.assertEqual(yaml.safe_load(Path(pipeline.CHART_PATH).read_text())["version"], "1.0.6")
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()