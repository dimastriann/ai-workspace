"""
AI Workspace API — Agent Tool Layer

Tool specifications, permission filtering, and built-in safe tools.
"""

import ast
import json
import operator
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retrieval import retrieval_service

ToolHandler = Callable[[AsyncSession, UUID, dict[str, Any]], Awaitable[str]]


@dataclass(frozen=True)
class ToolSpec:
    """A tool the agent may call."""

    name: str
    description: str
    parameters: dict[str, Any]
    permission: str
    handler: ToolHandler
    requires_approval: bool = False

    def to_openai(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Registry of tools filtered by skill permissions."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Duplicate tool: {spec.name}")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def list_for(self, permissions: set[str]) -> list[ToolSpec]:
        return [tool for tool in self._tools.values() if tool.permission in permissions]


# ── Calculator ───────────────────────────────────────────────────────────────

_BINARY_OPS: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY_OPS: dict[type[ast.unaryop], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def evaluate_expression(expression: str) -> float:
    """Evaluate a small arithmetic expression without eval()."""
    tree = ast.parse(expression, mode="eval")
    return float(_eval_node(tree.body))


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
        return float(
            _BINARY_OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
        )
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return float(_UNARY_OPS[type(node.op)](_eval_node(node.operand)))
    raise ValueError("Unsupported expression")


async def calculator_handler(
    db: AsyncSession, workspace_id: UUID, arguments: dict[str, Any]
) -> str:
    del db, workspace_id
    return str(evaluate_expression(str(arguments["expression"])))


async def search_documents_handler(
    db: AsyncSession, workspace_id: UUID, arguments: dict[str, Any]
) -> str:
    chunks = await retrieval_service.search(str(arguments["query"]), workspace_id, db)
    if not chunks:
        return "No matching document chunks."
    return json.dumps(
        [
            {
                "filename": chunk.filename,
                "ordinal": chunk.ordinal,
                "content": chunk.content[:800],
            }
            for chunk in chunks
        ]
    )


tool_registry = ToolRegistry()
tool_registry.register(
    ToolSpec(
        name="calculator",
        description="Evaluate a basic arithmetic expression.",
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Expression such as (2 + 3) * 4",
                }
            },
            "required": ["expression"],
            "additionalProperties": False,
        },
        permission="calculator",
        handler=calculator_handler,
    )
)
tool_registry.register(
    ToolSpec(
        name="search_documents",
        description="Search the current workspace documents for relevant chunks.",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords or a question to search for",
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        permission="search_documents",
        handler=search_documents_handler,
    )
)
