"""METHER Agent — the main reasoning loop with tool calling."""

from __future__ import annotations

import json
from typing import Any

import structlog

from mether.agent.llm import LLMClient, LLMError
from mether.events.bus import EventBus
from mether.memory.context import ContextMemory
from mether.tools.registry import ToolRegistry

logger = structlog.get_logger(__name__)

# Maximum tool-call iterations per single user message to prevent runaway loops.
_MAX_TOOL_ROUNDS = 5

_FALLBACK_RESPONSE = "METHER: LLM proxy offline. Running in limited mode."


class METHERAgent:
    """Core reasoning engine.

    1. Receives a user message.
    2. Builds a system prompt from CLAUDE.md + available tools.
    3. Calls the LLM (with tool schemas).
    4. If the LLM requests tool calls, executes them and feeds results back.
    5. Returns the final text response.
    """

    def __init__(
        self,
        llm: LLMClient,
        tools: ToolRegistry,
        memory: ContextMemory,
        bus: EventBus,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.memory = memory
        self.bus = bus

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process(self, user_message: str) -> str:
        """Process a single user message through the full agent loop.

        Returns the assistant's final text response.
        """
        logger.info("agent.process_start", message=user_message[:120])

        # 1. Emit thinking event
        await self.bus.emit("agent.thinking", {"message": user_message})

        # 2. Build system prompt
        system_prompt = self._build_system_prompt()

        # 3. Build messages list from memory + current message
        messages: list[dict[str, Any]] = self.memory.get_recent_context()
        messages.append({"role": "user", "content": user_message})

        # 4. Get tool schemas
        tool_schemas = self.tools.all_schemas() or None

        # 5. Reasoning + tool-calling loop
        try:
            response_text = await self._agent_loop(messages, tool_schemas, system_prompt)
        except LLMError as exc:
            logger.warning("agent.llm_offline", error=str(exc))
            response_text = _FALLBACK_RESPONSE

        # 6. Persist to session memory
        self.memory.add_interaction(user_message, response_text)

        # 7. Emit response event
        await self.bus.emit("agent.response", {"text": response_text})

        logger.info("agent.process_done", response_length=len(response_text))
        return response_text

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _agent_loop(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        system: str,
    ) -> str:
        """Run the LLM → tool-call → LLM feedback loop.

        Returns the final assistant text when ``stop_reason`` is ``"end_turn"``
        or the maximum number of tool rounds is reached.
        """
        for round_idx in range(_MAX_TOOL_ROUNDS):
            llm_response = await self.llm.chat(messages=messages, tools=tools, system=system)

            stop_reason = llm_response.get("stop_reason", "end_turn")
            content_blocks = llm_response.get("content", [])

            # Accumulate any text blocks
            text_parts: list[str] = []
            tool_use_blocks: list[dict[str, Any]] = []

            for block in content_blocks:
                if block.get("type") == "text":
                    text_parts.append(block["text"])
                elif block.get("type") == "tool_use":
                    tool_use_blocks.append(block)

            # If no tool calls requested, we're done.
            if stop_reason != "tool_use" or not tool_use_blocks:
                return "\n".join(text_parts) if text_parts else _FALLBACK_RESPONSE

            # --- Execute each requested tool ----------------------------------
            # Append the assistant's response (with tool_use blocks) first.
            messages.append({"role": "assistant", "content": content_blocks})

            tool_results: list[dict[str, Any]] = []
            for tool_block in tool_use_blocks:
                tool_name = tool_block["name"]
                tool_input = tool_block.get("input", {})
                tool_use_id = tool_block["id"]

                logger.info("agent.tool_call", tool=tool_name, round=round_idx)
                await self.bus.emit("tool.start", {"tool": tool_name, "input": tool_input})

                tool_impl = self.tools.get(tool_name)
                if tool_impl is None:
                    result_content = json.dumps({"error": f"Unknown tool: {tool_name}"})
                else:
                    try:
                        result = await tool_impl.execute(**tool_input)
                        result_content = result.model_dump_json()
                    except Exception as exc:
                        logger.exception("agent.tool_error", tool=tool_name)
                        result_content = json.dumps({"error": str(exc)})

                await self.bus.emit("tool.done", {"tool": tool_name, "result": result_content})

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result_content,
                    }
                )

            # Feed tool results back to the LLM.
            messages.append({"role": "user", "content": tool_results})

        # Exhausted tool rounds — return whatever text we have.
        logger.warning("agent.max_tool_rounds", max=_MAX_TOOL_ROUNDS)
        return "\n".join(text_parts) if text_parts else _FALLBACK_RESPONSE  # type: ignore[possibly-undefined]

    def _build_system_prompt(self) -> str:
        """Construct the full system prompt.

        Combines the CLAUDE.md persona with a dynamic listing of
        available tools.
        """
        persona = self.memory.load_claude_md()

        tool_names = self.tools.list_names()
        if tool_names:
            tools_section = "\n\n## Available Tools\n" + "\n".join(
                f"- **{name}**" for name in tool_names
            )
        else:
            tools_section = ""

        return persona + tools_section
