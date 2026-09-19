"""Report language selection and translated Markdown output."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.analysis.action_plan import render_action_plan_md
from agent.analysis.configmaps_security import (
    ConfigMapSecurityResult,
    analyze_configmaps,
    render_configmaps_md,
)
from agent.analysis.discovery import NamespaceArtifacts
from agent.analysis.findings import FindingsResult, analyze_findings
from agent.analysis.observability import ObservabilityResult, render_observability_md
from agent.analysis.operators import OperatorsResult, render_operators_md
from agent.analysis.references import render_references_md
from agent.analysis.resources import ResourceAnalysis, render_resources_md
from agent.analysis.topology import TopologyResult, render_topology_md
from agent.i18n import (
    SUPPORTED_LANGUAGES,
    clear_report_language,
    get_report_language,
    set_report_language,
    t,
)
from agent.i18n import UnsupportedLanguageError
from agent.prompts import build_cursor_prompt, build_system_prompt
from agent.report import ReportBuilder
from agent.system_settings import SettingsLoadError, SystemSettings, load_runtime_settings
from agent.visualization.pregenerate import (
    NamespaceVisualizations,
    format_visualization_catalog,
)


class ReportLanguageTests(unittest.TestCase):
    def tearDown(self) -> None:
        clear_report_language()

    def test_rejects_unsupported_language(self) -> None:
        for value in ("", "pt", "en", "fr", "pt_br"):
            with self.assertRaises(UnsupportedLanguageError):
                set_report_language(value)

    def test_normalizes_case(self) -> None:
        self.assertEqual(set_report_language("EN-US"), "en-us")
        self.assertEqual(get_report_language(), "en-us")

    def test_report_shell_uses_each_language(self) -> None:
        titles = {
            "pt-br": "Relatório de assessment OpenShift",
            "en-us": "OpenShift assessment report",
            "es": "Informe de evaluación de OpenShift",
            "it": "Report di valutazione OpenShift",
        }
        for code, title in titles.items():
            set_report_language(code)
            rendered = ReportBuilder(artifacts_dir=Path("/tmp/artifacts")).render()
            self.assertIn(title, rendered)
            for other, other_title in titles.items():
                if other != code:
                    self.assertNotIn(other_title, rendered)

    def test_prompts_follow_language(self) -> None:
        markers = {
            "pt-br": "português do Brasil",
            "en-us": "English (United States)",
            "es": "español de España",
            "it": "in italiano",
        }
        for code, marker in markers.items():
            set_report_language(code)
            system = build_system_prompt()
            cursor = build_cursor_prompt("/tmp/report.md")
            self.assertIn(marker, system)
            self.assertIn(marker, cursor)
            self.assertIn("/tmp/report.md", cursor)
            self.assertNotIn("{report_path}", cursor)

    def test_visualization_catalog_headings(self) -> None:
        viz = NamespaceVisualizations("demo", "topo", "mem", "cpu", "ea", "ec")
        expected = {
            "pt-br": "diagrama de arquitetura",
            "en-us": "architecture diagram",
            "es": "diagrama de arquitectura",
            "it": "diagramma di architettura",
        }
        for code, heading in expected.items():
            set_report_language(code)
            catalog = format_visualization_catalog([viz])
            self.assertIn(heading, catalog)
            self.assertIn(t("viz.intro"), catalog)

    def test_deterministic_sections_render_in_each_language(self) -> None:
        findings = FindingsResult()
        resources = ResourceAnalysis()
        obs = ObservabilityResult()
        cms = ConfigMapSecurityResult()
        topo = TopologyResult()
        operators = OperatorsResult()
        for code in SUPPORTED_LANGUAGES:
            set_report_language(code)
            chunks = [
                render_resources_md("demo", resources),
                render_topology_md("demo", topo),
                render_observability_md("demo", obs),
                render_configmaps_md("demo", cms),
                render_operators_md("demo", operators),
                render_action_plan_md("demo", findings, resources, obs, cms),
                render_references_md(),
                format_visualization_catalog([]),
            ]
            body = "\n".join(chunks)
            self.assertIn(t("res.title", name="demo"), body)
            self.assertIn(t("references.body").strip().splitlines()[0], body)
            self.assertNotIn("{name}", body)
            self.assertNotIn("{namespace}", body)

    def test_findings_text_follows_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "web.yaml"
            path.write_text(
                "apiVersion: apps/v1\n"
                "kind: Deployment\n"
                "metadata:\n"
                "  name: web\n"
                "  labels:\n"
                "    app: web\n"
                "spec:\n"
                "  replicas: 1\n"
                "  template:\n"
                "    spec:\n"
                "      containers:\n"
                "      - name: web\n"
                "        image: nginx:latest\n",
                encoding="utf-8",
            )
            ns = NamespaceArtifacts(name="demo", root=Path(tmp), deployments=[path])
            phrases = {
                "pt-br": "sem readinessProbe",
                "en-us": "missing readinessProbe",
                "es": "sin readinessProbe",
                "it": "readinessProbe assente",
            }
            for code, phrase in phrases.items():
                set_report_language(code)
                titles = [item.title for item in analyze_findings(ns).items]
                self.assertTrue(any(phrase in title for title in titles), titles)

    def test_load_runtime_settings_applies_language(self) -> None:
        settings = SystemSettings(
            language="es",
            status="active",
            llm_api_key="key",
            llm_model="model",
        )
        with patch.dict(os.environ, {"SYSTEM_SETTINGS_URL": "http://localhost:8000"}):
            with patch("agent.system_settings.fetch_system_settings", return_value=settings):
                self.assertTrue(load_runtime_settings())
        self.assertEqual(get_report_language(), "es")

    def test_load_runtime_settings_rejects_invalid_language(self) -> None:
        settings = SystemSettings(language="de", status="active", llm_api_key="key")
        with patch.dict(os.environ, {"SYSTEM_SETTINGS_URL": "http://localhost:8000"}):
            with patch("agent.system_settings.fetch_system_settings", return_value=settings):
                with self.assertRaises(SettingsLoadError):
                    load_runtime_settings()

    def test_load_runtime_settings_requires_url(self) -> None:
        env = os.environ.copy()
        env.pop("SYSTEM_SETTINGS_URL", None)
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SettingsLoadError):
                load_runtime_settings()


if __name__ == "__main__":
    unittest.main()
