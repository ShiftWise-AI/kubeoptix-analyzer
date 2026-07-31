"""Loop ReAct do agente de assessment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent.config import Settings
from agent.llm import LLMClient
from agent.prompts import SYSTEM_PROMPT, build_user_prompt
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


def run_assessment(artifacts_dir: Path, settings: Settings) -> Path:
    artifacts_dir = artifacts_dir.resolve()
    if not artifacts_dir.is_dir():
        raise SystemExit(f"Diretório de artefatos inválido: {artifacts_dir}")

    report = ReportBuilder(artifacts_dir=artifacts_dir)
    tools = build_all_tools(artifacts_dir, report, settings.max_file_chars)
    registry = tools_by_name(tools)
    schemas = openai_tool_schemas(tools)

    inventory = _initial_inventory(artifacts_dir, settings.max_file_chars)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(str(artifacts_dir), inventory)},
    ]

    llm = LLMClient(settings)
    print(f"[agent] Artefatos: {artifacts_dir}")
    print(f"[agent] Modelo: {settings.llm_model}")
    print(f"[agent] Tools: {', '.join(registry)}")

    for iteration in range(1, settings.max_iterations + 1):
        print(f"[agent] Iteração {iteration}/{settings.max_iterations}")
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
                    raise ValueError("Argumentos da tool devem ser um objeto JSON")
                tool = registry.get(name)
                if tool is None:
                    result = f"Tool desconhecida: {name}"
                else:
                    result = tool.run(**args)
            except Exception as exc:  # noqa: BLE001
                result = f"Erro ao executar {name}: {exc}"

            # Evita estourar contexto com resultados enormes
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
        print("[agent] Limite de iterações atingido.")
        if not report.sections:
            report.add_section(
                "Resumo incompleto",
                "O agente atingiu o limite de iterações antes de concluir a análise.",
            )

    out = report.write()
    print(f"[agent] Relatório gravado em: {out}")
    return out
