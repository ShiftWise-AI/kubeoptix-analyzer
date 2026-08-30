"""ReAct loop for the assessment agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.config import Settings
from agent.i18n import DEFAULT_LOCALE
from agent.llm import LLMClient
from agent.prompts import build_system_prompt, build_user_prompt
from agent.report import ReportBuilder
from agent.tools import build_all_tools, openai_tool_schemas, tools_by_name
from agent.tools.filesystem import build_filesystem_tools


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


def _fallback_section_texts(locale: str) -> tuple[str, str, str, str]:
    if locale == DEFAULT_LOCALE:
        return (
            "Agent summary",
            "Final notes",
            "Incomplete summary",
            "The agent reached the iteration limit before completing the analysis.",
        )
    return (
        "Agent summary",
        "Final notes",
        "Incomplete summary",
        "The agent hit the iteration limit before completing the analysis.",
    )


def run_assessment(
    artifacts_dir: Path,
    settings: Settings,
    locale: str = "pt-BR",
) -> Path:
    artifacts_dir = artifacts_dir.resolve()
    if not artifacts_dir.is_dir():
        raise SystemExit(f"Invalid artifacts directory: {artifacts_dir}")

    report = ReportBuilder(artifacts_dir=artifacts_dir, locale=locale)
    tools = build_all_tools(artifacts_dir, report, settings.max_file_chars)
    registry = tools_by_name(tools)
    schemas = openai_tool_schemas(tools)

    inventory = _initial_inventory(artifacts_dir, settings.max_file_chars)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": build_system_prompt(locale)},
        {"role": "user", "content": build_user_prompt(str(artifacts_dir), inventory, locale)},
    ]
    summary_title, final_notes_title, incomplete_title, incomplete_body = _fallback_section_texts(locale)

    llm = LLMClient(settings)
    print(f"[agent] Artifacts: {artifacts_dir}")
    print(f"[agent] Model: {settings.llm_model}")
    print(f"[agent] Tools: {', '.join(registry)}")

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
                report.add_section(summary_title, final_text)
            elif final_text:
                report.add_section(final_notes_title, final_text)
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
                    result = tool.run(**args)
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
            report.add_section(incomplete_title, incomplete_body)

    out = report.write()
    print(f"[agent] Report written to: {out}")
    return out
