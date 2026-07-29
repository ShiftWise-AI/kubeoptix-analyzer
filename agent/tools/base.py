"""Protocolo e helpers para tools do agente."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


class Tool(Protocol):
    name: str
    description: str
    parameters: dict[str, Any]

    def run(self, **kwargs: Any) -> str: ...


@dataclass
class FunctionTool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., str]

    def run(self, **kwargs: Any) -> str:
        return self.handler(**kwargs)

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def object_schema(
    properties: dict[str, Any],
    required: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }
