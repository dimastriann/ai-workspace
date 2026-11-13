"""
AI Workspace API — Agent Service

Executes a bounded tool-calling loop and persists run steps.
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AgentRun, AgentStep
from app.models.skill import SkillManifest
from app.services.agent_provider import AgentProvider, ToolCall
from app.services.tools import tool_registry

DEFAULT_PERMISSIONS = {"search_documents", "calculator"}
MAX_STEPS = 6


class AgentService:
    """Run the plan → tool → observe loop."""

    async def execute_stream(
        self,
        *,
        db: AsyncSession,
        run: AgentRun,
        skill: SkillManifest | None,
        provider: AgentProvider,
        max_steps: int = MAX_STEPS,
    ) -> AsyncGenerator[dict[str, Any]]:
        permissions = set(skill.permissions) if skill else DEFAULT_PERMISSIONS
        tools = tool_registry.list_for(permissions)
        schemas = [tool.to_openai() for tool in tools]

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt(skill)},
            {"role": "user", "content": run.instruction},
        ]

        run.status = "running"
        await db.commit()
        yield {"event": "run_started", "run_id": str(run.id)}
        yield {
            "event": "tools",
            "tools": [tool.name for tool in tools],
        }

        result_text = ""
        ordinal = 0
        finished = False

        try:
            for _ in range(max_steps):
                assistant_text = ""
                calls: list[ToolCall] = []

                async for event in provider.stream(messages, schemas):
                    if event.type == "token":
                        assistant_text += event.content
                        result_text += event.content
                        yield {"event": "token", "token": event.content}
                    elif event.type == "tool_calls":
                        calls = event.tool_calls

                if not calls:
                    finished = True
                    break

                messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_text or None,
                        "tool_calls": [
                            {
                                "id": call.id,
                                "type": "function",
                                "function": {
                                    "name": call.name,
                                    "arguments": json.dumps(call.arguments),
                                },
                            }
                            for call in calls
                        ],
                    }
                )

                for call in calls:
                    output, step_status = await self._run_tool(
                        db, run, call, permissions
                    )
                    step = AgentStep(
                        run_id=run.id,
                        ordinal=ordinal,
                        kind="tool",
                        tool_name=call.name,
                        input=json.dumps(call.arguments)[:4000],
                        output=output[:4000],
                        status=step_status,
                    )
                    db.add(step)
                    ordinal += 1
                    await db.commit()

                    yield {
                        "event": "tool",
                        "tool": call.name,
                        "status": step_status,
                        "output": output[:1000],
                    }
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": output,
                        }
                    )

            if not finished:
                run.status = "failed"
                run.error = "Maximum steps reached"
                await db.commit()
                yield {"event": "error", "message": "Maximum steps reached"}
                return

            run.status = "completed"
            run.result = result_text
            await db.commit()
            yield {"event": "done", "run_id": str(run.id)}
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)
            await db.commit()
            yield {"event": "error", "message": str(exc)}

    async def _run_tool(
        self,
        db: AsyncSession,
        run: AgentRun,
        call: ToolCall,
        permissions: set[str],
    ) -> tuple[str, str]:
        tool = tool_registry.get(call.name)
        if tool is None or tool.permission not in permissions:
            return f"Tool not available: {call.name}", "error"
        if tool.requires_approval:
            return f"Tool requires approval: {call.name}", "error"

        try:
            output = await tool.handler(db, run.workspace_id, call.arguments)
            return output, "completed"
        except Exception as exc:
            return f"Tool failed: {exc}", "error"

    def _system_prompt(self, skill: SkillManifest | None) -> str:
        prompt = (
            "You are an autonomous agent in the AI Workspace platform. "
            "Use the available tools when they help. When you have enough "
            "information, answer the user directly without calling tools."
        )
        if skill is not None:
            prompt += f"\n\nActive skill: {skill.name}\n{skill.instructions}"
        return prompt


agent_service = AgentService()
