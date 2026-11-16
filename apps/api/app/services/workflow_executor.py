"""Sequential execution of saved agent workflows."""

import json
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AgentRun, AgentStep, Workflow
from app.services.agent_provider import AgentProvider, ToolCall
from app.services.agent_service import DEFAULT_PERMISSIONS
from app.services.skills import skill_registry
from app.services.tools import tool_registry

MAX_TOOL_ROUNDS = 4
MAX_PERSISTED_STEPS = 50


class WorkflowExecutor:
    """Run workflow steps in order, passing each result to the next step."""

    async def execute_stream(
        self,
        *,
        db: AsyncSession,
        run: AgentRun,
        workflow: Workflow,
        provider: AgentProvider,
        user_input: str = "",
    ) -> AsyncGenerator[dict[str, Any]]:
        run.status = "running"
        await db.commit()
        yield {
            "event": "run_started",
            "run_id": str(run.id),
            "workflow_id": str(workflow.id),
        }

        previous: list[str] = []
        ordinal = 0
        steps = list(workflow.steps)

        try:
            for index, step in enumerate(steps):
                skill = skill_registry.get(step.skill) if step.skill else None
                permissions = (
                    set(skill.permissions) if skill else set(DEFAULT_PERMISSIONS)
                )
                tools = tool_registry.list_for(permissions)
                schemas = [tool.to_openai() for tool in tools]

                yield {
                    "event": "step_started",
                    "step": index,
                    "total": len(steps),
                    "instruction": step.instruction,
                    "skill": step.skill,
                }

                messages: list[dict[str, Any]] = [
                    {"role": "system", "content": self._system_prompt(workflow, skill)},
                    {
                        "role": "user",
                        "content": self._step_prompt(
                            workflow,
                            step.instruction,
                            previous,
                            user_input,
                        ),
                    },
                ]

                step_text = ""
                finished = False

                for _ in range(MAX_TOOL_ROUNDS):
                    assistant_text = ""
                    calls: list[ToolCall] = []

                    async for event in provider.stream(messages, schemas):
                        if event.type == "token":
                            assistant_text += event.content
                            step_text += event.content
                            yield {
                                "event": "token",
                                "step": index,
                                "token": event.content,
                            }
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
                        if ordinal >= MAX_PERSISTED_STEPS:
                            raise RuntimeError("Workflow exceeded its step budget")
                        db.add(
                            AgentStep(
                                run_id=run.id,
                                ordinal=ordinal,
                                kind="tool",
                                tool_name=call.name,
                                input=json.dumps(call.arguments)[:4000],
                                output=output[:4000],
                                status=step_status,
                            )
                        )
                        ordinal += 1
                        await db.commit()
                        yield {
                            "event": "tool",
                            "step": index,
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
                    raise RuntimeError(f"Step {index + 1} exceeded its tool budget")

                result = step_text.strip()
                db.add(
                    AgentStep(
                        run_id=run.id,
                        ordinal=ordinal,
                        kind="task",
                        tool_name=step.skill,
                        input=step.instruction[:4000],
                        output=result[:4000],
                        status="completed",
                    )
                )
                ordinal += 1
                await db.commit()

                previous.append(f"Step {index + 1} result:\n{result}")
                yield {
                    "event": "step_completed",
                    "step": index,
                    "output": result,
                }

            run.status = "completed"
            run.result = "\n\n".join(previous)
            await db.commit()
            yield {"event": "done", "run_id": str(run.id)}
        except Exception as exc:
            run.status = "failed"
            run.error = str(exc)[:2000]
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

    @staticmethod
    def _system_prompt(workflow: Workflow, skill: Any) -> str:
        prompt = (
            "You are executing one step of a saved workflow in the AI Workspace "
            "platform. Complete only the current step. Use tools when helpful, "
            "then return a concise result for the next step."
        )
        if skill is not None:
            prompt += f"\n\nActive skill: {skill.name}\n{skill.instructions}"
        prompt += f"\n\nWorkflow: {workflow.name}"
        if workflow.description:
            prompt += f"\nWorkflow goal: {workflow.description}"
        return prompt

    @staticmethod
    def _step_prompt(
        workflow: Workflow,
        instruction: str,
        previous: list[str],
        user_input: str,
    ) -> str:
        parts = [f"Current instruction:\n{instruction}"]
        if user_input.strip():
            parts.append(f"User input:\n{user_input.strip()}")
        if previous:
            parts.append("Previous step results:\n" + "\n\n".join(previous))
        else:
            parts.append("This is the first step.")
        parts.append("Return only the result for this step.")
        return "\n\n".join(parts)


workflow_executor = WorkflowExecutor()
