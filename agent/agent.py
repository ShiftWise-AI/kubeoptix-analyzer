"""ReAct loop for the assessment agent."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from agent.config import Settings
from agent.i18n import t
from agent.llm import LLMClient
from agent.prompts import build_system_prompt, build_user_prompt
from agent.report import ReportBuilder
from agent.tools import build_all_tools, openai_tool_schemas, tools_by_name
from agent.tools.filesystem import build_filesystem_tools
from agent.local_analyze import resolve_report_path
from agent.visualization.pregenerate import (
    append_missing_visualizations,
    finalize_report_markdown,
    format_visualization_catalog,
    generate_all_visualizations,
)


def _initial_inventory(artifacts_dir: Path, max_file_chars: int) -> str:
    list_tool = next(
        t for t in build_filesystem_tools(artifacts_dir, max_file_chars) if t.name == "list_artifacts"
    )
    return list_tool.run(path=".")


def _message_content(message: Any) -> str:
    content = getattr(message, "content", None)
    if content:
        return str(content)
    return ""


def _write_progress_event(
    *,
    current_file: str | None,
    processed_files: set[str],
) -> None:
    progress_path = os.getenv("KUBEOPTIX_PROGRESS_FILE", "").strip()
    if not progress_path:
        return

    payload = {
        "current_file": current_file,
        "processed_files": sorted(processed_files),
    }
    target = Path(progress_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    temporary.replace(target)


def run_assessment(
    artifacts_dir: Path,
    settings: Settings,
    report_path: Path | None = None,
) -> Path:
    artifacts_dir = artifacts_dir.resolve()
    if not artifacts_dir.is_dir():
        raise SystemExit(f"Invalid artifacts directory: {artifacts_dir}")

    dest = resolve_report_path(artifacts_dir, report_path)
    report = ReportBuilder(artifacts_dir=artifacts_dir)
    assets, visualizations = generate_all_visualizations(artifacts_dir)
    viz_catalog = format_visualization_catalog(visualizations)
    if visualizations:
        print(
            f"[agent] Pre-generated {len(visualizations)} namespace visualization set(s) "
            f"in {assets.assets_dir}"
        )

    tools = build_all_tools(
        artifacts_dir,
        report,
        settings.max_file_chars,
        assets=assets,
        visualizations=visualizations,
        report_dir=dest.parent,
    )
    registry = tools_by_name(tools)
    schemas = openai_tool_schemas(tools)

    inventory = _initial_inventory(artifacts_dir, settings.max_file_chars)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": build_system_prompt()},
        {
            "role": "user",
            "content": build_user_prompt(
                str(artifacts_dir),
                inventory,
                viz_catalog,
            ),
        },
    ]

    llm = LLMClient(settings)
    print(f"[agent] Artifacts: {artifacts_dir}")
    print(f"[agent] Model: {settings.llm_model}")
    print(f"[agent] Tools: {', '.join(registry)}")
    processed_files: set[str] = set()

    for iteration in range(1, settings.max_iterations + 1):
        print(f"[agent] Iteration {iteration}/{settings.max_iterations}")
        response = llm.chat(messages, tools=schemas)
        choice = response.choices[0]
        message = choice.message

        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": message.content,
        }
        if message.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments or "{}",
                    },
                }
                for tc in message.tool_calls
            ]
        messages.append(assistant_msg)

        if not message.tool_calls:
            final_text = _message_content(message).strip()
            if final_text and not report.sections:
                report.add_section("Resumo do agente", final_text)
            elif final_text:
                report.add_section("Notas finais", final_text)
            break

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            raw_args = tool_call.function.arguments or "{}"
            print(f"[agent] tool → {name}")
            try:
                args = json.loads(raw_args) if raw_args else {}
                if not isinstance(args, dict):
                    raise ValueError("Tool arguments must be a JSON object")
                tool = registry.get(name)
                if tool is None:
                    result = f"Unknown tool: {name}"
                else:
                    current_file = None
                    if name in {"read_file", "find_files"}:
                        requested_path = args.get("path")
                        if isinstance(requested_path, str) and requested_path not in {"", "."}:
                            current_file = requested_path
                    _write_progress_event(
                        current_file=current_file,
                        processed_files=processed_files,
                    )
                    result = tool.run(**args)
                    if current_file is not None:
                        processed_files.add(current_file)
                    _write_progress_event(
                        current_file=current_file,
                        processed_files=processed_files,
                    )
            except Exception as exc:  # noqa: BLE001
                result = f"Error running {name}: {exc}"

            # Prevent huge tool results from overflowing the context window.
            if len(result) > settings.max_file_chars:
                result = (
                    result[: settings.max_file_chars]
                    + f"\n...[truncado para {settings.max_file_chars} chars]"
                )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )
    else:
        print("[agent] Iteration limit reached.")
        if not report.sections:
            report.add_section(
                t("report.incomplete_title"),
                t("report.incomplete_body"),
            )

    if visualizations:
        report.sections = append_missing_visualizations(
            report.sections,
            visualizations,
        )

    content = finalize_report_markdown(
        report.render(),
        artifacts_dir=artifacts_dir,
        report_dir=dest.parent,
        visualizations=visualizations,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")

    from agent.visualization.report_postprocess import cleanup_stray_report_scripts

    cleanup_stray_report_scripts(dest.parent)
    return dest
