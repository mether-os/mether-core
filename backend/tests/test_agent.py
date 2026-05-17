import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_agent_process_returns_string(mock_agent):
    result = await mock_agent.process("hello")
    assert isinstance(result, str)
    assert len(result) > 0

@pytest.mark.asyncio
async def test_agent_handles_llm_failure():
    from mether.agent.agent import METHERAgent
    from mether.events.bus import EventBus
    from mether.tools.registry import ToolRegistry
    from mether.memory.context import ContextMemory
    from mether.agent.llm import LLMError
    
    bus = EventBus()
    registry = ToolRegistry()
    memory = ContextMemory("/tmp/nonexistent_claude.md")
    
    mock_llm = AsyncMock()
    mock_llm.chat = AsyncMock(side_effect=LLMError("LLM offline"))
    
    agent = METHERAgent(mock_llm, registry, memory, bus)
    result = await agent.process("test message")
    
    assert "offline" in result.lower() or "error" in result.lower()
