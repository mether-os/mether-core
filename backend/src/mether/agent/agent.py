"""METHER Agent — the main reasoning loop with tool calling."""

from __future__ import annotations

import json
import uuid
import asyncio
from typing import Any

import structlog

from mether.agent.llm import LLMClient, LLMError
from mether.events.bus import EventBus
from mether.memory.context import ContextMemory
from mether.tools.registry import ToolRegistry
from mether.tools.base import SecurityLevel

logger = structlog.get_logger(__name__)

# Maximum tool-call iterations per single user message to prevent runaway loops.
_MAX_TOOL_ROUNDS = 5

_FALLBACK_RESPONSE = (
    "METHER OFFLINE — LLM proxy unreachable.\n"
    "Start free-claude-code on port 8082 to enable AI responses."
)


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
        self.pending_confirmations: dict[str, asyncio.Event] = {}
        self.confirmation_results: dict[str, bool] = {}

    async def confirm_action(self, action_id: str, approved: bool):
        if action_id in self.pending_confirmations:
            self.confirmation_results[action_id] = approved
            self.pending_confirmations[action_id].set()

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
                        if getattr(tool_impl, "security_level", None) == SecurityLevel.DANGEROUS:
                            action_id = str(uuid.uuid4())
                            desc = f"Execute dangerous action with tool '{tool_name}'"
                            if tool_name == "process" and tool_input.get("action") == "kill":
                                desc = f"Kill process '{tool_input.get('name') or tool_input.get('pid')}'"
                            
                            await self.bus.emit("ws.send", {
                                "type": "confirm_required",
                                "action_id": action_id,
                                "tool": tool_name,
                                "description": desc,
                                "params": tool_input
                            })
                            
                            ev = asyncio.Event()
                            self.pending_confirmations[action_id] = ev
                            try:
                                await asyncio.wait_for(ev.wait(), timeout=30.0)
                            except asyncio.TimeoutError:
                                pass
                                
                            approved = self.confirmation_results.get(action_id, False)
                            
                            self.pending_confirmations.pop(action_id, None)
                            self.confirmation_results.pop(action_id, None)
                            
                            if not approved:
                                await self.bus.emit("ws.send", {"type": "action_cancelled", "action_id": action_id})
                                result_content = json.dumps({"error": "User denied action or timeout."})
                            else:
                                result = await tool_impl.execute(**tool_input)
                                result_content = result.model_dump_json()
                        else:
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

        system_tools_prompt = """
SYSTEM TOOLS AVAILABLE:
- app_launch: open any application ("open chrome", "launch vscode", "open spotify")
- code_run: run shell commands and scripts ("run this python file", "npm install", "git status")
- filesystem: read files, list dirs, search ("read my config file", "show files in downloads")
- process: list processes, system info, kill process ("what's using my CPU", "kill chrome")
- clipboard: read/write clipboard ("copy this to clipboard", "what's in my clipboard")
- screenshot: take screenshot ("screenshot my screen")

When user asks to open something, use app_launch.
When user asks to run a command or script, use code_run.
When user asks about system status, use process with action=info.
For file questions, use filesystem.

SAFETY RULES:
- DANGEROUS actions (kill, delete): always tell user what you're about to do first.
  Say: "I'll kill process X (PID 1234). Confirm?" and wait for confirmation.
- WRITE actions: execute immediately, report what was done.
- READ actions: execute immediately, present results cleanly.

GOOGLE TOOLS:
- gmail: search, read, send, reply to emails
  - "check my email" → gmail action=list_unread
  - "search emails from Mohit" → gmail action=search query="from:mohit"
  - "send email to x@y.com about meeting" → gmail action=send
  - "reply to that email" → gmail action=reply

- calendar: view and create calendar events
  - "what's on my calendar today" → calendar action=today
  - "schedule a meeting tomorrow at 3pm" → calendar action=create
  - "find a free 1 hour slot this week" → calendar action=find_slot

- drive: search and read Google Drive files
  - "find my project proposal" → drive action=search
  - "read that document" → drive action=read
  - "upload this file to drive" → drive action=upload

TIME ZONE: All times are in IST (Asia/Kolkata, UTC+5:30).
When creating calendar events, always convert user's local time to ISO format.
"""

        return persona + tools_section + "\n\nFor WhatsApp: when user asks to send a message to a name (e.g. 'send mohit a message'), do NOT use the resolve tool. Simply call the 'send' action with 'to' set to the person's name directly. The backend will instantly auto-resolve it. Only call 'send' once.\n" + system_tools_prompt
